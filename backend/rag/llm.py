"""
LLM Provider Core — AMLO

Manages two interchangeable LLM backends switchable at runtime:
  - "gemini" : Google Gemini via google-genai SDK
  - "local"  : Ollama (gemma3:4b or any pulled model) via HTTP

Higher-level functions live in:
  root_cause_analyzer.py  — analyze_root_cause()
  repair_advisor.py       — generate_repair_steps()
  work_order_drafter.py   — draft_work_order()
"""

import json
import time
import httpx
from google import genai
from google.genai import errors as genai_errors

from config import GEMINI_API_KEY, LLM_MODEL, LLM_PROVIDER, LOCAL_LLM_URL, LOCAL_LLM_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)

_provider = LLM_PROVIDER  # mutable at runtime


def get_provider() -> str:
    return _provider


def set_provider(provider: str):
    global _provider
    if provider not in ("gemini", "local"):
        raise ValueError(f"Unknown provider '{provider}' — use 'gemini' or 'local'")
    _provider = provider
    print(f"[LLM] Provider switched to: {provider}")


def _call_gemini(prompt: str, retries: int = 2) -> str:
    for attempt in range(retries):
        try:
            return client.models.generate_content(model=LLM_MODEL, contents=prompt).text.strip()
        except genai_errors.ClientError as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 35 * (attempt + 1)
                print(f"[LLM] Gemini rate limited — waiting {wait}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Gemini rate limit exceeded after retries")


def _call_local(prompt: str) -> str:
    response = httpx.post(
        f"{LOCAL_LLM_URL}/api/generate",
        json={"model": LOCAL_LLM_MODEL, "prompt": prompt, "stream": False},
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def _call(prompt: str) -> str:
    if _provider == "local":
        return _call_local(prompt)
    return _call_gemini(prompt)


def _parse_json(raw: str) -> dict:
    """Parse JSON from LLM output, stripping markdown code fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    return json.loads(text)

