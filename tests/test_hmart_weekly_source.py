from lifesource.sources.hmart_weekly import HmartTexasWeeklyAdSource


def test_inspect_html_fingerprints_weekly_ad_assets():
    html = """
    <html>
      <body>
        <h1>Weekly Ads Texas</h1>
        <p>Valid May 17 - May 23, 2026</p>
        <img src="/media/weekly-ads/texas/page-1.jpg">
        <a href="https://cdn.hmart.com/weekly-ads/texas/page-2.jpg">Page 2</a>
        <script>{"pdf":"https://cdn.hmart.com/weekly-ads/texas/current.pdf"}</script>
      </body>
    </html>
    """

    source = HmartTexasWeeklyAdSource()
    result = source.inspect_html(html)

    assert result.source_url == "https://www.hmart.com/weekly-ads-texas#/"
    assert result.fingerprint
    assert result.metadata["strategy"] == "weekly_ad_assets"
    assert result.metadata["date_labels"] == ["Valid May 17 - May 23, 2026"]
    assert result.assets == [
        "https://www.hmart.com/media/weekly-ads/texas/page-1.jpg",
        "https://cdn.hmart.com/weekly-ads/texas/page-2.jpg",
        "https://cdn.hmart.com/weekly-ads/texas/current.pdf",
    ]


def test_inspect_html_falls_back_to_raw_html_when_no_assets_exist():
    html = "<html><body><h1>Weekly Ads</h1><p>Select your state:</p></body></html>"

    source = HmartTexasWeeklyAdSource()
    result = source.inspect_html(html)

    assert result.fingerprint
    assert result.metadata["strategy"] == "raw_html"
    assert result.assets == []
    assert result.warnings == ["No weekly-ad assets found; fingerprint uses raw HTML."]
