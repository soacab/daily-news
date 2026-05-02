import datetime as dt
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from daily_news.cli import main
from daily_news.models import Candidate, SourceResult
from daily_news.cli import save_collection
from daily_news.codex_analysis import analysis_path


class CliCodexFlowTests(unittest.TestCase):
    def test_codex_brief_command_writes_brief_without_openai_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_date = dt.date(2026, 5, 2)
            candidate = Candidate(
                title="Agent audit trail",
                url="https://example.com/audit",
                source="Hacker News",
                published_at="2026-05-02T00:00:00+00:00",
                summary="Teams need auditability.",
                category="product",
                rank=1,
                score=88,
            )
            save_collection(root, report_date, [candidate], [SourceResult("Hacker News", True, [candidate])])

            code = main(["--root", str(root), "codex-brief", "--date", "2026-05-02"])
            brief = root / ".cache/daily-news/2026-05-02-codex-brief.md"
            brief_exists = brief.exists()
            brief_text = brief.read_text(encoding="utf-8")

        self.assertEqual(code, 0)
        self.assertTrue(brief_exists)
        self.assertIn("Codex 原生分析任务", brief_text)

    def test_apply_analysis_command_uses_codex_json_to_build_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            report_date = dt.date(2026, 5, 2)
            candidate = Candidate(
                title="Agent audit trail",
                url="https://example.com/audit",
                source="Hacker News",
                published_at="2026-05-02T00:00:00+00:00",
                summary="Teams need auditability.",
                category="product",
                rank=1,
                score=88,
            )
            save_collection(root, report_date, [candidate], [SourceResult("Hacker News", True, [candidate])])
            analysis_path(root, report_date).write_text(
                json.dumps(
                    {
                        "summary": "Codex 写出的日报总览。",
                        "opportunities": [{"title": "代理审计轨迹", "summary": "团队需要追踪代理行为。", "reason": "这是企业采用的治理门槛。", "source_urls": ["https://example.com/audit"]}],
                        "big_tech": [{"title": "平台审计能力", "summary": "平台能力变化。", "reason": "影响企业购买。", "source_urls": ["https://example.com/audit"]}],
                        "pain_points": [{"title": "行为不可追踪", "summary": "用户不知道代理做过什么。", "reason": "信任成本很高。", "source_urls": ["https://example.com/audit"]}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            code = main(["--root", str(root), "apply-analysis", "--date", "2026-05-02"])
            markdown = (root / "reports/2026-05-02.md").read_text(encoding="utf-8")
            html = (root / "site/index.html").read_text(encoding="utf-8")

        self.assertEqual(code, 0)
        self.assertIn("Codex 写出的日报总览", markdown)
        self.assertIn("代理审计轨迹", html)


if __name__ == "__main__":
    unittest.main()
