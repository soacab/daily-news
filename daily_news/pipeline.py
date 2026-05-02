from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Candidate, CollectionResult, SourceResult


TRACKED_HOSTS = {
    "openai.com",
    "anthropic.com",
    "deepmind.google",
    "blog.google",
    "nvidia.com",
    "microsoft.com",
    "meta.com",
    "ai.meta.com",
    "google.com",
}

OPPORTUNITY_TERMS = {
    "agent",
    "agents",
    "workflow",
    "automation",
    "developer",
    "coding",
    "design",
    "security",
    "cost",
    "pricing",
    "enterprise",
    "product hunt",
    "show hn",
    "launch",
    "users",
    "pain",
    "need",
    "audit",
    "monitor",
}

BIG_TECH_TERMS = {
    "openai",
    "anthropic",
    "claude",
    "google",
    "deepmind",
    "gemini",
    "microsoft",
    "copilot",
    "meta",
    "llama",
    "nvidia",
}

PAIN_TERMS = {
    "complain",
    "struggle",
    "pain",
    "problem",
    "hard",
    "cost",
    "security",
    "privacy",
    "latency",
    "workflow",
    "governance",
    "audit",
    "budget",
    "confusing",
}


def collect_candidates(sources: list[object], window_start: datetime, window_end: datetime) -> CollectionResult:
    candidates: list[Candidate] = []
    source_results: list[SourceResult] = []

    for source in sources:
        name = getattr(source, "name", source.__class__.__name__)
        try:
            result = source.fetch(window_start, window_end)
            if not isinstance(result, SourceResult):
                result = SourceResult(name=name, ok=True, candidates=list(result or []))
        except Exception as exc:  # noqa: BLE001 - source isolation is intentional.
            result = SourceResult(name=name, ok=False, error=str(exc))
        candidates.extend(result.candidates)
        source_results.append(result)

    return CollectionResult(candidates=candidates, source_results=source_results)


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"ref", "via"}
    ]
    clean_query = urlencode(query, doseq=True)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), clean_query, ""))


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def merge_candidates(candidates: list[Candidate]) -> list[Candidate]:
    merged: dict[str, Candidate] = {}

    for item in candidates:
        key = canonical_url(item.url) if item.url else normalize_title(item.title)
        existing = merged.get(key)
        if existing is None:
            item.url = canonical_url(item.url)
            item.sources = sorted(set(item.sources or [item.source]))
            merged[key] = item
            continue

        existing.sources = sorted(set(existing.sources + item.sources + [item.source]))
        if item.summary and item.summary not in existing.summary:
            existing.summary = (existing.summary + " " + item.summary).strip()
        if not existing.reason and item.reason:
            existing.reason = item.reason
        existing.score = max(existing.score, item.score)
        if existing.category == "general" and item.category != "general":
            existing.category = item.category

    return list(merged.values())


def score_candidates(candidates: list[Candidate]) -> list[Candidate]:
    for item in candidates:
        text = f"{item.title} {item.summary} {item.source} {' '.join(item.sources)}".lower()
        score = item.score or 10

        if item.category == "product":
            score += 20
        if item.category == "big_tech":
            score += 18
        if any(term in text for term in OPPORTUNITY_TERMS):
            score += 24
        if any(term in text for term in BIG_TECH_TERMS):
            score += 18
        if any(term in text for term in PAIN_TERMS):
            score += 16
        if len(item.sources) > 1:
            score += min(12, 4 * len(item.sources))
        if any(host in item.url for host in TRACKED_HOSTS):
            score += 10

        item.score = min(score, 100)

    ranked = sorted(candidates, key=lambda candidate: (-candidate.score, candidate.title.lower()))
    for index, item in enumerate(ranked, start=1):
        item.rank = index
        if not item.reason:
            item.reason = infer_reason(item)
    return ranked


def infer_reason(item: Candidate) -> str:
    text = f"{item.title} {item.summary}".lower()
    if any(term in text for term in PAIN_TERMS):
        return "出现明确用户痛点或采用阻力，值得转化为产品机会。"
    if any(term in text for term in BIG_TECH_TERMS):
        return "来自主要 AI 公司或平台动作，可能改变产品分发、能力边界或成本结构。"
    if any(term in text for term in OPPORTUNITY_TERMS):
        return "包含新产品、新工作流或开发者需求信号，适合跟进验证。"
    return "信息源可信且与 AI 产品生态相关，保留为趋势观察信号。"
