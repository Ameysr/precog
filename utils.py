import json
import os
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel

from config import OPENAI_API_KEY

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

client = OpenAI(api_key=OPENAI_API_KEY)


def call_llm(prompt: str, response_model: type[BaseModel]) -> BaseModel:
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format=response_model,
    )
    return response.choices[0].message.parsed


def save_json(data, filename: str | None = None) -> Path:
    if filename is None:
        filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_conversations.json"
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {path}")
    return path


def load_json(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def to_slug(text: str) -> str:
    return text.lower().replace(" ", "-").replace("/", "-")[:50]
