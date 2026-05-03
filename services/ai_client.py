"""
Shared AI client — uses Groq API (free tier).
All services call ask_ai() instead of Ollama directly.
"""
import os
import re
import json
from groq import Groq
from json_repair import repair_json

MODEL = "llama-3.3-70b-versatile"  # better than llama3.2, free on Groq

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set")
        _client = Groq(api_key=api_key)
    return _client


def ask_ai(system_prompt: str, user_content: str, timeout: int = 60) -> str:
    """
    Send a prompt to Groq and return the raw text response.
    Strips markdown code fences and extracts the first JSON block.
    """
    client = _get_client()
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
        timeout=timeout,
    )
    raw = completion.choices[0].message.content.strip()

    # Strip markdown code fences
    if "```" in raw:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if m:
            raw = m.group(1).strip()

    # Extract first JSON object or array
    m = re.search(r"[\[\{][\s\S]*[\]\}]", raw)
    if m:
        raw = m.group(0)

    return repair_json(raw)
