"""Agent-type and dimension-aware classifier. Generates test cases for any agent type across all dimensions."""

import json
import random
import re
from pathlib import Path

from pydantic import BaseModel

from utils import call_llm, save_json
from sectors import load_sector_raw_reviews
from taxonomy import get_intents_for_sector, get_taxonomy_for_agent, generate_dimension_test_templates
from agent_types import AgentType, TestDimension, DIMENSION_DESCRIPTIONS, get_failure_types_for_dimension
from schemas import TestCase

OUTPUT_DIR = Path("output")

GIBBERISH_PATTERNS = [
    r"everyone algorithms",
    r"everyone alogorithms",
    r"soo much faster download",
    r"thank you so much to everyone",
    r"\u2764\ufe0f",
    r"bhot vadia",
    r"nice ho",
]


class ClassifiedReview(BaseModel):
    review_text: str
    source_company: str
    is_positive: bool
    persona_match: str
    intent_match: str
    intent_match_id: str
    dimension: str
    failure_mode: str
    severity: str
    current_bad_response: str
    expected_agent_behavior: list[str]
    tests_capability: str
    verification_scenarios: list[str]
    why_it_matters: str


class BatchClassification(BaseModel):
    reviews: list[ClassifiedReview]


def _is_gibberish(text: str) -> bool:
    text_lower = text.lower()
    for p in GIBBERISH_PATTERNS:
        if re.search(p, text_lower):
            return True
    words = text.split()
    if len(words) < 4 and len(text) < 30:
        return True
    if len(set(words)) / max(len(words), 1) < 0.3 and len(words) > 5:
        return True
    return False


def _build_dimension_prompt_section(agent_type: AgentType) -> str:
    lines = []
    for dim in TestDimension:
        desc = DIMENSION_DESCRIPTIONS[dim]
        failures = get_failure_types_for_dimension(dim)
        lines.append(f"  - {dim.value}: {desc}")
        lines.append(f"    Failure modes: {', '.join(failures)}")
    return "\n".join(lines)


def classify_reviews(
    sector_name: str,
    profile,
    sample_size: int = 100,
    agent_type: AgentType = AgentType.CONVERSATIONAL,
    target_dimension: TestDimension | None = None,
) -> list[ClassifiedReview]:
    raw_reviews = load_sector_raw_reviews(sector_name)
    if not raw_reviews:
        return []

    clean = [r for r in raw_reviews if not _is_gibberish(r.get("text", ""))]
    removed = len(raw_reviews) - len(clean)
    if removed:
        print(f"  Filtered {removed} gibberish reviews")

    sampled = random.sample(clean, min(sample_size, len(clean)))
    print(f"  Classifying {len(sampled)} reviews for {agent_type.value} / {target_dimension.value if target_dimension else 'all'}...")

    taxonomy_intents = get_intents_for_sector(sector_name)

    personas_str = "\n".join(
        f"  - {p.name}: {p.description}"
        for p in profile.personas
    )
    intents_str = "\n".join(
        f"  - [{t['id']}] {t['name']}: {t['description']}."
        for t in taxonomy_intents
    )

    dim_section = _build_dimension_prompt_section(agent_type)

    all_classified = []
    batch_size = 5

    for i in range(0, len(sampled), batch_size):
        batch = sampled[i:i + batch_size]
        batch_text = "\n\n".join(
            f"REVIEW {j}: [{r.get('source_company', 'unknown')}] {r['text']}"
            for j, r in enumerate(batch)
        )

        prompt = f"""You are building a test suite for {profile.company_name}'s AI agent.
Agent type: {agent_type.value} - {agent_type.value} agent

PERSONAS served by this agent:
{personas_str}

INTENTS (use [id] to tag):
{intents_str}

TEST DIMENSIONS with failure modes (classify each review into the BEST dimension):
{dim_section}

For EACH review, provide:

1. is_positive: true if purely positive/praise with no issue.
2. persona_match: Which persona matches best?
3. intent_match_id: Which intent ID matches? Choose closest.
4. intent_match: Human-readable name of that intent.
5. dimension: Which test dimension best fits? memory_context / correctness / safety / reliability / quality
6. failure_mode: Which specific failure mode from that dimension does this show?
7. severity: mild / medium / high / rage
8. current_bad_response: What a BAD agent might say (1 sentence).
9. expected_agent_behavior: List 2-4 concrete actions for an {agent_type.value} agent.
10. tests_capability: "domain:action" format.
11. verification_scenarios: 2-3 concrete verification scenarios.
12. why_it_matters: One sentence on why this case is important.

LABELING RULES:
- Bus/service complaints -> merchant_service_dispute or general_quality
- UI/UX complaints -> ux_discoverability (quality dimension)
- Payment success but reward missing -> referral_or_reward_dispute
- Positive reviews -> is_positive=true, intent_match_id="no_failure", failure_mode="positive_sentiment"

Reviews:
{batch_text}

Return ONLY valid JSON matching this schema:
{{
  "reviews": [
    {{
      "review_text": "...",
      "source_company": "...",
      "is_positive": false,
      "persona_match": "...",
      "intent_match": "...",
      "intent_match_id": "...",
      "dimension": "memory_context/correctness/safety/reliability/quality",
      "failure_mode": "...",
      "severity": "mild/medium/high/rage",
      "current_bad_response": "...",
      "expected_agent_behavior": ["action1", "action2"],
      "tests_capability": "domain:action",
      "verification_scenarios": ["scenario1", "scenario2"],
      "why_it_matters": "..."
    }}
  ]
}}"""

        try:
            result = call_llm(prompt, BatchClassification)
            all_classified.extend(result.reviews)
            print(f"    Batch {i//batch_size + 1}/{(len(sampled)-1)//batch_size + 1}: {len(result.reviews)} classified")
        except Exception as e:
            print(f"    Batch {i//batch_size + 1} failed: {e}")
            continue

    return all_classified


def build_test_suite(
    classified: list[ClassifiedReview],
    profile,
    agent_type: AgentType = AgentType.CONVERSATIONAL,
) -> dict:
    by_intent_id = {}
    by_severity = {"mild": [], "medium": [], "high": [], "rage": []}
    by_dimension = {d.value: [] for d in TestDimension}
    by_failure_mode = {}
    positives = []
    negatives = []

    for r in classified:
        d = r.model_dump()
        if r.is_positive:
            positives.append(d)
        else:
            negatives.append(d)
            by_intent_id.setdefault(r.intent_match_id, []).append(d)
            dim_key = r.dimension if r.dimension in by_dimension else "quality"
            by_dimension[dim_key].append(d)
            by_severity.setdefault(r.severity, []).append(d)
            by_failure_mode.setdefault(r.failure_mode, []).append(d)

    from sectors import get_sector_for_business_type
    sector = get_sector_for_business_type(profile.business_type) or get_sector_for_business_type(profile.company_name) or "unknown"
    taxonomy_intents = get_intents_for_sector(sector)
    taxonomy_ids = [t["id"] for t in taxonomy_intents]

    covered_ids = list(set(by_intent_id.keys()))
    missing_ids = [i for i in taxonomy_ids if i not in covered_ids]

    dimension_stats = {}
    for dim in TestDimension:
        cases = by_dimension.get(dim.value, [])
        all_failure_types = set(get_failure_types_for_dimension(dim))
        tested_types = set(c["failure_mode"] for c in cases)
        dimension_stats[dim.value] = {
            "total_cases": len(cases),
            "failure_types_tested": sorted(tested_types),
            "failure_types_missing": sorted(all_failure_types - tested_types),
            "pct_coverage": round(len(tested_types) / len(all_failure_types) * 100) if all_failure_types else 0,
        }

    suite = {
        "target_company": profile.company_name,
        "agent_type": agent_type.value,
        "sector": sector,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "coverage": {
            "granular_intents": {
                "total": len(taxonomy_ids),
                "covered": len([i for i in taxonomy_ids if i in covered_ids]),
                "missing": missing_ids,
                "pct": round(len([i for i in taxonomy_ids if i in covered_ids]) / len(taxonomy_ids) * 100) if taxonomy_ids else 0,
            },
            "dimensions": dimension_stats,
            "failure_modes": {
                "total": sum(len(t["failure_modes"]) for t in taxonomy_intents),
                "unique_tested": len(by_failure_mode),
            },
            "total_test_cases": len(classified),
            "failure_cases": len(negatives),
            "positive_praise_cases": len(positives),
            "by_severity": {k: len(v) for k, v in by_severity.items()},
        },
        "test_cases_negative": negatives,
        "test_cases_positive": positives,
        "gaps": {
            "untested_intents": missing_ids,
            "note": "These intents have zero test cases. No agent behavior data exists for them.",
        },
    }

    path = save_json(
        suite,
        filename=f"{profile.company_name.lower().replace(' ', '-')}_test_suite.json",
    )
    print(f"\n  Coverage: {suite['coverage']['granular_intents']['pct']}% intents")
    print(f"  Dimensions: {{k: v['total_cases'] for k, v in dimension_stats.items()}}")
    print(f"  Failure modes tested: {suite['coverage']['failure_modes']['unique_tested']} unique")
    print(f"  Severity: {suite['coverage']['by_severity']}")
    if missing_ids:
        print(f"  Gaps: {', '.join(missing_ids)}")

    return suite


def classify_for_agent(
    profile,
    sector_name: str,
    agent_type: AgentType = AgentType.CONVERSATIONAL,
    sample_size: int = 100,
) -> list[TestCase]:
    classified = classify_reviews(
        sector_name=sector_name,
        profile=profile,
        sample_size=sample_size,
        agent_type=agent_type,
    )
    test_cases = []
    for c in classified:
        try:
            dim = TestDimension(c.dimension) if c.dimension in [d.value for d in TestDimension] else TestDimension.QUALITY
        except ValueError:
            dim = TestDimension.QUALITY
        test_cases.append(TestCase(
            agent_type=agent_type,
            dimension=dim,
            scenario_label=f"{c.intent_match_id}:{c.failure_mode}",
            scenario_description=c.review_text[:200],
            prompt_sequence=[c.review_text],
            failure_mode=c.failure_mode,
            severity=c.severity,
            persona_match=c.persona_match,
            intent_match=c.intent_match,
            intent_match_id=c.intent_match_id,
            source_review=c.review_text,
            verification_scenarios=c.verification_scenarios,
            why_it_matters=c.why_it_matters,
            expected_tool_calls=None,
            expected_response_patterns=c.expected_agent_behavior,
        ))
    return test_cases
