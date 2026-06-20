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


def build_profile(scraped_pages: dict[str, str], company_url: str) -> CompanyProfile:
    combined = "\n\n".join(
        f"--- {title} ---\n{text[:2000]}"
        for title, text in scraped_pages.items()
    )

    prompt = f"""You are analyzing a company based on their website content.

Company URL: {company_url}

Website content:
{combined[:15000]}

Extract a structured profile needed to generate synthetic customer support conversations.
Identify realistic user personas, common intents, frustration points, and brand voice.
Return ONLY valid JSON matching the schema."""

    return call_llm(prompt, CompanyProfile)
