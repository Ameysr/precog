"""Universal test runner. Executes test cases against any agent via AgentProtocol adapter."""

from __future__ import annotations

import json
import uuid
from typing import Sequence

from agent_protocol import AgentProtocol, ChatMessage, HTTPChatAdapter, ScriptAdapter
from agent_types import AgentType
from config import AGENT_ADAPTER, AGENT_API_KEY, AGENT_ENDPOINT, AGENT_MODEL, AGENT_TYPE
from schemas import TestCase, TestRunResult


def create_adapter(
    adapter_type: str = "",
    endpoint: str = "",
    api_key: str = "",
    model: str = "",
    handler_fn=None,
) -> AgentProtocol:
    adapter_type = adapter_type or AGENT_ADAPTER
    endpoint = endpoint or AGENT_ENDPOINT
    api_key = api_key or AGENT_API_KEY
    model = model or AGENT_MODEL

    if adapter_type == "http":
        return HTTPChatAdapter(endpoint=endpoint, api_key=api_key, model=model)
    elif adapter_type == "script":
        if handler_fn is None:
            raise ValueError("handler_fn required for script adapter")
        return ScriptAdapter(handler_fn=handler_fn)
    elif adapter_type == "langchain":
        from agent_protocol import LangChainAdapter
        if handler_fn is None:
            raise ValueError("agent_executor required for langchain adapter")
        return LangChainAdapter(agent_executor=handler_fn)
    else:
        return HTTPChatAdapter(endpoint=endpoint, api_key=api_key, model=model)


class TestRunner:
    def __init__(self, agent: AgentProtocol):
        self._agent = agent
        self._history: list[ChatMessage] = []

    def run_test(self, test_case: TestCase) -> TestRunResult:
        result = TestRunResult(
            test_case_id=test_case.id or f"test_{uuid.uuid4().hex[:8]}",
            dimension=test_case.dimension,
            agent_type=test_case.agent_type,
            passed=False,
        )

        prompts = test_case.prompt_sequence
        if not prompts:
            result.errors.append("No prompts in test case")
            return result

        all_responses: list[str] = []
        all_tool_calls: list[dict] = []

        try:
            for i, prompt in enumerate(prompts):
                msg = ChatMessage.user(prompt)
                response = self._agent.chat(self._history + [msg])
                self._history.append(msg)
                self._history.append(ChatMessage.assistant(response.text, response.tool_calls))
                all_responses.append(response.text)
                all_tool_calls.extend(response.tool_calls)

            result.actual_responses = all_responses
            result.actual_tool_calls = all_tool_calls

            if test_case.dimension.value == "memory_context":
                ctx_scores = _score_context_retention(self._history, test_case.context_requirements)
                result.context_retention_score = ctx_scores.get("retention_score")
                result.passed = ctx_scores.get("context_retained", False)
                result.score = ctx_scores.get("retention_score", 0.0)
                if ctx_scores.get("failures"):
                    result.failure_detail = "; ".join(ctx_scores["failures"])
                    result.errors = ctx_scores["failures"]

            elif test_case.expected_tool_calls:
                from correctness_tests import evaluate_tool_call_correctness
                eval_result = evaluate_tool_call_correctness(test_case.expected_tool_calls, all_tool_calls)
                result.tool_call_accuracy = eval_result["score"]
                result.passed = eval_result["correct"]
                result.score = eval_result["score"]
                if eval_result["errors"]:
                    result.failure_detail = "; ".join(eval_result["errors"])
                    result.errors = eval_result["errors"]

            elif test_case.forbidden_response_patterns:
                combined = " ".join(all_responses).lower()
                violations = [p for p in test_case.forbidden_response_patterns if p.lower() in combined]
                if violations:
                    result.passed = False
                    result.score = 0.0
                    result.failure_detail = f"Forbidden patterns found: {violations}"
                    result.errors = violations
                else:
                    result.passed = True
                    result.score = 1.0

            elif test_case.expected_response_patterns:
                combined = " ".join(all_responses).lower()
                matches = [p for p in test_case.expected_response_patterns if p.lower() in combined or _semantic_match(p, combined)]
                match_pct = len(matches) / len(test_case.expected_response_patterns) if test_case.expected_response_patterns else 0
                result.passed = match_pct > 0.5
                result.score = match_pct

            else:
                result.passed = bool(all_responses[-1]) if all_responses else False
                result.score = 1.0 if result.passed else 0.0

        except Exception as e:
            result.errors.append(str(e))
            result.failure_detail = f"Runner error: {e}"
            result.passed = False
            result.score = 0.0

        return result

    def run_suite(self, test_cases: Sequence[TestCase]) -> list[TestRunResult]:
        results = []
        for tc in test_cases:
            r = self.run_test(tc)
            results.append(r)
            status = "PASS" if r.passed else "FAIL"
            print(f"  [{status}] {tc.scenario_label or tc.failure_mode} ({r.score:.2f})")
        return results

    def reset(self) -> None:
        self._history = []
        self._agent.reset()


def _score_context_retention(history: list[ChatMessage], requirements: list[str]) -> dict:
    from memory_tests import evaluate_context_retention
    conv = []
    for msg in history:
        conv.append({"role": msg.role, "content": msg.content, "tool_calls": msg.tool_calls})
    return evaluate_context_retention(conv, requirements)


def _semantic_match(pattern: str, text: str) -> bool:
    keywords = pattern.lower().split()
    return sum(1 for k in keywords if k in text) / max(len(keywords), 1) > 0.3
