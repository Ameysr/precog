"""Classifies real reviews with granular intent taxonomy, atomic failure modes, and expected behaviors."""

import json
import random
from pathlib import Path

from pydantic import BaseModel

from utils import call_llm, save_json
from sectors import load_sector_raw_reviews
from taxonomy import get_intents_for_sector

OUTPUT_DIR = Path("output")


class ClassifiedReview(BaseModel):
    review_text: str
    source_company: str
    persona_match: str
    intent_match: str
    intent_match_id: str
    failure_mode: str
    severity: str
    tests_capability: str
    expected_agent_behavior: list[str]
    why_it_matters: str


class BatchClassification(BaseModel):
    reviews: list[ClassifiedReview]


def classify_reviews(
    sector_name: str,
    profile,
    sample_size: int = 100,
) -> list[ClassifiedReview]:
    raw_reviews = load_sector_raw_reviews(sector_name)
    if not raw_reviews:
        print(f"  [!] No raw reviews found for sector '{sector_name}'")
        return []

    sampled = random.sample(raw_reviews, min(sample_size, len(raw_reviews)))
    print(f"  Classifying {len(sampled)} reviews...")

    # Load rich taxonomy (use ALL intents for this sector)
    taxonomy_intents = get_intents_for_sector(sector_name)

    personas_str = "\n".join(
        f"  - {p.name}: {p.description}. Traits: {', '.join(p.traits)}. Frustration triggers: {', '.join(p.frustration_triggers)}"
        for p in profile.personas
    )
    intents_str = "\n".join(
        f"  - [{t['id']}] {t['name']}: {t['description']}. Failure modes: {', '.join(t['failure_modes'][:4])}."
        for t in taxonomy_intents
    )

    all_classified = []
    batch_size = 5

    for i in range(0, len(sampled), batch_size):
        batch = sampled[i:i + batch_size]
        batch_text = "\n\n".join(
            f"REVIEW {j}: [{r.get('source_company', 'unknown')}] {r['text']}"
            for j, r in enumerate(batch)
        )

        prompt = f"""You are classifying real user reviews for {profile.company_name}'s AI customer support agent.

This company serves these customer personas:
{personas_str}

The agent handles these granular intents (use the [id] to tag):
{intents_str}

For EACH review, classify into:

1. persona_match: Which persona matches BEST? Choose from the list above.
2. intent_match_id: Which intent ID matches BEST? Choose from the [id] list above.
3. intent_match: The human-readable name of that intent.
4. failure_mode: Which SPECIFIC failure mode from that intent's list does this review show? Choose the closest match.
5. severity: User's emotional state — mild (annoyed but calm) / medium (clearly frustrated) / high (very angry) / rage (screaming, threats).
6. tests_capability: What SPECIFIC agent capability does this stress-test? Use format: "domain:action"
   Examples: "order_execution:slippage_acknowledgment", "kyc:document_upload_handling", "withdrawal:bank_credit_timeline", "charts:historical_data_retrieval"
7. expected_agent_behavior: List 3-4 specific actions the agent SHOULD take. Be concrete.
   Examples: ["acknowledge user frustration","request order_id to trace","explain LTP vs limit order","offer RMS escalation"]
8. why_it_matters: One specific sentence about what makes this a valuable test case for an auto-fix system.

CRITICAL RULES:
- intent_match_id must be ONE of the IDs listed above (e.g., "order_execution_delay", "kyc_verification_status")
- failure_mode must be ONE of the failure modes listed for that intent
- expected_agent_behavior must be concrete actions, not vague promises
- DO NOT use generic categories like "technical issues" or "handling complaints"

Reviews:
{batch_text}

Return ONLY valid JSON matching this schema:
{{
  "reviews": [
    {{
      "review_text": "full text",
      "source_company": "source name",
      "persona_match": "persona name",
      "intent_match": "intent name",
      "intent_match_id": "intent id",
      "failure_mode": "specific failure mode",
      "severity": "mild/medium/high/rage",
      "tests_capability": "domain:action format",
      "expected_agent_behavior": ["action1", "action2", "action3"],
      "why_it_matters": "specific reason"
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


def build_test_suite(classified: list[ClassifiedReview], profile) -> dict:
    """Organize into structured test suite with coverage report."""
    by_intent_id = {}
    by_severity = {"mild": [], "medium": [], "high": [], "rage": []}
    by_failure_mode = {}

    for r in classified:
        d = r.model_dump()
        by_intent_id.setdefault(r.intent_match_id, []).append(d)
        by_severity.setdefault(r.severity, []).append(d)
        by_failure_mode.setdefault(r.failure_mode, []).append(d)

    from taxonomy import get_intents_for_sector
    from sectors import get_sector_for_business_type
    sector = get_sector_for_business_type(profile.business_type) or get_sector_for_business_type(profile.company_name) or "unknown"
    taxonomy_intents = get_intents_for_sector(sector)
    taxonomy_ids = [t["id"] for t in taxonomy_intents]

    covered_ids = [i for i in taxonomy_ids if i in by_intent_id]
    missing_ids = [i for i in taxonomy_ids if i not in by_intent_id]

    suite = {
        "target_company": profile.company_name,
        "sector": sector,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "coverage": {
            "granular_intents": {
                "total": len(taxonomy_ids),
                "covered": len(covered_ids),
                "missing": missing_ids,
                "pct": round(len(covered_ids) / len(taxonomy_ids) * 100) if taxonomy_ids else 0,
            },
            "failure_modes": {
                "total": sum(len(t["failure_modes"]) for t in taxonomy_intents),
                "unique_tested": len(by_failure_mode),
            },
            "total_test_cases": len(classified),
            "by_severity": {k: len(v) for k, v in by_severity.items()},
        },
        "test_cases": [r.model_dump() for r in classified],
        "gaps": {
            "untested_intents": missing_ids,
            "recommendation": _generate_recommendation(missing_ids, taxonomy_intents),
        },
    }

    path = save_json(
        suite,
        filename=f"{profile.company_name.lower().replace(' ', '-')}_test_suite.json",
    )
    print(f"\n  Coverage: {suite['coverage']['granular_intents']['pct']}% intents ({suite['coverage']['granular_intents']['covered']}/{suite['coverage']['granular_intents']['total']})")
    print(f"  Failure modes tested: {len(by_failure_mode)} unique")
    if missing_ids:
        print(f"  Gaps: {', '.join(missing_ids)}")

    return suite


def _generate_recommendation(missing_ids: list[str], taxonomy: list[dict]) -> str:
    if not missing_ids:
        return "Full coverage achieved."
    details = []
    for mid in missing_ids:
        found = [t for t in taxonomy if t["id"] == mid]
        if found:
            details.append(f"{found[0]['name']} — {found[0]['description']}")
    return "Untested: " + " | ".join(details)
