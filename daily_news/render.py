from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from .models import Candidate, SourceResult


def candidate_to_frontend(item: Candidate) -> dict[str, Any]:
    return {
        "title": item.title,
        "summary": item.summary,
        "reason": item.reason,
        "score": item.score,
        "rank": item.rank,
        "published_at": item.published_at,
        "sources": [{"name": source, "url": item.url} for source in item.sources],
        "url": item.url,
    }


def build_report_payload(
    report_date: dt.date,
    candidates: list[Candidate],
    source_results: list[SourceResult],
    analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    opportunities = [item for item in candidates if item.category in {"product", "general"}][:5]
    big_tech = [item for item in candidates if item.category == "big_tech"][:5]
    pain_points = [
        item
        for item in candidates
        if any(term in f"{item.title} {item.summary} {item.reason}".lower() for term in ["pain", "cost", "security", "workflow", "audit", "governance", "budget", "hard"])
    ][:3]
    if len(pain_points) < 3:
        pain_points.extend([item for item in opportunities if item not in pain_points][: 3 - len(pain_points)])

    summary = "今天的 AI 产品机会主要来自产品发布、社区痛点和巨头平台动作的交叉信号。"
    if analysis and isinstance(analysis.get("summary"), str):
        summary = analysis["summary"]

    return {
        "date": report_date.isoformat(),
        "title": "AI 产品机会日报",
        "summary": summary,
        "opportunities": [candidate_to_frontend(item) for item in opportunities],
        "big_tech": [candidate_to_frontend(item) for item in big_tech],
        "pain_points": [candidate_to_frontend(item) for item in pain_points[:3]],
        "source_health": [
            {"name": result.name, "ok": result.ok, "count": len(result.candidates), "error": result.error}
            for result in source_results
        ],
        "low_signal": len(candidates) < 8,
        "all_candidates": [item.to_dict() for item in candidates],
        "analysis": analysis,
    }


def write_report_files(root: Path, payload: dict[str, Any]) -> dict[str, Path]:
    report_date = payload["date"]
    reports_dir = root / "reports"
    data_reports_dir = root / "site/data/reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    data_reports_dir.mkdir(parents=True, exist_ok=True)
    (root / "site/data").mkdir(parents=True, exist_ok=True)

    markdown_path = reports_dir / f"{report_date}.md"
    report_json_path = data_reports_dir / f"{report_date}.json"
    latest_path = root / "site/data/latest.json"
    archive_path = root / "site/data/archive.json"

    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    report_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_archive(archive_path, payload)

    return {"markdown": markdown_path, "json": report_json_path, "latest": latest_path, "archive": archive_path}


def write_archive(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        archive = json.loads(path.read_text(encoding="utf-8"))
    else:
        archive = {"reports": []}

    reports = [report for report in archive.get("reports", []) if report.get("date") != payload["date"]]
    reports.insert(
        0,
        {
            "date": payload["date"],
            "title": payload["title"],
            "summary": payload["summary"],
            "path": f"reports/{payload['date']}.md",
            "json": f"data/reports/{payload['date']}.json",
            "low_signal": payload.get("low_signal", False),
        },
    )
    archive["reports"] = sorted(reports, key=lambda report: report["date"], reverse=True)
    path.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8")


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# AI 产品机会日报 · {payload['date']}",
        "",
        payload["summary"],
        "",
    ]
    if payload.get("low_signal"):
        lines.extend(
            [
                "> 低信号日：过去 24 小时可用高质量信号不足，以下内容保留来源覆盖和候选判断，供轻量复盘。",
                "",
            ]
        )
    lines.extend(render_section("今日产品机会", payload["opportunities"]))
    lines.extend(render_section("AI 巨头动态", payload["big_tech"]))
    lines.extend(render_section("用户痛点与需求信号", payload["pain_points"]))
    lines.extend(["## 来源覆盖", ""])
    for source in payload["source_health"]:
        status = "OK" if source["ok"] else "FAIL"
        suffix = f" - {source['error']}" if source.get("error") else ""
        lines.append(f"- {status} · {source['name']} · {source['count']} 条{suffix}")
    lines.append("")
    return "\n".join(lines)


def render_section(title: str, items: list[dict[str, Any]]) -> list[str]:
    lines = [f"## {title}", ""]
    if not items:
        lines.extend(["暂无足够高质量信号。", ""])
        return lines
    for index, item in enumerate(items, start=1):
        source_links = ", ".join(f"[{source['name']}]({source['url']})" for source in item.get("sources", []))
        lines.extend(
            [
                f"### {index}. {item['title']}",
                "",
                f"- 摘要：{item.get('summary') or '暂无摘要'}",
                f"- 判断：{item.get('reason') or '值得跟进验证。'}",
                f"- 分数：{item.get('score', 0)}",
                f"- 来源：{source_links or item.get('url', '')}",
                "",
            ]
        )
    return lines
