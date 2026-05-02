from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Candidate:
    title: str
    url: str
    source: str
    published_at: str
    summary: str = ""
    category: str = "general"
    score: int = 0
    rank: int = 0
    reason: str = ""
    sources: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.sources:
            self.sources = [self.source]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at,
            "summary": self.summary,
            "category": self.category,
            "score": self.score,
            "rank": self.rank,
            "reason": self.reason,
            "sources": self.sources,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Candidate":
        return cls(
            title=str(data.get("title", "")),
            url=str(data.get("url", "")),
            source=str(data.get("source", "")),
            published_at=str(data.get("published_at", "")),
            summary=str(data.get("summary", "")),
            category=str(data.get("category", "general")),
            score=int(data.get("score", 0) or 0),
            rank=int(data.get("rank", 0) or 0),
            reason=str(data.get("reason", "")),
            sources=list(data.get("sources", []) or []),
        )


@dataclass
class SourceResult:
    name: str
    ok: bool
    candidates: list[Candidate] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "count": len(self.candidates),
            "error": self.error,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


@dataclass
class CollectionResult:
    candidates: list[Candidate]
    source_results: list[SourceResult]


@dataclass
class PublishResult:
    status: str
    message: str
    commit_hash: str = ""
