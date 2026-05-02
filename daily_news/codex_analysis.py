from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from .models import Candidate, SourceResult
from .render import build_report_payload, write_report_files
from .site import write_static_site


REQUIRED_SECTIONS = ("opportunities", "big_tech", "pain_points")


def analysis_path(root: Path, report_date: dt.date) -> Path:
    return root / ".cache/daily-news" / f"{report_date.isoformat()}-analysis.json"


def brief_path(root: Path, report_date: dt.date) -> Path:
    return root / ".cache/daily-news" / f"{report_date.isoformat()}-codex-brief.md"


def write_codex_brief(
    root: Path,
    report_date: dt.date,
    candidates: list[Candidate],
    source_results: list[SourceResult],
) -> Path:
    path = brief_path(root, report_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_codex_brief(report_date, candidates, source_results), encoding="utf-8")
    return path


def render_codex_brief(
    report_date: dt.date,
    candidates: list[Candidate],
    source_results: list[SourceResult],
    limit: int = 40,
) -> str:
    output_path = f".cache/daily-news/{report_date.isoformat()}-analysis.json"
    lines = [
        f"# Codex 原生分析任务 · {report_date.isoformat()}",
        "",
        "你是 AI 产品情报分析师。请阅读下面候选信号，写出中文为主的高质量日报分析。",
        "",
        f"把最终 JSON 写入 `{output_path}`。只输出 JSON，不要夹杂 Markdown。",
        "",
        "## 输出 JSON schema",
        "",
        "```json",
        json.dumps(
            {
                "summary": "2-4 句中文总览，说明今天最重要的产品机会和巨头动态。",
                "opportunities": [
                    {
                        "title": "中文机会标题",
                        "summary": "用中文说明这个机会是什么。",
                        "reason": "为什么值得跟进，最好连接用户痛点/平台变化/商业化可能。",
                        "source_urls": ["https://example.com/source"],
                    }
                ],
                "big_tech": [
                    {
                        "title": "中文动态标题",
                        "summary": "巨头动作的事实摘要。",
                        "reason": "它可能怎样改变能力边界、分发或成本结构。",
                        "source_urls": ["https://example.com/source"],
                    }
                ],
                "pain_points": [
                    {
                        "title": "中文痛点标题",
                        "summary": "用户/团队具体卡在哪里。",
                        "reason": "为什么这是产品需求而不只是新闻。",
                        "source_urls": ["https://example.com/source"],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        "```",
        "",
        "## 选择规则",
        "",
        "- 选择 5 个产品机会、5 条巨头动态、3 个用户痛点。",
        "- 只使用候选数据里的来源 URL，不要编造来源。",
        "- 每条候选的 published_at 就是引用日期；不要选择明显不在本期窗口内的旧资料。",
        "- 中文改写，不要机械翻译标题；保留必要英文产品名。",
        "- 优先选择和 AI 产品、AI 趋势、AI 发展、用户痛点、用户需求相关的信号。",
        "- 对低质量或无关候选直接忽略。",
        "",
        "## 来源覆盖",
        "",
    ]
    for result in source_results:
        status = "OK" if result.ok else "FAIL"
        suffix = f" · {result.error}" if result.error else ""
        lines.append(f"- {status} · {result.name} · {len(result.candidates)} 条{suffix}")

    lines.extend(["", "## 候选信号", ""])
    for candidate in candidates[:limit]:
        lines.extend(
            [
                f"### {candidate.rank or '-'} · {candidate.title}",
                "",
                f"- category: {candidate.category}",
                f"- score: {candidate.score}",
                f"- source: {', '.join(candidate.sources)}",
                f"- url: {candidate.url}",
                f"- published_at: {candidate.published_at}",
                f"- summary: {candidate.summary or 'N/A'}",
                f"- existing_reason: {candidate.reason or 'N/A'}",
                "",
            ]
        )
    return "\n".join(lines)


def load_codex_analysis(root: Path, report_date: dt.date) -> dict[str, Any]:
    path = analysis_path(root, report_date)
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_analysis(data)
    return data


def validate_analysis(data: dict[str, Any]) -> None:
    if not isinstance(data.get("summary"), str) or not data["summary"].strip():
        raise ValueError("Codex analysis must include a non-empty summary.")
    for section in REQUIRED_SECTIONS:
        items = data.get(section)
        if not isinstance(items, list) or not items:
            raise ValueError(f"Codex analysis must include non-empty {section}.")
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"{section}[{index}] must be an object.")
            for field in ("title", "summary", "reason"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    raise ValueError(f"{section}[{index}] must include non-empty {field}.")
            if not isinstance(item.get("source_urls"), list) or not item["source_urls"]:
                raise ValueError(f"{section}[{index}] must include source_urls.")


def validate_analysis_sources(data: dict[str, Any], candidates: list[Candidate]) -> None:
    known_urls = {candidate.url for candidate in candidates}
    for section in REQUIRED_SECTIONS:
        for item in data.get(section, []):
            unknown_urls = [url for url in item.get("source_urls", []) if url not in known_urls]
            if unknown_urls:
                title = item.get("title", section)
                raise ValueError(f"Analysis item {title!r} cites URLs outside the candidate set: {unknown_urls}")


def apply_codex_analysis(
    root: Path,
    report_date: dt.date,
    candidates: list[Candidate],
    source_results: list[SourceResult],
) -> dict[str, Path]:
    analysis = load_codex_analysis(root, report_date)
    validate_analysis_sources(analysis, candidates)
    payload = build_report_payload(report_date, candidates, source_results, analysis)
    paths = write_report_files(root, payload)
    paths["site"] = write_static_site(root)
    return paths
