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


def test_inspect_html_excludes_theme_and_social_assets():
    html = """
    <html>
      <body>
        <img src="https://hmartus.vtexassets.com/assets/vtex/assets-builder/hmartus.store-theme/logo-hmart.png">
        <img src="https://hmartus.vtexassets.com/assets/vtex/assets-builder/hmartus.store-theme/footer/icon-instagram.png">
        <img src="https://www.hmart.com/assets/vtex.file-manager-graphql/images/current.jpg?utm_campaign=Weekly+Sale+-+All">
      </body>
    </html>
    """

    source = HmartTexasWeeklyAdSource()
    result = source.inspect_html(html)

    assert result.assets == []
    assert result.metadata["strategy"] == "raw_html"


def test_inspect_html_accepts_vtex_weekly_ad_image_by_alt_text():
    html = """
    <html>
      <body>
        <img
          alt="Weekly Ad Southern Texas English"
          src="https://hmartus.vtexassets.com/assets/vtex.file-manager-graphql/images/70013bcf-b50a-4332-94a7-dc1b2cb30e5c___0cb517b774be6bba75f676c52b3fbe85.jpg">
      </body>
    </html>
    """

    source = HmartTexasWeeklyAdSource()
    result = source.inspect_html(html)

    assert result.metadata["strategy"] == "weekly_ad_assets"
    assert result.assets == [
        "https://hmartus.vtexassets.com/assets/vtex.file-manager-graphql/images/70013bcf-b50a-4332-94a7-dc1b2cb30e5c___0cb517b774be6bba75f676c52b3fbe85.jpg"
    ]


def test_check_uses_rendered_html_when_raw_html_has_no_assets():
    rendered_html = """
    <html>
      <body>
        <img
          alt="Weekly Ad Southern Texas English"
          src="https://hmartus.vtexassets.com/assets/vtex.file-manager-graphql/images/current___weekly.jpg">
      </body>
    </html>
    """

    class FakeSource(HmartTexasWeeklyAdSource):
        def fetch_html(self):
            return "<html><body><h1>Weekly Ads</h1></body></html>"

        def fetch_rendered_html(self):
            return rendered_html

    result = FakeSource().check()

    assert result.metadata["strategy"] == "rendered_weekly_ad_assets"
    assert result.assets == [
        "https://hmartus.vtexassets.com/assets/vtex.file-manager-graphql/images/current___weekly.jpg"
    ]


def test_inspect_html_excludes_kakaotalk_marketing_promo():
    html = """
    <html>
      <body>
        <img src="https://www.hmart.com/assets/vtex.file-manager-graphql/images/c3d9721c.jpg?utm_campaign=KakaoTalk+All&utm_campaign=Weekly+Sale+-+All">
      </body>
    </html>
    """

    source = HmartTexasWeeklyAdSource()
    result = source.inspect_html(html)

    assert result.assets == []
    assert result.metadata["strategy"] == "raw_html"


def test_inspect_html_deduplicates_html_escaped_asset_urls():
    html = """
    <html>
      <body>
        <img src="https://www.hmart.com/media/weekly-ads/texas/current.jpg?week=1&amp;dm_t=1">
        <script>"https://www.hmart.com/media/weekly-ads/texas/current.jpg?week=1&dm_t=1"</script>
      </body>
    </html>
    """

    source = HmartTexasWeeklyAdSource()
    result = source.inspect_html(html)

    assert result.assets == [
        "https://www.hmart.com/media/weekly-ads/texas/current.jpg?week=1&dm_t=1"
    ]
