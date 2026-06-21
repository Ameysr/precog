import random
from datetime import datetime

from pydantic import BaseModel

from config import GROQ_MODEL
from profiler import CompanyProfile, Persona, Intent
from utils import call_llm, save_json


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


def generate_conversations(profile: CompanyProfile, count: int = 60) -> list[dict]:
    pairs = _build_persona_intent_pairs(profile.personas, profile.intents)
    random.shuffle(pairs)

    happy_count = int(count * 0.4)
    frust_count = int(count * 0.4)
    edge_count = count - happy_count - frust_count

    all_convos = []

    for pair_list, mood_label, mood in [
        (pairs[:happy_count], "happy", "smooth"),
        (pairs[happy_count:happy_count + frust_count], "frustrated", "frustrated"),
        (pairs[happy_count + frust_count:], "edge_cases", "edge"),
    ]:
        for p in pair_list[:3]:
            convos = _generate_batch(profile, p["persona"], p["intent"], mood, mood_label)
            all_convos.extend(convos)
            if len(all_convos) >= count:
                break
        if len(all_convos) >= count:
            break

    all_convos = all_convos[:count]
    timestamp = datetime.now().isoformat()

    payload = {
        "company": profile.company_name,
        "url": profile.website_url,
        "generated_at": timestamp,
        "total": len(all_convos),
        "conversations": [c.model_dump() for c in all_convos],
    }

    path = save_json(payload)
    return payload


def _build_persona_intent_pairs(
    personas: list[Persona], intents: list[Intent]
) -> list[dict]:
    pairs = []
    for persona in personas:
        for intent in intents:
            pairs.append({"persona": persona, "intent": intent})
    return pairs


def _generate_batch(
    profile: CompanyProfile,
    persona: Persona,
    intent: Intent,
    mood: str,
    mood_label: str,
) -> list[Conversation]:
    prompt = f"""Generate 3 realistic customer support conversations for {profile.company_name}.

Company: {profile.company_name} ({profile.business_type})
Voice guidelines: {profile.voice_guidelines}

Persona: {persona.name}
  Description: {persona.description}
  Traits: {', '.join(persona.traits)}
  Frustration triggers: {', '.join(persona.frustration_triggers)}

Intent: {intent.name}
  Description: {intent.description}
  What user tries to do: {', '.join(intent.user_steps)}
  Failure modes: {', '.join(intent.failure_modes)}

Mood: {mood_label}

Generate 3 conversations. Each must:
- Include 3-6 user messages in a natural back-and-forth
- Embed frustration signals naturally (repetition, urgency, comparison to competitor, threat to churn, sarcasm, confusion)
- Reflect the persona's traits and triggers
- Be based on the intent's failure modes
- Include what a good support response should do

Return ONLY valid JSON matching this schema:
{{
  "conversations": [
    {{
      "id": "unique-id",
      "persona": "persona name",
      "intent": "intent name",
      "scenario": "description of the scenario",
      "user_messages": ["msg1", "msg2", "msg3"],
      "frustration_signals": ["signal1", "signal2"],
      "frustration_level": "low|medium|high",
      "expected_good_outcome": "what good agent should do"
    }}
  ]
}}"""

    try:
        batch = call_llm(prompt, ConversationBatch)
        for c in batch.conversations:
            c.id = f"{profile.company_name.lower().replace(' ', '-')}-{hash(c.scenario) % 10000:04d}"
        return batch.conversations
    except Exception as e:
        print(f"  Failed for {persona.name}/{intent.name}: {e}")
        return []
