import pytest
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


class TestBaseScraper:
    def test_base_scraper_is_abstract(self):
        from lifesource.scrapers.base import BaseScraper

        with pytest.raises(TypeError):
            BaseScraper()

    def test_base_scraper_retry_on_failure(self, httpx_mock):
        from lifesource.scrapers.base import BaseScraper
        from lifesource.models import Deal

        # First two requests fail, third succeeds
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(status_code=200, text="<html>ok</html>")

        class TestScraper(BaseScraper):
            store_name = "test"

            def parse(self, html: str) -> list[Deal]:
                return []

            def get_url(self) -> str:
                return "https://example.com"

        scraper = TestScraper(retry_delay=0.01)
        result = scraper.fetch("https://example.com")
        assert result == "<html>ok</html>"
        assert len(httpx_mock.get_requests()) == 3

    def test_base_scraper_gives_up_after_max_retries(self, httpx_mock):
        from lifesource.scrapers.base import BaseScraper, ScraperError
        from lifesource.models import Deal

        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(status_code=500)

        class TestScraper(BaseScraper):
            store_name = "test"

            def parse(self, html: str) -> list[Deal]:
                return []

            def get_url(self) -> str:
                return "https://example.com"

        scraper = TestScraper(max_retries=3, retry_delay=0.01)
        with pytest.raises(ScraperError):
            scraper.fetch("https://example.com")


class TestHebScraper:
    def test_parse_deals_from_sample(self):
        from lifesource.scrapers.heb import HebScraper

        sample = (FIXTURES / "heb_sample.html").read_text()
        scraper = HebScraper()
        deals = scraper.parse(sample)

        # 5 products in fixture, but one has empty name and one has no SKUs
        # So we expect 4 valid deals
        assert len(deals) == 4
        for deal in deals:
            assert deal.store == "heb"
            assert deal.item_name
            assert deal.sale_price > 0
            assert deal.source_type == "scraper"

    def test_parse_extracts_correct_prices(self):
        from lifesource.scrapers.heb import HebScraper

        sample = (FIXTURES / "heb_sample.html").read_text()
        scraper = HebScraper()
        deals = scraper.parse(sample)

        apple = next(d for d in deals if "Fuji Apple" in d.item_name)
        assert apple.sale_price == 0.6
        assert apple.regular_price == 0.98
        assert apple.unit == "lb"
        assert apple.category == "Fruit & vegetables"

    def test_parse_extracts_category(self):
        from lifesource.scrapers.heb import HebScraper

        sample = (FIXTURES / "heb_sample.html").read_text()
        scraper = HebScraper()
        deals = scraper.parse(sample)

        milk = next(d for d in deals if "Milk" in d.item_name)
        assert milk.category == "Dairy & eggs"

    def test_parse_returns_empty_on_no_deals(self):
        from lifesource.scrapers.heb import HebScraper

        scraper = HebScraper()
        deals = scraper.parse("<html><body>No deals here</body></html>")
        assert deals == []

    def test_parse_returns_empty_on_empty_json(self):
        from lifesource.scrapers.heb import HebScraper

        scraper = HebScraper()
        deals = scraper.parse("{}")
        assert deals == []
