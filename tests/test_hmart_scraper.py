import json

from lifesource.scrapers.hmart import HmartScraper


def test_hmart_generic_sale_scraper_does_not_emit_weekly_ad_deals():
    payload = {
        "@type": "ItemList",
        "name": "Sale",
        "itemListElement": [
            {
                "item": {
                    "@type": "Product",
                    "name": "Korean Pear",
                    "image": "https://example.com/pear.jpg",
                    "offers": {"price": "2.99"},
                }
            }
        ],
    }
    html = f"""
    <html>
      <script type="application/ld+json">{json.dumps(payload)}</script>
    </html>
    """

    deals = HmartScraper().parse(html)

    assert len(deals) == 1
    assert deals[0].source_type != "weekly_ad"
    assert deals[0].source_url == "https://www.hmart.com/sale"
