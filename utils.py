import json
import time
from datetime import datetime
from pathlib import Path

from groq import Groq
from pydantic import BaseModel

from config import GROQ_API_KEY, GROQ_MODEL

_last_call = 0.0
_MIN_INTERVAL = 1.0  # seconds between API calls to avoid per-minute rate limits

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def _client() -> Groq:
    return Groq(api_key=GROQ_API_KEY)


def call_llm(prompt: str, response_model: type[BaseModel]) -> BaseModel:
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)

    messages = [
        {"role": "system", "content": "You are a JSON generator. Output only valid JSON matching the requested schema."},
        {"role": "user", "content": prompt},
    ]
    response = _client().chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    _last_call = time.time()
    raw = response.choices[0].message.content
    return response_model.model_validate_json(raw)


def save_json(data, filename: str | None = None, directory: Path | None = None) -> Path:
    if filename is None:
        filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_conversations.json"
    path = (directory or OUTPUT_DIR) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {path}")
    return path


def to_slug(text: str) -> str:
    return text.lower().replace(" ", "-").replace("/", "-")[:50]
