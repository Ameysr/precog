"""Classifies real reviews by persona, intent, severity, and what agent capability they test."""

import json
import random
from pathlib import Path

from pydantic import BaseModel

from utils import call_llm, save_json
from sectors import load_sector_raw_reviews

OUTPUT_DIR = Path("output")


class ClassifiedReview(BaseModel):
    review_text: str
    source_company: str
    persona_match: str
    persona_confidence: str
    intent_match: str
    intent_confidence: str
    severity: str
    tests_capability: str
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

    personas_str = "\n".join(
        f"  - {p.name}: {p.description}. Traits: {', '.join(p.traits)}. Frustration triggers: {', '.join(p.frustration_triggers)}"
        for p in profile.personas
    )
    intents_str = "\n".join(
        f"  - {i.name}: {i.description}. Failure modes: {', '.join(i.failure_modes)}"
        for i in profile.intents
    )

    all_classified = []
    batch_size = 5

    for i in range(0, len(sampled), batch_size):
        batch = sampled[i:i + batch_size]
        batch_text = "\n\n".join(
            f"REVIEW {j}: [{r.get('source_company', 'unknown')}] {r['text']}"
            for j, r in enumerate(batch)
        )

        prompt = f"""You are classifying real user reviews for an AI agent that serves {profile.company_name}.

The agent handles these customer personas:
{personas_str}

The agent handles these customer intents:
{intents_str}

Classify each review below by:
1. persona_match: Which persona from the list above does this review match BEST? (choose one)
2. persona_confidence: How confident are you? (high/medium/low)
3. intent_match: Which intent from the list above does this review match BEST? (choose one)
4. intent_confidence: high/medium/low
5. severity: What frustration level does this review show? (mild/medium/high/rage)
6. tests_capability: What specific agent capability does this review stress-test? (e.g. "handling billing disputes", "KYC verification flow", "cancellation process")
7. why_it_matters: One sentence on why this is an important test case

Reviews:
{batch_text}

Return ONLY valid JSON matching this schema:
{{
  "reviews": [
    {{
      "review_text": "full review text",
      "source_company": "source company name",
      "persona_match": "persona name",
      "persona_confidence": "high/medium/low",
      "intent_match": "intent name",
      "intent_confidence": "high/medium/low",
      "severity": "mild/medium/high/rage",
      "tests_capability": "what it stress-tests",
      "why_it_matters": "why important"
    }}
  ]
}}"""

        try:
            result = call_llm(prompt, BatchClassification)
            for r in result.reviews:
                # Attach original text if model truncated
                original = next(
                    (rr["text"] for rr in batch if rr["text"].startswith(r.review_text[:50])),
                    r.review_text,
                )
                if len(original) > len(r.review_text):
                    r.review_text = original
            all_classified.extend(result.reviews)
            print(f"    Batch {i//batch_size + 1}/{(len(sampled)-1)//batch_size + 1}: {len(result.reviews)} classified")
        except Exception as e:
            print(f"    Batch {i//batch_size + 1} failed: {e}")
            continue

    return all_classified


def build_test_suite(classifier_results: list[ClassifiedReview], profile) -> dict:
    """Organize classified reviews into a structured test suite with coverage report."""
    by_intent = {}
    by_severity = {"mild": [], "medium": [], "high": [], "rage": []}
    by_persona = {}

    for r in classifier_results:
        by_intent.setdefault(r.intent_match, []).append(r.model_dump())
        by_severity.setdefault(r.severity, []).append(r.model_dump())
        by_persona.setdefault(r.persona_match, []).append(r.model_dump())

    # Coverage report
    profile_intents = [i.name for i in profile.intents]
    profile_personas = [p.name for p in profile.personas]

    covered_intents = [i for i in profile_intents if i in by_intent]
    missing_intents = [i for i in profile_intents if i not in by_intent]

    covered_personas = [p for p in profile_personas if p in by_persona]
    missing_personas = [p for p in profile_personas if p not in by_persona]

    suite = {
        "target_company": profile.company_name,
        "sector": getattr(profile, "business_type", "unknown"),
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "coverage": {
            "intents": {
                "total": len(profile_intents),
                "covered": len(covered_intents),
                "missing": missing_intents,
                "pct": round(len(covered_intents) / len(profile_intents) * 100) if profile_intents else 0,
            },
            "personas": {
                "total": len(profile_personas),
                "covered": len(covered_personas),
                "missing": missing_personas,
                "pct": round(len(covered_personas) / len(profile_personas) * 100) if profile_personas else 0,
            },
            "total_test_cases": len(classifier_results),
            "by_severity": {k: len(v) for k, v in by_severity.items()},
        },
        "test_cases": [r.model_dump() for r in classifier_results],
        "gaps": {
            "untested_intents": missing_intents,
            "untested_personas": missing_personas,
            "recommendation": _generate_recommendation(missing_intents, missing_personas),
        },
    }

    path = save_json(
        suite,
        filename=f"{profile.company_name.lower().replace(' ', '-')}_test_suite.json",
    )
    print(f"\n  Coverage: {suite['coverage']['intents']['pct']}% intents, {suite['coverage']['personas']['pct']}% personas")
    if missing_intents:
        print(f"  Gaps: untested intents — {', '.join(missing_intents)}")
    if missing_personas:
        print(f"  Gaps: untested personas — {', '.join(missing_personas)}")

    return suite


def _generate_recommendation(missing_intents: list[str], missing_personas: list[str]) -> str:
    parts = []
    if missing_intents:
        parts.append(f"Add test cases for missing intents: {', '.join(missing_intents)}")
    if missing_personas:
        parts.append(f"Find reviews targeting these personas: {', '.join(missing_personas)}")
    if not parts:
        parts.append("Full coverage achieved. Consider adding edge case reviews.")
    return " | ".join(parts)
