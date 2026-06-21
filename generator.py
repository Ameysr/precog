import json
import random
import re
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


EMOTIONAL_MODES = [
    ("rage", 0.25),
    ("panic", 0.20),
    ("sarcastic", 0.15),
    ("confused", 0.15),
    ("resigned", 0.10),
    ("abusive", 0.10),
    ("threatening_legal", 0.05),
]

MESSAGE_COUNTS = {
    "short": (1, 2, 0.15),
    "medium": (3, 5, 0.40),
    "long": (6, 10, 0.30),
    "epic": (11, 20, 0.15),
}


def _load_language_bank(company_name: str) -> dict | None:
    pattern = f"{company_name.lower().replace(' ', '-')}_language_bank.json"
    for d in [DATA_DIR, OUTPUT_DIR]:
        path = d / pattern
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    print(f"  [!] No language bank found for {company_name}")
    return None


def _pick_emotional_mode() -> tuple[str, str]:
    mode = random.choices(
        [m for m, _ in EMOTIONAL_MODES],
        weights=[p for _, p in EMOTIONAL_MODES],
        k=1,
    )[0]
    label_map = {
        "rage": "USER IS FURIOUS. Use ALL CAPS, expletives, threats. No politeness.",
        "panic": "USER IS PANICKING. Financial loss or urgent problem. Repeated messages, desperation.",
        "sarcastic": "USER IS SARCASTIC. Passive-aggressive, mocking, 'great service' style.",
        "confused": "USER IS CONFUSED. They don't understand what happened. Asking repetitive questions.",
        "resigned": "USER IS RESIGNED. They've tried everything. Tired, giving up, or defeated tone.",
        "abusive": "USER IS ABUSIVE. Personal insults, vulgar language, yelling.",
        "threatening_legal": "USER IS THREATENING LEGAL ACTION. Mentioning lawyers, consumer court, police complaint.",
    }
    return mode, label_map[mode]


def _pick_message_count() -> int:
    size, (min_c, max_c, _) = random.choices(
        list(MESSAGE_COUNTS.items()),
        weights=[p for _, (_, _, p) in MESSAGE_COUNTS.items()],
        k=1,
    )[0]
    return random.randint(min_c, max_c)


def _apply_messiness(text: str, intensity: float = 0.3) -> str:
    if random.random() > intensity:
        return text

    ops = []

    # Random ALL CAPS for emphasis
    if random.random() < 0.4:
        words = text.split()
        if len(words) > 3:
            idx = random.randint(0, len(words) - 1)
            words[idx] = words[idx].upper()
            text = " ".join(words)

    # Random full-line ALL CAPS (rage mode)
    if random.random() < 0.15:
        if random.random() < 0.5:
            text = text.upper()

    # Random exclamation spam
    if random.random() < 0.3:
        text = re.sub(r"[.!?]", "!", text)
        text = text.rstrip("!") + "!" * random.randint(1, 5)

    # Random typos (swap adjacent chars)
    if random.random() < 0.25:
        chars = list(text)
        for _ in range(random.randint(1, 3)):
            idx = random.randint(0, len(chars) - 2)
            if chars[idx].isalpha() and chars[idx + 1].isalpha():
                chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
        text = "".join(chars)

    # Remove random punctuation
    if random.random() < 0.15:
        text = re.sub(r"[.?!,;:]", "", text)

    # Add random ellipsis
    if random.random() < 0.2:
        text += "..." if random.random() < 0.5 else ".."

    return text


def _inject_hinglish(text: str, hinglish_phrases: list[str]) -> str:
    if not hinglish_phrases or random.random() > 0.3:
        return text
    phrase = random.choice(hinglish_phrases)
    insert_positions = [
        lambda t: f"{phrase} {t}",
        lambda t: f"{t} {phrase}",
        lambda t: t.replace(".", f", {phrase}.", 1) if "." in t else f"{t} {phrase}",
    ]
    return random.choice(insert_positions)(text)


def generate_conversations(
    profile: CompanyProfile,
    count: int = 60,
) -> list[dict]:
    bank = _load_language_bank(profile.company_name)

    pairs = []
    for persona in profile.personas:
        for intent in profile.intents:
            pairs.append({"persona": persona, "intent": intent})

    all_convos = []
    round_num = 0

    while len(all_convos) < count:
        random.shuffle(pairs)
        for p in pairs:
            convos = _generate_batch(
                profile, bank, p["persona"], p["intent"], round_num,
            )
            all_convos.extend(convos)
            if len(all_convos) >= count:
                break
        round_num += 1
        if round_num > 50:
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
    bank: dict | None,
    persona,
    intent,
    round_num: int,
) -> list[Conversation]:
    emotion_mode, emotion_instruction = _pick_emotional_mode()
    num_messages = _pick_message_count()

    bank_context = ""
    if bank:
        anger = bank.get("anger_words", [])
        panic = bank.get("panic_words", [])
        hinglish = bank.get("hinglish_examples", [])
        starters = bank.get("sentence_starters", {})
        complaints = bank.get("real_complaints_cleaned", [])
        issues = bank.get("domain_issues", [])
        financial = bank.get("financial_terms", [])
        sarcasm = bank.get("sarcasm_patterns", [])

        if starters:
            angry_starts = starters.get("angry", [])
            panicked_starts = starters.get("panicked", [])
            sarcastic_starts = starters.get("sarcastic", [])
        else:
            angry_starts = panicked_starts = sarcastic_starts = []

        bank_context = f"""
Real vocabulary to use (must include some of these):
Anger words: {random.sample(anger, min(3, len(anger))) if anger else 'use natural anger'}
Panic words: {random.sample(panic, min(2, len(panic))) if panic else 'use natural panic'}
Financial terms: {random.sample(financial, min(3, len(financial))) if financial else 'use natural terms'}

Real sentence starters to use:
Angry: {random.sample(angry_starts, min(2, len(angry_starts))) if angry_starts else 'natural angry starters'}
Panicked: {random.sample(panicked_starts, min(2, len(panicked_starts))) if panicked_starts else 'natural panicked starters'}
Sarcastic: {random.sample(sarcastic_starts, min(2, len(sarcastic_starts))) if sarcastic_starts else 'natural sarcastic starters'}

Real complaint example to style-match:
{random.choice(complaints) if complaints else 'user complaint'}

Domain issues to reference: {random.sample(issues, min(3, len(issues))) if issues else profile.high_frustration_areas[:3]}

Hinglish phrases to mix in (use naturally): {random.sample(hinglish, min(2, len(hinglish))) if hinglish else 'none'}

Sarcasm patterns: {random.sample(sarcasm, min(2, len(sarcasm))) if sarcasm else 'none'}
"""

    domain_terms = profile.domain_terminology[:5] if profile.domain_terminology else []
    known_issues = profile.known_issues_from_docs[:5] if profile.known_issues_from_docs else []
    error_scenarios = profile.error_scenarios[:5] if profile.error_scenarios else []
    agent_failures = profile.agent_failure_patterns[:5] if profile.agent_failure_patterns else []

    prompt = f"""Generate {1} HIGHLY REALISTIC customer support conversation for {profile.company_name}.

{emotion_instruction}

Company: {profile.company_name} ({profile.business_type})
Voice guidelines (how agent SHOULD NOT sound): {profile.voice_guidelines}

Persona: {persona.name} ({persona.description})
Traits: {', '.join(persona.traits)}
Frustration triggers: {', '.join(persona.frustration_triggers)}

Intent: {intent.name}
User steps: {', '.join(intent.user_steps)}
Failure modes: {', '.join(intent.failure_modes)}

Domain terms to use naturally: {', '.join(domain_terms)}
Real issues from this company: {', '.join(known_issues)}
Error scenarios: {', '.join(error_scenarios)}
Ways agent can fail: {', '.join(agent_failures)}

Number of user messages: EXACTLY {num_messages} messages (this is critical)

{bank_context}

CRITICAL RULES:
- Do NOT use polite language. Real frustrated users are NOT polite.
- Do NOT say "I'm having trouble" or "Can you help" — real users don't talk like this.
- Start conversations with raw emotion, not explanations.
- Include specific numbers (amounts, dates, order IDs) naturally.
- Vary message length — some are 2 words, some are 3 sentences.
- Add typos, missing punctuation, or awkward phrasing naturally.
- NEVER mention "your competitor" in a structured way. Just say the competitor name directly if at all.
- The agent can be unhelpful, slow, or wrong. Sometimes the agent gaslights the user.
- Sometimes the issue is NOT resolved.
- Include financial specifics where relevant (actual amounts with ₹, fund names, order types).
- For Hinglish: mix Hindi words naturally into English sentences.

Return ONLY valid JSON matching this schema:
{{
  "conversations": [
    {{
      "id": "unique-id",
      "persona": "persona name",
      "intent": "intent name",
      "scenario": "one line description",
      "user_messages": ["msg1", "msg2", ...],
      "frustration_signals": ["signal1", "signal2"],
      "frustration_level": "low|medium|high",
      "expected_good_outcome": "short description of fix"
    }}
  ]
}}"""

    try:
        batch = call_llm(prompt, ConversationBatch)
        result = []
        for c in batch.conversations:
            c.id = f"{profile.company_name.lower().replace(' ', '-')}-{abs(hash(c.scenario)) % 10000:04d}"

            # Apply messiness post-processing
            messy_messages = []
            for i, msg in enumerate(c.user_messages):
                m = msg
                if bank:
                    m = _inject_hinglish(m, bank.get("hinglish_examples", []))
                m = _apply_messiness(m, intensity=0.35)
                messy_messages.append(m)
            c.user_messages = messy_messages

            result.append(c)
        return result
    except Exception as e:
        print(f"  Failed: {e}")
        return []
