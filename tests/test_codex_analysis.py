import datetime as dt
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from daily_news.codex_analysis import (
    analysis_path,
    apply_codex_analysis,
    render_codex_brief,
    validate_analysis,
    write_codex_brief,
)
from daily_news.models import Candidate, SourceResult
from daily_news.render import build_report_payload


class CodexAnalysisTests(unittest.TestCase):
    def test_render_codex_brief_includes_candidate_context_and_output_path(self):
        candidate = Candidate(
            title="Show HN: Agent cost monitor",
            url="https://news.ycombinator.com/item?id=1",
            source="Hacker News",
            published_at="2026-05-02T00:00:00+00:00",
            summary="Teams discuss unpredictable agent costs.",
            category="product",
            score=90,
            rank=1,
            reason="Cost pain is explicit.",
        )

        brief = render_codex_brief(dt.date(2026, 5, 2), [candidate], [SourceResult("Hacker News", True, [candidate])])

        self.assertIn("Codex 原生分析任务", brief)
        self.assertIn(".cache/daily-news/2026-05-02-analysis.json", brief)
        self.assertIn("Show HN: Agent cost monitor", brief)
        self.assertIn("只使用候选数据里的来源 URL", brief)

    def test_validate_analysis_requires_core_sections(self):
        analysis = {
            "summary": "今天的机会来自成本可视化和代理治理。",
            "opportunities": [{"title": "Agent cost monitor", "summary": "成本痛点明确。", "reason": "预算不可控。", "source_urls": ["https://example.com/a"]}],
            "big_tech": [{"title": "OpenAI platform update", "summary": "平台能力变化。", "reason": "影响分发。", "source_urls": ["https://example.com/b"]}],
            "pain_points": [{"title": "Teams cannot audit agents", "summary": "治理难。", "reason": "企业采用阻力。", "source_urls": ["https://example.com/c"]}],
        }

        validate_analysis(analysis)

        broken = dict(analysis)
        broken["opportunities"] = []
        with self.assertRaises(ValueError):
            validate_analysis(broken)

    def test_apply_codex_analysis_writes_markdown_json_and_site_from_codex_text(self):
        report_date = dt.date(2026, 5, 2)
        candidate = Candidate(
            title="Agent cost monitor",
            url="https://example.com/a",
            source="Hacker News",
            published_at="2026-05-02T00:00:00+00:00",
            summary="Original candidate summary.",
            category="product",
            score=90,
            rank=1,
            reason="Original reason.",
        )
        analysis = {
            "summary": "Codex 判断：代理成本监控正在变成产品机会。",
            "opportunities": [{"title": "代理成本监控", "summary": "团队需要按任务追踪代理成本。", "reason": "预算摩擦已经出现在社区讨论里。", "source_urls": ["https://example.com/a"]}],
            "big_tech": [{"title": "平台能力变化", "summary": "巨头更新会影响工具入口。", "reason": "需要观察分发权。", "source_urls": ["https://example.com/a"]}],
            "pain_points": [{"title": "成本不可解释", "summary": "用户不知道每次代理调用花在哪里。", "reason": "这是明确采购阻力。", "source_urls": ["https://example.com/a"]}],
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = analysis_path(root, report_date)
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(analysis, ensure_ascii=False), encoding="utf-8")
            paths = apply_codex_analysis(root, report_date, [candidate], [SourceResult("Hacker News", True, [candidate])])
            markdown = paths["markdown"].read_text(encoding="utf-8")
            latest = json.loads((root / "site/data/latest.json").read_text(encoding="utf-8"))

        self.assertIn("Codex 判断", markdown)
        self.assertIn("代理成本监控", markdown)
        self.assertEqual(latest["opportunities"][0]["title"], "代理成本监控")
        self.assertEqual(latest["opportunities"][0]["sources"][0]["url"], "https://example.com/a")

    def test_build_report_payload_prefers_codex_analysis_sections(self):
        report_date = dt.date(2026, 5, 2)
        candidate = Candidate(
            title="Original title",
            url="https://example.com/original",
            source="Source",
            published_at="2026-05-02T00:00:00+00:00",
            summary="Original summary.",
            category="product",
        )
        analysis = {
            "summary": "Codex summary.",
            "opportunities": [{"title": "Codex title", "summary": "Codex summary item.", "reason": "Codex reason.", "source_urls": ["https://example.com/original"]}],
            "big_tech": [{"title": "Codex big tech", "summary": "Codex big tech item.", "reason": "Codex reason.", "source_urls": ["https://example.com/original"]}],
            "pain_points": [{"title": "Codex pain", "summary": "Codex pain item.", "reason": "Codex reason.", "source_urls": ["https://example.com/original"]}],
        }

        payload = build_report_payload(report_date, [candidate], [SourceResult("Source", True, [candidate])], analysis)

        self.assertEqual(payload["summary"], "Codex summary.")
        self.assertEqual(payload["opportunities"][0]["title"], "Codex title")
        self.assertEqual(payload["big_tech"][0]["title"], "Codex big tech")
        self.assertEqual(payload["pain_points"][0]["title"], "Codex pain")

    def test_write_codex_brief_creates_cache_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_codex_brief(root, dt.date(2026, 5, 2), [], [])
            text = path.read_text(encoding="utf-8")

        self.assertEqual(path.name, "2026-05-02-codex-brief.md")
        self.assertIn("2026-05-02-analysis.json", text)


if __name__ == "__main__":
    unittest.main()
