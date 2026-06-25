from __future__ import annotations

from pydantic import BaseModel, Field

from agent_types import AgentType, TestDimension


class TestCase(BaseModel):
    id: str = ""
    agent_type: AgentType = AgentType.CONVERSATIONAL
    dimension: TestDimension = TestDimension.QUALITY
    scenario_label: str = ""
    scenario_description: str = ""
    prompt_sequence: list[str] = Field(default_factory=list)
    expected_tool_calls: list[dict] | None = None
    expected_response_patterns: list[str] = Field(default_factory=list)
    forbidden_response_patterns: list[str] = Field(default_factory=list)
    context_requirements: list[str] = Field(default_factory=list)
    failure_mode: str = ""
    severity: str = "medium"
    persona_match: str = ""
    intent_match: str = ""
    intent_match_id: str = ""
    source_review: str | None = None
    verification_scenarios: list[str] = Field(default_factory=list)
    why_it_matters: str = ""


class TestRunResult(BaseModel):
    test_case_id: str
    dimension: TestDimension
    agent_type: AgentType
    passed: bool
    score: float = 0.0  # 0.0 - 1.0
    actual_responses: list[str] = Field(default_factory=list)
    actual_tool_calls: list[dict] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    failure_detail: str | None = None
    context_retention_score: float | None = None
    tool_call_accuracy: float | None = None


class DimensionCoverage(BaseModel):
    dimension: TestDimension
    total: int = 0
    passed: int = 0
    failed: int = 0
    score: float = 0.0  # weighted
    failure_types_tested: list[str] = Field(default_factory=list)
    failure_types_missing: list[str] = Field(default_factory=list)


class AgentTestReport(BaseModel):
    agent_name: str = ""
    agent_type: AgentType = AgentType.CONVERSATIONAL
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    overall_score: float = 0.0
    dimension_coverage: dict[str, DimensionCoverage] = Field(default_factory=dict)
    test_results: list[TestRunResult] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    top_failures: list[dict] = Field(default_factory=list)
    severity_distribution: dict[str, int] = Field(default_factory=dict)


class ProbeResult(BaseModel):
    probe_id: str
    prompts: list[str]
    responses: list[str]
    tool_calls: list[dict]
    discovered_failures: list[str]
    confidence: float
