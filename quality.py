"""Quality checks for generated test cases — validates coverage across all 5 dimensions."""

import re
from pathlib import Path

from agent_types import AgentType, TestDimension, get_failure_types_for_dimension, DIMENSION_WEIGHT_BY_AGENT_TYPE
from schemas import TestCase

OUTPUT_DIR = Path("output")


def check_vocabulary_diversity(conversations: list[dict]) -> dict:
    all_words = []
    for c in conversations:
        for msg in c.get("user_messages", []):
            words = re.findall(r"\w+", msg.lower())
            all_words.extend(words)
    if not all_words:
        return {"pass": False, "ttr": 0, "total": 0, "unique": 0}
    total = len(all_words)
    unique = len(set(all_words))
    ttr = unique / total if total > 0 else 0
    return {"pass": ttr > 0.35, "ttr": round(ttr, 3), "total": total, "unique": unique}


def check_sentence_starters(conversations: list[dict]) -> dict:
    banned = {"can you", "this is", "i'm trying to", "i want", "i need", "could you"}
    bad_count = 0
    total = 0
    starter_counts = {}
    for c in conversations:
        for msg in c.get("user_messages", []):
            msg = msg.strip().lower()
            if not msg:
                continue
            total += 1
            first_three = " ".join(msg.split()[:3])
            starter_counts[first_three] = starter_counts.get(first_three, 0) + 1
            for b in banned:
                if msg.startswith(b):
                    bad_count += 1
                    break
    return {
        "pass": bad_count < total * 0.15 if total > 0 else True,
        "bad_starter_pct": round(bad_count / total * 100, 1) if total > 0 else 0,
        "top_starters": dict(sorted(starter_counts.items(), key=lambda x: -x[1])[:5]),
    }


def check_all_caps_presence(conversations: list[dict]) -> dict:
    caps_count = 0
    for c in conversations:
        for msg in c.get("user_messages", []):
            words = msg.split()
            caps_words = [w for w in words if w.isupper() and len(w) > 2]
            if caps_words:
                caps_count += 1
                break
    return {
        "pass": caps_count >= len(conversations) * 0.1,
        "conversations_with_caps": caps_count,
        "pct": round(caps_count / len(conversations) * 100, 1) if conversations else 0,
    }


def check_dimension_coverage(test_cases: list[TestCase], agent_type: AgentType = AgentType.CONVERSATIONAL) -> dict:
    dim_counts = {d.value: 0 for d in TestDimension}
    dim_failure_types = {d.value: set() for d in TestDimension}

    for tc in test_cases:
        dim_counts[tc.dimension.value] = dim_counts.get(tc.dimension.value, 0) + 1
        if tc.failure_mode:
            dim_failure_types[tc.dimension.value].add(tc.failure_mode)

    weights = DIMENSION_WEIGHT_BY_AGENT_TYPE.get(agent_type, {})
    dim_coverage = {}
    weighted_score = 0.0

    for dim in TestDimension:
        required_types = set(get_failure_types_for_dimension(dim))
        tested_types = dim_failure_types.get(dim.value, set())
        coverage_pct = round(len(tested_types) / len(required_types) * 100) if required_types else 0
        weight = weights.get(dim, 0.2)
        dim_score = coverage_pct / 100 * weight
        weighted_score += dim_score
        dim_coverage[dim.value] = {
            "test_count": dim_counts.get(dim.value, 0),
            "failure_types_tested": len(tested_types),
            "failure_types_total": len(required_types),
            "coverage_pct": coverage_pct,
            "tested_types": sorted(tested_types),
            "missing_types": sorted(required_types - tested_types),
        }

    total_tests = sum(dim_counts.values())
    return {
        "overall": {
            "pass": weighted_score >= 0.5,
            "weighted_coverage_score": round(weighted_score, 2),
            "total_test_cases": total_tests,
        },
        "by_dimension": dim_coverage,
    }


def run_all_checks(conversations: list[dict], domain_type: str = "") -> dict:
    checks = {
        "vocabulary_diversity": check_vocabulary_diversity(conversations),
        "sentence_starters": check_sentence_starters(conversations),
        "all_caps_presence": check_all_caps_presence(conversations),
    }
    passed = sum(1 for c in checks.values() if c["pass"])
    total = len(checks)
    return {
        "overall": {"pass": passed == total, "passed": passed, "total": total, "score": round(passed / total * 100, 1)},
        "checks": checks,
    }


def print_report(report: dict) -> None:
    print("\n" + "=" * 50)
    print("QUALITY REPORT")
    print("=" * 50)
    status = "PASS" if report["overall"]["pass"] else "FAIL"
    print(f"[{status}] Score: {report['overall']['score']}% ({report['overall']['passed']}/{report['overall']['total']} checks passed)")
    for name, check in report["checks"].items():
        icon = "[PASS]" if check["pass"] else "[FAIL]"
        print(f"  {icon} {name.replace('_', ' ').title()}")
        details = {k: v for k, v in check.items() if k != "pass"}
        for k, v in details.items():
            print(f"      {k}: {v}")
    print("=" * 50)


def print_dimension_report(coverage: dict) -> None:
    print("\n" + "=" * 50)
    print("DIMENSION COVERAGE REPORT")
    print("=" * 50)
    o = coverage["overall"]
    status = "PASS" if o["pass"] else "FAIL"
    print(f"[{status}] Weighted Coverage: {o['weighted_coverage_score']:.0%} ({o['total_test_cases']} total tests)")
    for dim_name, dc in coverage["by_dimension"].items():
        icon = "[PASS]" if dc["coverage_pct"] >= 50 else "[FAIL]"
        print(f"  {icon} {dim_name:25s} {dc['coverage_pct']:>3d}% ({dc['test_count']} tests, {dc['failure_types_tested']}/{dc['failure_types_total']} failure types)")
        if dc["missing_types"]:
            print(f"      Missing: {', '.join(dc['missing_types'][:5])}")
    print("=" * 50)
