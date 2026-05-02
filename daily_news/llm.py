from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .models import Candidate


DEFAULT_MODEL = os.environ.get("DAILY_NEWS_MODEL", "gpt-5.2")


def analyze_candidates(candidates: list[Candidate], report_date: str) -> dict[str, Any] | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or not candidates:
        return None

    compact = [
        {
            "title": item.title,
            "summary": item.summary[:500],
            "url": item.url,
            "category": item.category,
            "score": item.score,
            "sources": item.sources,
        }
        for item in candidates[:40]
    ]
    prompt = {
        "task": "Create a Chinese daily AI product opportunity brief.",
        "date": report_date,
        "requirements": {
            "opportunities": 5,
            "big_tech": 5,
            "pain_points": 3,
            "tone": "concise, analytical, Chinese-first",
            "return_json_only": True,
        },
        "candidates": compact,
    }
    body = {
        "model": DEFAULT_MODEL,
        "instructions": (
            "You are an AI product intelligence analyst. Return valid JSON only with keys: "
            "summary, opportunities, big_tech, pain_points. Each list item should include "
            "title, summary, reason, and source_urls."
        ),
        "input": json.dumps(prompt, ensure_ascii=False),
        "max_output_tokens": 3000,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        data = json.loads(response.read().decode("utf-8"))

    output_text = data.get("output_text") or extract_output_text(data)
    if not output_text:
        return None
    return json.loads(output_text)


def extract_output_text(data: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                parts.append(content.get("text", ""))
    return "\n".join(part for part in parts if part).strip()
