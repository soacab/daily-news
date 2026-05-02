import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from daily_news.models import Candidate, SourceResult
from daily_news.pipeline import collect_candidates, merge_candidates, score_candidates
from daily_news.render import build_report_payload, write_report_files


class PipelineTests(unittest.TestCase):
    def test_collect_candidates_keeps_results_when_one_source_fails(self):
        class GoodSource:
            name = "good"

            def fetch(self, window_start, window_end):
                return SourceResult(
                    name=self.name,
                    ok=True,
                    candidates=[
                        Candidate(
                            title="OpenAI launches a new agent feature",
                            url="https://example.com/openai-agent",
                            source="good",
                            published_at=window_end.isoformat(),
                            summary="Official product launch.",
                            category="big_tech",
                        )
                    ],
                )

        class BrokenSource:
            name = "broken"

            def fetch(self, window_start, window_end):
                raise RuntimeError("feed unavailable")

        result = collect_candidates(
            [GoodSource(), BrokenSource()],
            dt.datetime(2026, 5, 1, tzinfo=dt.timezone.utc),
            dt.datetime(2026, 5, 2, tzinfo=dt.timezone.utc),
        )

        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].title, "OpenAI launches a new agent feature")
        self.assertEqual(len(result.source_results), 2)
        self.assertFalse(result.source_results[1].ok)
        self.assertIn("feed unavailable", result.source_results[1].error)

    def test_merge_candidates_deduplicates_by_canonical_url_and_keeps_sources(self):
        items = [
            Candidate(
                title="Anthropic introduces Claude Design",
                url="https://www.anthropic.com/news/claude-design?utm_source=hn",
                source="Anthropic",
                published_at="2026-05-02T00:00:00+00:00",
                summary="Official launch.",
                category="big_tech",
            ),
            Candidate(
                title="Claude Design by Anthropic launches",
                url="https://www.anthropic.com/news/claude-design",
                source="Techmeme",
                published_at="2026-05-02T01:00:00+00:00",
                summary="Aggregator coverage.",
                category="product",
            ),
        ]

        merged = merge_candidates(items)

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].url, "https://www.anthropic.com/news/claude-design")
        self.assertEqual(merged[0].sources, ["Anthropic", "Techmeme"])
        self.assertIn("Aggregator coverage.", merged[0].summary)

    def test_score_candidates_promotes_opportunity_and_big_tech_signals(self):
        items = [
            Candidate(
                title="Show HN: AI workflow audit for product teams",
                url="https://news.ycombinator.com/item?id=1",
                source="Hacker News",
                published_at="2026-05-02T00:00:00+00:00",
                summary="Users complain about tracking AI workflow costs.",
                category="product",
                score=0,
            ),
            Candidate(
                title="OpenAI updates API pricing",
                url="https://openai.com/news/api-pricing",
                source="OpenAI",
                published_at="2026-05-02T00:00:00+00:00",
                summary="Official pricing update.",
                category="big_tech",
                score=0,
            ),
        ]

        scored = score_candidates(items)

        self.assertGreater(scored[0].score, 0)
        self.assertGreater(scored[1].score, 0)
        self.assertEqual(scored[0].rank, 1)

    def test_write_report_files_creates_markdown_and_frontend_json(self):
        report_date = dt.date(2026, 5, 2)
        candidate = Candidate(
            title="AI workflow audit tools get traction",
            url="https://example.com/workflow-audit",
            source="Hacker News",
            published_at="2026-05-02T00:00:00+00:00",
            summary="Teams want visibility into agent actions and cost.",
            category="product",
            score=92,
            rank=1,
            reason="Clear user pain around governance.",
            sources=["Hacker News", "Product Hunt"],
        )
        payload = build_report_payload(
            report_date=report_date,
            candidates=[candidate],
            source_results=[SourceResult(name="Hacker News", ok=True, candidates=[candidate])],
            analysis=None,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_report_files(root, payload)

            markdown = paths["markdown"].read_text(encoding="utf-8")
            site_markdown_exists = (root / "site/reports/2026-05-02.md").exists()
            latest = json.loads((root / "site/data/latest.json").read_text(encoding="utf-8"))
            archive = json.loads((root / "site/data/archive.json").read_text(encoding="utf-8"))

        self.assertIn("# AI 产品机会日报 · 2026-05-02", markdown)
        self.assertTrue(site_markdown_exists)
        self.assertEqual(latest["date"], "2026-05-02")
        self.assertEqual(latest["opportunities"][0]["title"], candidate.title)
        self.assertEqual(archive["reports"][0]["path"], "reports/2026-05-02.md")


if __name__ == "__main__":
    unittest.main()
