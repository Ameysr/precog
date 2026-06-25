"""Report generator. Produces structured coverage reports and pass/fail summaries."""

from datetime import datetime
from pathlib import Path

from agent_types import AgentType, TestDimension
from schemas import AgentTestReport
from utils import save_json


def generate_report_summary(report: AgentTestReport) -> str:
    lines = []
    lines.append("=" * 55)
    lines.append(f"AGENT TEST REPORT: {report.agent_name}")
    lines.append(f"Agent Type: {report.agent_type.value}")
    lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 55)

    status = "PASS" if report.overall_score >= 0.7 else "FAIL"
    lines.append(f"[{status}] Overall Score: {report.overall_score:.0%}")
    lines.append(f"  Tests: {report.passed}/{report.total_tests} passed ({report.failed} failed)")
    lines.append(f"")

    lines.append("DIMENSION COVERAGE:")
    for dim_name, dc in report.dimension_coverage.items():
        d = TestDimension(dim_name)
        pct = f"{dc.score:.0%}" if dc.total > 0 else "N/A"
        icon = "[PASS]" if dc.passed == dc.total and dc.total > 0 else "[FAIL]"
        lines.append(f"  {icon} {d.value:25s} | score: {pct:>5s}  | {dc.passed}/{dc.total} passed | {len(dc.failure_types_tested)}/{len(dc.failure_types_tested)+len(dc.failure_types_missing)} failure types")
        if dc.failure_types_missing:
            lines.append(f"      Untested failure types: {', '.join(dc.failure_types_missing[:5])}")

    if report.gaps:
        lines.append(f"")
        lines.append("GAPS:")
        for g in report.gaps:
            lines.append(f"  - {g}")

    if report.top_failures:
        lines.append(f"")
        lines.append("TOP FAILURES:")
        for f in report.top_failures[:5]:
            lines.append(f"  - {f['test_case_id']}: {f['failure'] or 'no detail'} (score: {f['score']})")

    if report.severity_distribution:
        lines.append(f"")
        lines.append("SEVERITY DISTRIBUTION:")
        for sev, count in sorted(report.severity_distribution.items()):
            lines.append(f"  {sev}: {count}")

    lines.append("=" * 55)
    return "\n".join(lines)


def save_report(report: AgentTestReport, filename: str | None = None) -> Path:
    if filename is None:
        filename = f"{report.agent_name.lower().replace(' ', '-')}_test_report.json"

    payload = {
        "agent_name": report.agent_name,
        "agent_type": report.agent_type.value,
        "generated_at": datetime.now().isoformat(),
        "overall_score": report.overall_score,
        "total_tests": report.total_tests,
        "passed": report.passed,
        "failed": report.failed,
        "dimension_coverage": {
            dim: {
                "score": dc.score,
                "passed": dc.passed,
                "total": dc.total,
                "tested_types": dc.failure_types_tested,
                "missing_types": dc.failure_types_missing,
            }
            for dim, dc in report.dimension_coverage.items()
        },
        "gaps": report.gaps,
        "top_failures": report.top_failures[:20],
        "severity_distribution": report.severity_distribution,
        "test_results": [
            {
                "test_case_id": r.test_case_id,
                "dimension": r.dimension.value,
                "passed": r.passed,
                "score": r.score,
                "failure": r.failure_detail,
                "context_retention_score": r.context_retention_score,
                "tool_call_accuracy": r.tool_call_accuracy,
            }
            for r in report.test_results
        ],
    }

    return save_json(payload, filename=filename)
