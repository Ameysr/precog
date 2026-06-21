import json

from pydantic import BaseModel

from utils import call_llm


class Persona(BaseModel):
    name: str
    description: str
    traits: list[str]
    common_goals: list[str]
    frustration_triggers: list[str]


class Intent(BaseModel):
    name: str
    description: str
    user_steps: list[str]
    failure_modes: list[str]
    severity: str


class CompanyProfile(BaseModel):
    company_name: str
    business_type: str
    description: str
    website_url: str
    personas: list[Persona]
    intents: list[Intent]
    voice_guidelines: str
    high_frustration_areas: list[str]


def _schema_example() -> dict:
    return {
        "company_name": "ExampleCorp",
        "business_type": "SaaS / fintech / food delivery",
        "description": "short description",
        "website_url": "https://example.com",
        "personas": [
            {
                "name": "Persona name",
                "description": "short description",
                "traits": ["trait1", "trait2"],
                "common_goals": ["goal1", "goal2"],
                "frustration_triggers": ["trigger1", "trigger2"],
            }
        ],
        "intents": [
            {
                "name": "Intent name",
                "description": "what the user wants",
                "user_steps": ["step1", "step2"],
                "failure_modes": ["what goes wrong"],
                "severity": "low/medium/high",
            }
        ],
        "voice_guidelines": "how the company speaks",
        "high_frustration_areas": ["area1", "area2"],
    }


def build_profile(scraped_pages: dict[str, str], company_url: str) -> CompanyProfile:
    combined = "\n\n".join(
        f"--- {title} ---\n{text[:2000]}"
        for title, text in scraped_pages.items()
    )

    schema = json.dumps(_schema_example(), indent=2)

    prompt = f"""You are analyzing a company based on their website content.

Company URL: {company_url}

Website content:
{combined[:15000]}

Extract a structured profile needed to generate synthetic customer support conversations.
Identify realistic user personas, common intents, frustration points, and brand voice.

You MUST return JSON that matches this EXACT schema (field names must be identical):
{schema}

Return ONLY the JSON object, no other text."""

    return call_llm(prompt, CompanyProfile)
