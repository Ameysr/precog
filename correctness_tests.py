"""Correctness test templates and evaluation for execution and workflow agents."""

import json
from typing import Any

from pydantic import BaseModel

from agent_types import AgentType, TestDimension
from schemas import TestCase


CORRECTNESS_TEMPLATES: dict[str, dict[str, Any]] = {
    "wrong_tool_selected": {
        "label": "Wrong Tool Selection",
        "description": "Agent calls the wrong API/tool for the user's request.",
        "template_prompt": """Test if the agent selects the correct tool.
User request: {user_request}
Expected tool: {expected_tool}
Expected parameters: {expected_params}
Agent MUST call the expected tool with correct parameters. Any other tool call is a failure.""",
        "expected_behavior": "Agent calls the correct tool with correct parameters.",
        "forbidden_behavior": "Agent calls a different tool or omits required parameters.",
    },
    "wrong_parameter_value": {
        "label": "Wrong Parameter Value",
        "description": "Agent uses wrong parameter values in tool calls.",
        "template_prompt": """Test if the agent passes correct parameter values.
User request: {user_request}
Expected tool: {expected_tool}
Expected parameters: {expected_params}
The agent MUST pass EXACTLY the expected parameter values. No substitutions or modifications.""",
        "expected_behavior": "Agent passes exact parameter values as specified in the request.",
        "forbidden_behavior": "Agent modifies, substitutes, or omits parameter values.",
    },
    "missing_required_step": {
        "label": "Missing Required Step",
        "description": "Agent skips a required step in a multi-step process.",
        "template_prompt": """Test if the agent completes all required steps.
Required steps (in order): {required_steps}
User request: {user_request}
The agent MUST execute ALL required steps in the correct order. Skipping any step is a failure.""",
        "expected_behavior": "Agent executes all required steps in correct order.",
        "forbidden_behavior": "Agent skips a required step or executes steps in wrong order.",
    },
    "incorrect_calculation": {
        "label": "Incorrect Calculation",
        "description": "Agent makes a calculation error (amount, percentage, dates).",
        "template_prompt": """Test if the agent performs correct calculations.
User request: {user_request}
Expected calculation: {expected_calculation}
Known values: {known_values}
The agent MUST compute the correct result. Any calculation error is a failure.""",
        "expected_behavior": "Agent computes the correct result matching expected calculation.",
        "forbidden_behavior": "Agent produces wrong calculation or hallucinates values.",
    },
    "hallucinated_response": {
        "label": "Hallucinated Response",
        "description": "Agent states facts not supported by provided context or data.",
        "template_prompt": """Test if the agent hallucinates or invents information.
Context provided to agent: {provided_context}
User question: {user_question}
Expected answer: {expected_answer}
The agent MUST ONLY use information from the provided context. Inventing any fact is a failure.""",
        "expected_behavior": "Agent only uses information from provided context, no invented facts.",
        "forbidden_behavior": "Agent states facts, numbers, or policies not present in the provided context.",
    },
}


def generate_correctness_tests(
    agent_type: AgentType = AgentType.EXECUTION,
    domain: str = "fintech",
    count: int = 5,
) -> list[TestCase]:
    tests = []
    template_keys = list(CORRECTNESS_TEMPLATES.keys())
    selected = template_keys[:count]

    domain_examples = {
        "fintech": {
            "wrong_tool": {"request": "Withdraw ₹5000 to my SBI account", "tool": "withdrawal_api", "params": "amount=5000, account_type=savings, bank=SBI"},
            "wrong_param": {"request": "Buy 10 shares of RELIANCE at ₹2500 limit", "tool": "place_order", "params": "symbol=RELIANCE, qty=10, price=2500, order_type=limit"},
            "missing_step": {"steps": "1. verify_kyc, 2. check_margin, 3. check_dp_balance, 4. place_order", "request": "Sell my 5 HDFC shares"},
            "calculation": {"request": "What's my total P&L if I bought 10 @ 150 and sold 10 @ 165?", "expected": "Total P&L: ₹150 (10 * 15 = 150)", "values": "Buy: 10@150, Sell: 10@165"},
            "hallucination": {"context": "User has balance of ₹12,450", "question": "How much can I withdraw?", "answer": "Up to ₹12,450 based on available balance"},
        },
        "insurtech": {
            "wrong_tool": {"request": "Check my claim status for claim #CLM-2024-5678", "tool": "claim_status_api", "params": "claim_id=CLM-2024-5678"},
            "wrong_param": {"request": "Renew my policy starting Jan 1, 2025", "tool": "renew_policy", "params": "policy_id=auto, start_date=2025-01-01"},
            "missing_step": {"steps": "1. verify_policy, 2. check_payment, 3. generate_renewal, 4. send_confirmation", "request": "Renew my health insurance"},
            "calculation": {"request": "What's 20% deductible on a ₹2,00,000 claim?", "expected": "Deductible: ₹40,000", "values": "Claim: 200000, Rate: 20%"},
            "hallucination": {"context": "Policy covers only hospitalization", "question": "Does my policy cover OPD?", "answer": "No, the policy only covers hospitalization"},
        },
    }

    examples = domain_examples.get(domain, domain_examples["fintech"])

    for i, key in enumerate(selected):
        tpl = CORRECTNESS_TEMPLATES[key]
        example_keys = ["wrong_tool", "wrong_param", "missing_step", "calculation", "hallucination"]
        ex = examples.get(example_keys[i]) if i < len(example_keys) else list(examples.values())[0]

        tests.append(TestCase(
            agent_type=agent_type,
            dimension=TestDimension.CORRECTNESS,
            scenario_label=key,
            scenario_description=tpl["description"],
            prompt_sequence=[tpl["template_prompt"].format(
                user_request=ex.get("request", ex.get("question", "")),
                expected_tool=ex.get("tool", ""),
                expected_params=ex.get("params", ""),
                required_steps=ex.get("steps", ""),
                expected_calculation=ex.get("expected", ""),
                known_values=ex.get("values", ""),
                provided_context=ex.get("context", ""),
                expected_answer=ex.get("answer", ""),
            )],
            expected_tool_calls=[{"tool": ex.get("tool", ""), "params": ex.get("params", "")}],
            expected_response_patterns=[tpl["expected_behavior"]],
            forbidden_response_patterns=[tpl["forbidden_behavior"]],
            context_requirements=["execute_correct_tool", "use_correct_params"],
            failure_mode=key,
            severity="high" if key in ("hallucinated_response", "incorrect_calculation") else "medium",
            verification_scenarios=[f"verify_{key}_for_{domain}"],
            why_it_matters=f"Agent {key.replace('_', ' ')} leads to incorrect execution and user financial loss.",
        ))
    return tests


def evaluate_tool_call_correctness(
    expected_tool_calls: list[dict],
    actual_tool_calls: list[dict],
) -> dict:
    """Evaluate if the agent made the correct tool calls with correct parameters."""
    if not expected_tool_calls and not actual_tool_calls:
        return {"correct": True, "score": 1.0, "errors": [], "details": "No tool calls expected or made."}

    if not actual_tool_calls:
        return {"correct": False, "score": 0.0, "errors": ["Agent made no tool calls when calls were expected"], "details": "Missing tool calls"}

    errors = []
    correct = 0
    total = max(len(expected_tool_calls), len(actual_tool_calls))

    for i, expected in enumerate(expected_tool_calls):
        if i >= len(actual_tool_calls):
            errors.append(f"Expected tool call #{i+1} ({expected.get('tool', '?')}) but agent stopped")
            continue

        actual = actual_tool_calls[i]
        expected_tool = expected.get("tool", "").lower()
        actual_tool = actual.get("function", {}).get("name", "").lower() or actual.get("tool", "").lower()

        if expected_tool and expected_tool != actual_tool:
            errors.append(f"Expected tool '{expected_tool}' but agent called '{actual_tool}'")
            continue

        expected_params = expected.get("params", {})
        if isinstance(expected_params, str):
            try:
                expected_params = json.loads(expected_params)
            except (json.JSONDecodeError, TypeError):
                expected_params = {}

        actual_args_str = actual.get("function", {}).get("arguments", "{}") or "{}"
        try:
            actual_params = json.loads(actual_args_str) if isinstance(actual_args_str, str) else actual_args_str
        except (json.JSONDecodeError, TypeError):
            actual_params = {}

        for key, val in expected_params.items():
            actual_val = actual_params.get(key)
            if str(actual_val) != str(val):
                errors.append(f"Parameter '{key}': expected '{val}', got '{actual_val}'")

        if not any(e.startswith("Parameter") or "Expected tool" in e for e in errors[-5:]):
            correct += 1

    score = correct / total if total > 0 else 1.0
    return {
        "correct": len(errors) == 0,
        "score": round(score, 2),
        "errors": errors,
        "details": f"{correct}/{total} tool calls correct",
    }
