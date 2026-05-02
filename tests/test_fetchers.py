import datetime as dt
import unittest

from daily_news.fetchers import parse_news_page_links


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
            published_at=dt.datetime(2026, 5, 2, tzinfo=dt.timezone.utc).isoformat(),
            limit=5,
        )

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "Introducing Claude Design")
        self.assertEqual(items[0].url, "https://www.anthropic.com/news/introducing-claude-design")
        self.assertEqual(items[0].category, "big_tech")


if __name__ == "__main__":
    unittest.main()
