"""Classifies real reviews with auto-fix-ready schema: has bad response, fix target, verification."""

import json
import random
import re
from pathlib import Path

from pydantic import BaseModel

from utils import call_llm, save_json
from sectors import load_sector_raw_reviews
from taxonomy import get_intents_for_sector

OUTPUT_DIR = Path("output")

GIBBERISH_PATTERNS = [
    r"everyone algorithms",
    r"everyone alogorithms",
    r"soo much faster download",
    r"thank you so much to everyone",
    r"\u2764\ufe0f",  # heart emoji followed by nothing useful
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
    # Check for gibberish: very short, repetitive, or mostly emoji
    words = text.split()
    if len(words) < 4 and len(text) < 30:
        return True
    if len(set(words)) / max(len(words), 1) < 0.3 and len(words) > 5:
        return True
    return False


def _is_positive_review(text: str) -> bool:
    positive_signals = ["love the app", "excellent", "amazing", "soo good", "very nice", "best app", "works perfectly", "great experience", "my favorite"]
    negative_signals = ["please fix", "not working", "issue", "problem", "bug", "error", "frustrat", "worst", "useless", "refund", "money stuck"]
    text_lower = text.lower()
    has_positive = any(s in text_lower for s in positive_signals)
    has_negative = any(s in text_lower for s in negative_signals)
    return has_positive and not has_negative


def classify_reviews(
    sector_name: str,
    profile,
    sample_size: int = 100,
) -> list[ClassifiedReview]:
    raw_reviews = load_sector_raw_reviews(sector_name)
    if not raw_reviews:
        return []

    # Filter gibberish first
    clean = [r for r in raw_reviews if not _is_gibberish(r.get("text", ""))]
    removed = len(raw_reviews) - len(clean)
    if removed:
        print(f"  Filtered {removed} gibberish reviews")

    sampled = random.sample(clean, min(sample_size, len(clean)))
    print(f"  Classifying {len(sampled)} reviews...")

    taxonomy_intents = get_intents_for_sector(sector_name)

    personas_str = "\n".join(
        f"  - {p.name}: {p.description}"
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

        prompt = f"""You are building a test suite for {profile.company_name}'s AI agent. You must classify each real user review with auto-fix information.

PERSONAS served by this agent:
{personas_str}

GRANULAR INTENTS (use [id] to tag):
{intents_str}

For EACH review, provide:

1. is_positive: true if this review is purely positive/praise with no complaint. false if there's any issue reported.
2. persona_match: Which persona from the list matches best?
3. intent_match_id: Which granular intent ID matches? Choose the CLOSEST match even if imperfect.
4. intent_match: Human-readable name of that intent.
5. failure_mode: Which specific failure mode from that intent's list does this show?
6. severity: mild / medium / high / rage
7. current_bad_response: What a BAD agent might say. Imagine a lazy/generic support agent. Write 1 sentence of a dismissive or unhelpful reply. Example: "Please clear your app cache and try again."
8. expected_agent_behavior: List 2-4 concrete actions with tool/API calls. NOT vague steps. Examples:
   - "call_withdrawal_api(transaction_id) → check if age > 24h → if yes, trigger_nodal_escalation()"
   - "query_kyc_status(user_pan) → if 'REJECTED', explain_rejection_reason() → offer_reupload_link()"
   - "pull_gtt_logs(order_id) → compare trigger_price vs LTP_timeline → show_user_timeline()"
9. tests_capability: Single atomic capability in "domain:action" format.
10. verification_scenarios: List 2-3 concrete scenarios that would test this fix.
    Example: ["withdrawal_stuck_3_days_SBI", "withdrawal_stuck_1_day_within_TAT", "withdrawal_processed_but_not_credited"]
11. why_it_matters: One sentence on how this case tests a specific auto-fix capability.

CRITICAL LABELING RULES:
- Bus/service complaints (e.g., bus was late) → NOT fraud. These are merchant_service_dispute or general_quality.
- UI/UX complaints (e.g., button hard to find) → NOT notification_missing. These are ux_discoverability.
- Payment success but reward/cashback missing → NOT dp_charges. These are referral_or_reward_dispute.
- Positive reviews with no issue → is_positive=true, intent_match_id="no_failure", failure_mode="positive_sentiment"
- If no intent matches closely, use the closest match anyway. Prefer false positive over no_match.

Reviews:
{batch_text}

Return ONLY valid JSON matching this schema:
{{
  "reviews": [
    {{
      "review_text": "...",
      "source_company": "...",
      "is_positive": false,
      "persona_match": "persona name",
      "intent_match": "intent name",
      "intent_match_id": "intent id",
      "failure_mode": "failure mode",
      "severity": "mild/medium/high/rage",
      "current_bad_response": "bad agent response",
      "expected_agent_behavior": ["tool_call1", "tool_call2"],
      "tests_capability": "domain:action",
      "verification_scenarios": ["scenario1", "scenario2"],
      "why_it_matters": "reason"
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
    """Organize into auto-fix-ready test suite."""
    by_intent_id = {}
    by_severity = {"mild": [], "medium": [], "high": [], "rage": []}
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
            by_severity.setdefault(r.severity, []).append(d)
            by_failure_mode.setdefault(r.failure_mode, []).append(d)

    from taxonomy import get_intents_for_sector
    from sectors import get_sector_for_business_type
    sector = get_sector_for_business_type(profile.business_type) or get_sector_for_business_type(profile.company_name) or "unknown"
    taxonomy_intents = get_intents_for_sector(sector)
    taxonomy_ids = [t["id"] for t in taxonomy_intents]

    covered_ids = list(set(by_intent_id.keys()))
    missing_ids = [i for i in taxonomy_ids if i not in covered_ids]

    suite = {
        "target_company": profile.company_name,
        "sector": sector,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "coverage": {
            "granular_intents": {
                "total": len(taxonomy_ids),
                "covered": len([i for i in taxonomy_ids if i in covered_ids]),
                "missing": missing_ids,
                "pct": round(len([i for i in taxonomy_ids if i in covered_ids]) / len(taxonomy_ids) * 100) if taxonomy_ids else 0,
            },
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
    print(f"\n  Coverage: {suite['coverage']['granular_intents']['pct']}% intents ({suite['coverage']['granular_intents']['covered']}/{suite['coverage']['granular_intents']['total']})")
    print(f"  Failure modes tested: {suite['coverage']['failure_modes']['unique_tested']} unique")
    print(f"  Severity distribution: {suite['coverage']['by_severity']}")
    if missing_ids:
        print(f"  Gaps: {', '.join(missing_ids)}")

    return suite
