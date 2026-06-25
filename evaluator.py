"""Multi-dimensional agent evaluator. LLM-as-judge + rule-based scoring for all 5 dimensions."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from agent_types import AgentType, TestDimension, get_failure_types_for_dimension, DIMENSION_DESCRIPTIONS
from schemas import TestRunResult, DimensionCoverage, AgentTestReport
from utils import call_llm


class DimensionEvalResult(BaseModel):
    score: float
    passed: bool
    strengths: list[str]
    weaknesses: list[str]
    critical_failures: list[str]
    explanation: str


def evaluate_dimension(
    dimension: TestDimension,
    results: list[TestRunResult],
    agent_type: AgentType = AgentType.CONVERSATIONAL,
) -> DimensionCoverage:
    dim_results = [r for r in results if r.dimension == dimension]
    total = len(dim_results)
    passed = sum(1 for r in dim_results if r.passed)
    failed = total - passed

    all_failure_types = set(get_failure_types_for_dimension(dimension))
    tested_types = set()
    for r in dim_results:
        tested_types.add(r.failure_detail.split(":")[0].strip() if r.failure_detail else r.test_case_id)

    score = (passed / total) if total > 0 else 0.0

    return DimensionCoverage(
        dimension=dimension,
        total=total,
        passed=passed,
        failed=failed,
        score=round(score, 2),
        failure_types_tested=sorted(tested_types & all_failure_types),
        failure_types_missing=sorted(all_failure_types - tested_types),
    )


def evaluate_overall(
    run_results: list[TestRunResult],
    agent_type: AgentType = AgentType.CONVERSATIONAL,
    agent_name: str = "agent",
) -> AgentTestReport:
    dim_coverages = {}
    for dim in TestDimension:
        dc = evaluate_dimension(dim, run_results, agent_type)
        dim_coverages[dim.value] = dc

    from agent_types import DIMENSION_WEIGHT_BY_AGENT_TYPE
    weights = DIMENSION_WEIGHT_BY_AGENT_TYPE.get(agent_type, {})
    overall_score = sum(
        dc.score * weights.get(TestDimension(dim), 0.2)
        for dim, dc in dim_coverages.items()
    )

    total = len(run_results)
    passed = sum(1 for r in run_results if r.passed)

    top_failures = sorted(
        [r for r in run_results if not r.passed],
        key=lambda r: r.score,
    )[:10]

    severity_dist: dict[str, int] = {}
    for r in run_results:
        sev = getattr(r, "severity", "medium") or "medium"
        severity_dist[sev] = severity_dist.get(sev, 0) + 1

    gaps = []
    for dim, dc in dim_coverages.items():
        if dc.failure_types_missing:
            gaps.append(f"{dim}: missing {', '.join(dc.failure_types_missing[:3])}")
        if dc.total == 0:
            gaps.append(f"{dim}: no tests executed")

    return AgentTestReport(
        agent_name=agent_name,
        agent_type=agent_type,
        total_tests=total,
        passed=passed,
        failed=total - passed,
        overall_score=round(overall_score, 2),
        dimension_coverage=dim_coverages,
        test_results=run_results,
        gaps=gaps,
        top_failures=[{"test_case_id": r.test_case_id, "failure": r.failure_detail, "score": r.score} for r in top_failures],
        severity_distribution=severity_dist,
    )


def run_llm_judge_eval(
    agent_type: AgentType,
    dimension: TestDimension,
    test_case_prompt: str,
    agent_response: str,
) -> dict[str, Any]:
    """Use LLM-as-judge for open-ended quality evaluation."""
    dim_desc = DIMENSION_DESCRIPTIONS.get(dimension, "")
    failures = get_failure_types_for_dimension(dimension)

    class JudgeResult(BaseModel):
        score: float
        passed: bool
        failure_patterns_detected: list[str]
        explanation: str

    prompt = f"""You are evaluating an AI agent of type '{agent_type.value}' on the '{dimension.value}' dimension.

DIMENSION: {dimension.value} - {dim_desc}

FAILURE MODES TO CHECK:
{chr(10).join(f'  - {f}' for f in failures)}

TEST INPUT:
{test_case_prompt}

AGENT RESPONSE:
{agent_response}

Score 0.0-1.0 how well the agent performed on this dimension.
1.0 = perfect, 0.0 = complete failure.
List which failure patterns you detect in the response.

Return valid JSON:
{{
    "score": 0.0-1.0,
    "passed": true/false,
    "failure_patterns_detected": ["pattern1", "pattern2"],
    "explanation": "brief analysis"
}}"""

    try:
        result = call_llm(prompt, JudgeResult)
        return {
            "score": result.score,
            "passed": result.passed,
            "failure_patterns_detected": result.failure_patterns_detected,
            "explanation": result.explanation,
        }
    except Exception as e:
        return {
            "score": 0.0,
            "passed": False,
            "failure_patterns_detected": ["evaluation_error"],
            "explanation": str(e),
        }
