"""Precog v2 — Universal Agent Test Suite Generator + Runner.
Works for any agent type: conversational, execution, workflow, RAG, autonomous.
Probes → generates test cases → runs → reports pass/fail per dimension."""

import re
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from agent_protocol import create_adapter
from agent_types import AgentType, TestDimension
from classifier import classify_reviews, build_test_suite, classify_for_agent
from config import AGENT_ENDPOINT, AGENT_TYPE, AGENT_ADAPTER, AGENT_API_KEY, AGENT_MODEL
from evaluator import evaluate_overall
from memory_tests import generate_memory_tests
from correctness_tests import generate_correctness_tests
from safety_tests import generate_safety_tests
from reliability_tests import generate_reliability_tests
from probe import probe_agent
from report import generate_report_summary, save_report
from runner import TestRunner
from profiler import build_profile
from scraper import discover_urls, scrape_pages
from sectors import get_sector_for_business_type, load_sector_raw_reviews
from taxonomy import get_intents_for_sector
from utils import save_json


def _resolve_agent_type(hint: str | None) -> AgentType:
    if hint:
        try:
            return AgentType(hint.lower())
        except ValueError:
            pass
    try:
        return AgentType(AGENT_TYPE.lower())
    except ValueError:
        return AgentType.CONVERSATIONAL


def main():
    print("=" * 55)
    print("PRECOG v2 — Universal Agent Test Suite")
    print("=" * 55)

    agent_endpoint = input(f"Agent endpoint [{AGENT_ENDPOINT}]: ").strip() or AGENT_ENDPOINT
    agent_type_hint = input(f"Agent type (conversational/execution/workflow/rag/autonomous) [{AGENT_TYPE}]: ").strip() or AGENT_TYPE
    agent_type = _resolve_agent_type(agent_type_hint)

    company_url = input("Company URL (optional for profile): ").strip()
    if company_url and not company_url.startswith("http"):
        company_url = "https://" + company_url

    run_probe = input("Probe agent first to discover flaws? (y/N): ").strip().lower() == "y"
    run_tests = input("Run generated tests against agent? (Y/n): ").strip().lower() != "n"

    adapter = create_adapter(
        adapter_type=AGENT_ADAPTER,
        endpoint=agent_endpoint,
        api_key=AGENT_API_KEY,
        model=AGENT_MODEL,
    )
    agent_name = adapter.name

    discovered_flaws = []
    if run_probe:
        print(f"\n{'='*55}")
        print(f"PHASE 0: PROBE AGENT")
        print(f"{'='*55}")
        probe_results = probe_agent(adapter, agent_type)
        discovered_flaws = [
            {"probe_id": pr.probe_id, "failures": pr.discovered_failures, "confidence": pr.confidence}
            for pr in probe_results if pr.discovered_failures
        ]
        if discovered_flaws:
            print(f"\n  Discovered {len(discovered_flaws)} flaw patterns from probing.")
            for f in discovered_flaws:
                print(f"    - {f['probe_id']}: {', '.join(f['failures'])} (confidence: {f['confidence']})")
        else:
            print(f"\n  No obvious flaws detected during probing.")

    profile = None
    sector = None
    raw_reviews = []

    if company_url:
        print(f"\n{'='*55}")
        print(f"PHASE 1: UNDERSTAND COMPANY")
        print(f"{'='*55}")
        urls = discover_urls(company_url)
        if urls:
            pages = scrape_pages(urls)
            if pages:
                profile = build_profile(pages, company_url)
                print(f"  Business: {profile.business_type}")
                print(f"  Personas: {[p.name for p in profile.personas]}")
                print(f"  Intents: {[i.name for i in profile.intents]}")

                print(f"\n{'='*55}")
                print(f"PHASE 2: MATCH SECTOR + LOAD REVIEWS")
                print(f"{'='*55}")
                bt = profile.business_type if hasattr(profile, 'business_type') else ""
                sector = get_sector_for_business_type(bt) or get_sector_for_business_type(company_url)
                if sector:
                    raw_reviews = load_sector_raw_reviews(sector)
                    print(f"  Sector: {sector} ({len(raw_reviews)} raw reviews)")
                else:
                    print(f"  No sector match. Will use template-based tests only.")
                    sector = "generic"

    print(f"\n{'='*55}")
    print(f"PHASE 3: GENERATE TEST CASES")
    print(f"{'='*55}")

    all_test_cases = []

    mem_tests = generate_memory_tests(agent_type=agent_type, sector=sector)
    all_test_cases.extend(mem_tests)
    print(f"  Memory tests: {len(mem_tests)}")

    corr_tests = generate_correctness_tests(agent_type=agent_type, domain=sector or "fintech")
    all_test_cases.extend(corr_tests)
    print(f"  Correctness tests: {len(corr_tests)}")

    safe_tests = generate_safety_tests(agent_type=agent_type)
    all_test_cases.extend(safe_tests)
    print(f"  Safety tests: {len(safe_tests)}")

    reli_tests = generate_reliability_tests(agent_type=agent_type)
    all_test_cases.extend(reli_tests)
    print(f"  Reliability tests: {len(reli_tests)}")

    if profile and sector and raw_reviews:
        print(f"  Classifying real reviews as quality tests...")
        from classifier import classify_for_agent
        review_tests = classify_for_agent(profile, sector, agent_type=agent_type, sample_size=30)
        all_test_cases.extend(review_tests)
        print(f"  Review-based tests: {len(review_tests)}")

    print(f"  Total: {len(all_test_cases)} test cases")

    for i, tc in enumerate(all_test_cases):
        tc.id = f"tc_{i:04d}_{tc.dimension.value}_{tc.failure_mode}"

    save_json(
        [tc.model_dump() for tc in all_test_cases],
        filename=f"{agent_name.lower().replace(' ', '-')}_generated_tests.json",
    )

    if run_tests:
        print(f"\n{'='*55}")
        print(f"PHASE 4: RUN TESTS AGAINST AGENT")
        print(f"{'='*55}")

        runner = TestRunner(adapter)
        results = runner.run_suite(all_test_cases)

        print(f"\n{'='*55}")
        print(f"PHASE 5: EVALUATE & REPORT")
        print(f"{'='*55}")

        report = evaluate_overall(results, agent_type=agent_type, agent_name=agent_name)

        print(f"\n{generate_report_summary(report)}")

        save_report(report)

        if discovered_flaws:
            print(f"\nValidated flaws from probing:")
            for f in discovered_flaws:
                related_results = [r for r in results if r.test_case_id.endswith(f['probe_id']) or f['probe_id'] in r.test_case_id]
                validated = sum(1 for r in related_results if not r.passed)
                print(f"  - {f['probe_id']}: {validated}/{len(related_results)} confirmed" if related_results else f"  - {f['probe_id']}: not specifically tested")
    else:
        print(f"\n  Tests saved to output/. Run with --run to execute against agent.")

    print(f"\n{'='*55}")
    print(f"DONE")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
