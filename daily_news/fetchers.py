from __future__ import annotations

import datetime as dt
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from .models import Candidate, SourceResult


USER_AGENT = "daily-news-local/0.1 (+https://github.com/)"


def fetch_text(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def fetch_json(url: str, timeout: int = 20) -> object:
    return json.loads(fetch_text(url, timeout=timeout))


def parse_feed_datetime(value: str) -> str:
    if not value:
        return dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        return parsedate_to_datetime(value).astimezone(dt.timezone.utc).isoformat()
    except (TypeError, ValueError):
        try:
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc).isoformat()
        except ValueError:
            return dt.datetime.now(dt.timezone.utc).isoformat()


def strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value or ""))).strip()


class RssSource:
    def __init__(self, name: str, url: str, category: str = "general") -> None:
        self.name = name
        self.url = url
        self.category = category

    def fetch(self, window_start: dt.datetime, window_end: dt.datetime) -> SourceResult:
        text = fetch_text(self.url)
        root = ET.fromstring(text)
        candidates: list[Candidate] = []

        for item in root.findall(".//item"):
            title = strip_html(item.findtext("title", ""))
            link = item.findtext("link", "").strip()
            published = parse_feed_datetime(item.findtext("pubDate", ""))
            summary = strip_html(item.findtext("description", ""))
            if title and link and in_window(published, window_start, window_end):
                candidates.append(Candidate(title, link, self.name, published, summary, self.category))

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//atom:entry", ns):
            title = strip_html(entry.findtext("atom:title", "", ns))
            link = ""
            link_node = entry.find("atom:link", ns)
            if link_node is not None:
                link = link_node.attrib.get("href", "")
            published = parse_feed_datetime(
                entry.findtext("atom:published", "", ns) or entry.findtext("atom:updated", "", ns)
            )
            summary = strip_html(entry.findtext("atom:summary", "", ns) or entry.findtext("atom:content", "", ns))
            if title and link and in_window(published, window_start, window_end):
                candidates.append(Candidate(title, link, self.name, published, summary, self.category))

        return SourceResult(self.name, ok=True, candidates=candidates)


class HackerNewsSource:
    name = "Hacker News"

    def fetch(self, window_start: dt.datetime, window_end: dt.datetime) -> SourceResult:
        start = int(window_start.timestamp())
        end = int(window_end.timestamp())
        queries = ["AI", "LLM", "agent", "OpenAI", "Claude", "Gemini", "Show HN AI"]
        candidates: list[Candidate] = []

        for query in queries:
            params = urllib.parse.urlencode(
                {
                    "query": query,
                    "tags": "story",
                    "numericFilters": f"created_at_i>{start},created_at_i<{end},points>5",
                    "hitsPerPage": 20,
                }
            )
            data = fetch_json(f"https://hn.algolia.com/api/v1/search_by_date?{params}")
            for hit in data.get("hits", []) if isinstance(data, dict) else []:
                title = hit.get("title") or hit.get("story_title") or ""
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                summary = f"{hit.get('points', 0)} points, {hit.get('num_comments', 0)} comments"
                candidates.append(
                    Candidate(
                        title=strip_html(title),
                        url=url,
                        source=self.name,
                        published_at=parse_feed_datetime(hit.get("created_at", "")),
                        summary=summary,
                        category="product",
                    )
                )

        return SourceResult(self.name, ok=True, candidates=candidates)


class GitHubAISource:
    name = "GitHub AI Repositories"

    def fetch(self, window_start: dt.datetime, window_end: dt.datetime) -> SourceResult:
        pushed_after = window_start.date().isoformat()
        query = urllib.parse.quote(f"topic:ai pushed:>{pushed_after}")
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=20"
        data = fetch_json(url)
        candidates = []
        for repo in data.get("items", []) if isinstance(data, dict) else []:
            description = repo.get("description") or ""
            candidates.append(
                Candidate(
                    title=repo.get("full_name", ""),
                    url=repo.get("html_url", ""),
                    source=self.name,
                    published_at=repo.get("pushed_at") or window_end.isoformat(),
                    summary=f"{description} Stars: {repo.get('stargazers_count', 0)}",
                    category="product",
                )
            )
        return SourceResult(self.name, ok=True, candidates=candidates)


class HuggingFaceSource:
    name = "Hugging Face"

    def fetch(self, window_start: dt.datetime, window_end: dt.datetime) -> SourceResult:
        data = fetch_json("https://huggingface.co/api/models?sort=likes&direction=-1&limit=20")
        candidates = []
        for model in data if isinstance(data, list) else []:
            model_id = model.get("modelId", "")
            if not model_id:
                continue
            candidates.append(
                Candidate(
                    title=model_id,
                    url=f"https://huggingface.co/{model_id}",
                    source=self.name,
                    published_at=window_end.isoformat(),
                    summary=f"Likes: {model.get('likes', 0)} Downloads: {model.get('downloads', 0)}",
                    category="product",
                )
            )
        return SourceResult(self.name, ok=True, candidates=candidates)


class TechmemeSource:
    name = "Techmeme River"

    def fetch(self, window_start: dt.datetime, window_end: dt.datetime) -> SourceResult:
        text = fetch_text("https://www.techmeme.com/river")
        candidates = []
        for match in re.finditer(r"<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", text, flags=re.I | re.S):
            title = strip_html(match.group(2))
            if not title or not looks_ai_related(title):
                continue
            url = urllib.parse.urljoin("https://www.techmeme.com/river", html.unescape(match.group(1)))
            candidates.append(
                Candidate(
                    title=title,
                    url=url,
                    source=self.name,
                    published_at=window_end.isoformat(),
                    summary="Techmeme industry signal.",
                    category="big_tech",
                )
            )
            if len(candidates) >= 20:
                break
        return SourceResult(self.name, ok=True, candidates=candidates)


def looks_ai_related(text: str) -> bool:
    lowered = text.lower()
    terms = ["ai", "openai", "anthropic", "claude", "gemini", "llm", "agent", "nvidia", "copilot"]
    return any(term in lowered for term in terms)


def in_window(value: str, window_start: dt.datetime, window_end: dt.datetime) -> bool:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except ValueError:
        return True
    return window_start <= parsed <= window_end


def default_sources() -> list[object]:
    return [
        RssSource("OpenAI News", "https://openai.com/news/rss.xml", "big_tech"),
        RssSource("Anthropic Newsroom", "https://www.anthropic.com/news/rss.xml", "big_tech"),
        RssSource("Google DeepMind Blog", "https://deepmind.google/blog/rss.xml", "big_tech"),
        RssSource("NVIDIA Blog", "https://blogs.nvidia.com/feed/", "big_tech"),
        RssSource("Product Hunt", "https://www.producthunt.com/feed", "product"),
        RssSource("Planet AI", "https://planet-ai.net/rss.xml", "general"),
        HackerNewsSource(),
        GitHubAISource(),
        HuggingFaceSource(),
        TechmemeSource(),
    ]
