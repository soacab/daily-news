import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from daily_news.publisher import publish_changes
from daily_news.site import write_static_site


class SiteAndPublishTests(unittest.TestCase):
    def test_write_static_site_creates_guizang_article_homepage_without_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "site/data"
            data_dir.mkdir(parents=True)
            (data_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "date": "2026-05-02",
                        "title": "AI 产品机会日报",
                        "summary": "今天的重点是 AI 工作流审计和巨头模型更新。",
                        "opportunities": [
                            {
                                "title": "AI 工作流审计",
                                "summary": "团队需要知道代理做了什么。",
                                "reason": "治理痛点明确。",
                                "score": 91,
                                "sources": [{"name": "Hacker News", "url": "https://news.ycombinator.com/"}],
                            }
                        ],
                        "big_tech": [],
                        "pain_points": [],
                        "source_health": [{"name": "Hacker News", "ok": True, "count": 1}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (data_dir / "archive.json").write_text(
                json.dumps({"reports": []}, ensure_ascii=False),
                encoding="utf-8",
            )

            html_path = write_static_site(root)
            html = html_path.read_text(encoding="utf-8")

        self.assertIn("<title>daily-news · AI 产品机会日报</title>", html)
        self.assertIn("AI 产品机会日报", html)
        self.assertIn("靛蓝瓷", html)
        self.assertNotIn("[必填]", html)

    def test_publish_changes_returns_noop_when_git_has_no_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)

            result = publish_changes(root, report_date="2026-05-02", push=False)

        self.assertEqual(result.status, "noop")
        self.assertIn("No changes", result.message)


if __name__ == "__main__":
    unittest.main()
