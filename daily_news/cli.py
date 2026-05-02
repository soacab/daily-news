from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from .fetchers import default_sources
from .llm import analyze_candidates
from .models import Candidate, SourceResult
from .pipeline import collect_candidates, merge_candidates, score_candidates
from .publisher import publish_changes
from .render import build_report_payload, write_report_files
from .site import write_static_site
from .codex_analysis import analysis_path, apply_codex_analysis, write_codex_brief


def parse_date(value: str | None) -> dt.date:
    if value:
        return dt.date.fromisoformat(value)
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()


def utc_window_for_report(report_date: dt.date) -> tuple[dt.datetime, dt.datetime]:
    tz = dt.timezone(dt.timedelta(hours=8))
    end_local = dt.datetime.combine(report_date, dt.time(8, 0), tzinfo=tz)
    start_local = end_local - dt.timedelta(days=1)
    return start_local.astimezone(dt.timezone.utc), end_local.astimezone(dt.timezone.utc)


def cache_path(root: Path, report_date: dt.date) -> Path:
    return root / ".cache/daily-news" / f"{report_date.isoformat()}-candidates.json"


def save_collection(root: Path, report_date: dt.date, candidates: list[Candidate], sources: list[SourceResult]) -> Path:
    path = cache_path(root, report_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"candidates": [item.to_dict() for item in candidates], "sources": [source.to_dict() for source in sources]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def load_collection(root: Path, report_date: dt.date) -> tuple[list[Candidate], list[SourceResult]]:
    path = cache_path(root, report_date)
    data = json.loads(path.read_text(encoding="utf-8"))
    candidates = [Candidate.from_dict(item) for item in data.get("candidates", [])]
    sources = [
        SourceResult(
            name=item.get("name", ""),
            ok=bool(item.get("ok")),
            candidates=[Candidate.from_dict(candidate) for candidate in item.get("candidates", [])],
            error=item.get("error", ""),
        )
        for item in data.get("sources", [])
    ]
    return candidates, sources


def command_collect(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    report_date = parse_date(args.date)
    window_start, window_end = utc_window_for_report(report_date)
    collection = collect_candidates(default_sources(), window_start, window_end)
    merged = score_candidates(merge_candidates(collection.candidates))
    path = save_collection(root, report_date, merged, collection.source_results)
    print(f"Collected {len(merged)} candidates -> {path}")
    return 0


def command_generate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    report_date = parse_date(args.date)
    try:
        candidates, sources = load_collection(root, report_date)
    except FileNotFoundError:
        window_start, window_end = utc_window_for_report(report_date)
        collection = collect_candidates(default_sources(), window_start, window_end)
        candidates = score_candidates(merge_candidates(collection.candidates))
        sources = collection.source_results
        save_collection(root, report_date, candidates, sources)
    analysis = analyze_candidates(candidates, report_date.isoformat()) if getattr(args, "use_openai", False) else None
    payload = build_report_payload(report_date, candidates, sources, analysis)
    paths = write_report_files(root, payload)
    print(f"Generated {paths['markdown']}")
    return 0


def command_codex_brief(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    report_date = parse_date(args.date)
    try:
        candidates, sources = load_collection(root, report_date)
    except FileNotFoundError:
        window_start, window_end = utc_window_for_report(report_date)
        collection = collect_candidates(default_sources(), window_start, window_end)
        candidates = score_candidates(merge_candidates(collection.candidates))
        sources = collection.source_results
        save_collection(root, report_date, candidates, sources)
    path = write_codex_brief(root, report_date, candidates, sources)
    print(f"Wrote Codex brief {path}")
    return 0


def command_apply_analysis(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    report_date = parse_date(args.date)
    candidates, sources = load_collection(root, report_date)
    paths = apply_codex_analysis(root, report_date, candidates, sources)
    print(f"Applied Codex analysis -> {paths['markdown']}")
    return 0


def command_build_site(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    path = write_static_site(root)
    print(f"Built {path}")
    return 0


def command_publish(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    report_date = parse_date(args.date)
    result = publish_changes(root, report_date.isoformat(), push=not args.no_push)
    print(result.message)
    return 0 if result.status in {"noop", "published"} else 1


def command_run_daily(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    report_date = parse_date(args.date)
    collect_args = argparse.Namespace(root=root, date=report_date.isoformat())
    brief_args = argparse.Namespace(root=root, date=report_date.isoformat())
    publish_args = argparse.Namespace(root=root, date=report_date.isoformat(), no_push=args.no_push)
    command_collect(collect_args)
    command_codex_brief(brief_args)
    if not analysis_path(root, report_date).exists():
        print(
            "Codex brief is ready. Write the analysis JSON first, then run "
            f"`scripts/daily-news apply-analysis --date {report_date.isoformat()}` and publish."
        )
        return 2
    command_apply_analysis(argparse.Namespace(root=root, date=report_date.isoformat()))
    return command_publish(publish_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="daily-news")
    parser.add_argument("--root", default=".", help="Project root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect")
    collect.add_argument("--date")
    collect.set_defaults(func=command_collect)

    generate = subparsers.add_parser("generate")
    generate.add_argument("--date")
    generate.add_argument("--use-openai", action="store_true", help="Optional legacy OpenAI API generation path")
    generate.set_defaults(func=command_generate)

    codex_brief = subparsers.add_parser("codex-brief")
    codex_brief.add_argument("--date")
    codex_brief.set_defaults(func=command_codex_brief)

    apply_analysis = subparsers.add_parser("apply-analysis")
    apply_analysis.add_argument("--date")
    apply_analysis.set_defaults(func=command_apply_analysis)

    build_site = subparsers.add_parser("build-site")
    build_site.set_defaults(func=command_build_site)

    publish = subparsers.add_parser("publish")
    publish.add_argument("--date")
    publish.add_argument("--no-push", action="store_true")
    publish.set_defaults(func=command_publish)

    run_daily = subparsers.add_parser("run-daily")
    run_daily.add_argument("--date")
    run_daily.add_argument("--no-push", action="store_true")
    run_daily.set_defaults(func=command_run_daily)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
