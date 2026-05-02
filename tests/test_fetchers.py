import unittest

from daily_news.fetchers import infer_date_from_url, parse_news_page_links


class FetcherTests(unittest.TestCase):
    def test_parse_news_page_links_extracts_ai_news_cards(self):
        html = """
        <a href="/news/introducing-claude-design">Introducing Claude Design</a>
        <a href="https://www.anthropic.com/news/project-glasswing">Project Glasswing</a>
        <a href="/company">Company</a>
        """

        items = parse_news_page_links(
            html,
            base_url="https://www.anthropic.com/news",
            source_name="Anthropic Newsroom",
            category="big_tech",
            limit=5,
        )

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "Introducing Claude Design")
        self.assertEqual(items[0].url, "https://www.anthropic.com/news/introducing-claude-design")
        self.assertEqual(items[0].category, "big_tech")

    def test_parse_news_page_links_extracts_dates_and_filters_window(self):
        html = """
        <a href="/news/claude-opus-4-7">
          Product Apr 16, 2026 Introducing Claude Opus 4.7 Product Apr 16, 2026 Our latest model.
        </a>
        <a href="/news/claude-design-anthropic-labs">
          Product May 1, 2026 Introducing Claude Design by Anthropic Labs
        </a>
        """

        items = parse_news_page_links(
            html,
            base_url="https://www.anthropic.com/news",
            source_name="Anthropic Newsroom",
            category="big_tech",
            limit=5,
            window_start_iso="2026-05-01T00:00:00+00:00",
            window_end_iso="2026-05-02T00:00:00+00:00",
        )

        self.assertEqual([item.title for item in items], ["Introducing Claude Design by Anthropic Labs"])
        self.assertEqual(items[0].published_at, "2026-05-01T00:00:00+00:00")

    def test_infer_date_from_url_supports_common_news_patterns(self):
        self.assertEqual(
            infer_date_from_url("https://fortune.com/2026/04/27/avoca-ai-agents").date().isoformat(),
            "2026-04-27",
        )
        self.assertEqual(
            infer_date_from_url("https://www.bloomberg.com/news/articles/2026-05-01/ai-tools").date().isoformat(),
            "2026-05-01",
        )


if __name__ == "__main__":
    unittest.main()
