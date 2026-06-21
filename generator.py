import json
import random
import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from profiler import CompanyProfile
from utils import call_llm, save_json

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")


class Conversation(BaseModel):
    id: str
    persona: str
    intent: str
    scenario: str
    user_messages: list[str]
    frustration_signals: list[str]
    frustration_level: str
    expected_good_outcome: str


class ConversationBatch(BaseModel):
    conversations: list[Conversation]


USER_CLASSES = [
    {
        "id": "A",
        "name": "Professional English",
        "pct": 0.25,
        "desc": "Educated professional. Speaks fluent English. Formal tone. Detailed explanations. NO Hinglish. NO slang. Uses complete sentences.",
    },
    {
        "id": "B",
        "name": "Hinglish Coder",
        "pct": 0.25,
        "desc": "Mixed Hindi-English. Sporadic code-switching mid-sentence. Emotional. Hindi phrases woven naturally into English, not tacked on. 'Yaar yeh app kaam nahi kar raha, I've tried 5 times'.",
    },
    {
        "id": "C",
        "name": "ALL CAPS Rager",
        "pct": 0.15,
        "desc": "Furious. Short messages. ALL CAPS. Expletives. NO polite words. Direct, aggressive, accusatory. 'THIS APP IS A SCAM. GIVE ME MY MONEY BACK'.",
    },
    {
        "id": "D",
        "name": "Passive Aggressive",
        "pct": 0.15,
        "desc": "Sarcastic, cold, polite on the surface but clearly angry. 'Oh wonderful. Another error message. Just what I needed today.' No shouting, no caps. Icy tone.",
    },
    {
        "id": "E",
        "name": "Confused Newbie",
        "pct": 0.10,
        "desc": "Non-technical user. Doesn't understand terminology. Repeats themselves. Asks same question multiple times. Mild frustration from confusion, not anger.",
    },
    {
        "id": "F",
        "name": "Legal Threatener",
        "pct": 0.10,
        "desc": "Threatens legal action, consumer court, police complaint. Cites regulations. Demands escalation. Formal in tone but threatening in content. 'I will file a complaint with the ombudsman.'",
    },
]

FRUSTRATION_BASELINES = [
    ("mild", 0.20, "Slightly annoyed. User has a minor issue but isn't angry yet. They expect a quick fix."),
    ("medium", 0.30, "Clearly frustrated. Issue has persisted. User is raising their voice but not raging."),
    ("high", 0.30, "Very frustrated. Issue has gone unresolved. User is angry, raising voice, threatening."),
    ("rage", 0.20, "Extremely angry. User has been wronged repeatedly. Screaming, cursing, threatening legal action."),
]

SECTOR_REVIEWS_CACHE: dict[str, list[dict]] = {}


def _load_sector_reviews(sector_name: str) -> list[dict]:
    if sector_name in SECTOR_REVIEWS_CACHE:
        return SECTOR_REVIEWS_CACHE[sector_name]

    path = DATA_DIR / "sectors" / sector_name / "raw_reviews.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        reviews = data.get("reviews", [])
        SECTOR_REVIEWS_CACHE[sector_name] = reviews
        return reviews
    return []


def _pick_user_class() -> dict:
    classes = [c for c in USER_CLASSES]
    weights = [c["pct"] for c in classes]
    return random.choices(classes, weights=weights, k=1)[0]


def _pick_frustration() -> tuple:
    levels = [(n, p, d) for n, p, d in FRUSTRATION_BASELINES]
    weights = [p for _, p, _ in FRUSTRATION_BASELINES]
    return random.choices(levels, weights=weights, k=1)[0]


def _get_domain_reviews(profile: CompanyProfile, count: int = 5) -> list[str]:
    try:
        from build_sector_banks import get_sector_for_business_type, load_sector_bank
        sector = get_sector_for_business_type(profile.business_type)
        if not sector:
            return []
        reviews = _load_sector_reviews(sector)
        if not reviews:
            return []
        selected = random.sample(reviews, min(count, len(reviews)))
        return [r["text"] for r in selected if r.get("text") and len(r["text"]) > 30]
    except ImportError:
        return []
    except Exception:
        return []


def generate_conversations(
    profile: CompanyProfile,
    count: int = 15,
) -> list[dict]:
    pairs = []
    for persona in profile.personas:
        for intent in profile.intents:
            pairs.append({"persona": persona, "intent": intent})

    # Load real reviews for anchoring
    anchor_reviews = _get_domain_reviews(profile, count=10)

    all_convos = []
    round_num = 0

    while len(all_convos) < count:
        random.shuffle(pairs)
        for p in pairs:
            convos = _generate_batch(profile, p["persona"], p["intent"], anchor_reviews, round_num)
            all_convos.extend(convos)
            if len(all_convos) >= count:
                break
        round_num += 1
        if round_num > 30:
            break

    all_convos = all_convos[:count]

    payload = {
        "company": profile.company_name,
        "url": profile.website_url,
        "generated_at": datetime.now().isoformat(),
        "total": len(all_convos),
        "conversations": [c.model_dump() for c in all_convos],
    }

    path = save_json(payload)
    return payload


def _generate_batch(
    profile: CompanyProfile,
    persona,
    intent,
    anchor_reviews: list[str],
    round_num: int,
) -> list[Conversation]:
    user_class = _pick_user_class()
    frust_level, frust_pct, frust_desc = _pick_frustration()

    # Pick a real review anchor
    anchor = ""
    if anchor_reviews:
        anchor = random.choice(anchor_reviews)

    domain_terms = profile.domain_terminology[:5] if profile.domain_terminology else []
    known_issues = profile.known_issues_from_docs[:4] if profile.known_issues_from_docs else []
    error_scenarios = profile.error_scenarios[:4] if profile.error_scenarios else []
    agent_failures = profile.agent_failure_patterns[:3] if profile.agent_failure_patterns else []

    prompt = f"""Generate 3 customer support conversations for {profile.company_name}.

COMPANY: {profile.company_name} ({profile.business_type})
DOMAIN TERMS: {', '.join(domain_terms)}
KNOWN ISSUES: {', '.join(known_issues)}
ERROR SCENARIOS: {', '.join(error_scenarios)}
AGENT FAILURES: {', '.join(agent_failures)}

PERSONA: {persona.name} ({persona.description})
INTENT: {intent.name}
FRUSTRATION LEVEL: {frust_level.upper()} — {frust_desc}

USER CLASS: {user_class['name']}
{user_class['desc']}

ANCHOR REAL REVIEW (use this as inspiration for the conversation's tone and content):
"{anchor}"

INSTRUCTIONS:
- EACH conversation MUST be spoken entirely in ONE user class. Do NOT mix classes.
- If user class is "Professional English" → NO Hinglish, NO slang, proper grammar.
- If user class is "Hinglish Coder" → weave Hindi naturally into English sentences mid-flow.
- If user class is "ALL CAPS Rager" → EVERY message is angry, short, aggressive.
- If user class is "Passive Aggressive" → sarcastic, cold, polite words with angry subtext.
- If user class is "Confused Newbie" → no technical jargon, repeat questions, mild frustration.
- If user class is "Legal Threatener" → formal tone, mentions regulations, demands escalation.

- Frustration level {frust_level}: adjust intensity accordingly.
- DO NOT use "can you", "could you", "I'm having trouble", "can you help" — EVER.
- Real users describe the problem, they don't ask for help.
- Include specific numbers, dates, amounts naturally.
- Vary message lengths: some short (2-5 words), some longer.
- The agent can be unhelpful, wrong, slow, or gaslight the user.
- Sometimes the issue is NOT resolved. Sometimes the user gives up.
- AVOID checklist patterns. Do NOT include every keyword.
- Real people repeat themselves, use filler words, sometimes trail off...
- Start with the problem, not with pleasantries.

Return ONLY valid JSON matching this schema:
{{
  "conversations": [
    {{
      "id": "unique-id",
      "persona": "{persona.name}",
      "intent": "{intent.name}",
      "scenario": "one-line description",
      "user_messages": ["msg1", "msg2", ...],
      "frustration_signals": ["signal1", "signal2"],
      "frustration_level": "{frust_level}",
      "expected_good_outcome": "what a fix looks like"
    }}
  ]
}}"""

    try:
        batch = call_llm(prompt, ConversationBatch)
        result = []
        for c in batch.conversations:
            c.id = f"{profile.company_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
            c.frustration_level = frust_level
            c.persona = persona.name
            c.intent = intent.name
            result.append(c)
        return result
    except Exception as e:
        print(f"  Failed: {e}")
        return []
