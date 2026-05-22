import pytest
from httpx import ASGITransport, AsyncClient

from lifesource.sources.hmart_weekly import HMART_TEXAS_WEEKLY_AD_URL, WeeklyAdInspection
from lifesource.sources.snapshots import SourceSnapshot, record_source_snapshot


@pytest.fixture
def app(tmp_db):
    from lifesource.server import create_app

    return create_app(db_path=tmp_db)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_sources_page_shows_hmart_asset_links(client, tmp_db):
    record_source_snapshot(
        tmp_db,
        SourceSnapshot(
            store="hmart",
            region="texas",
            source_url=HMART_TEXAS_WEEKLY_AD_URL,
            source_type="weekly_ad",
            fingerprint="abc123",
            raw_metadata={
                "assets": ["https://cdn.hmart.com/weekly-ad-page.jpg"],
                "strategy": "weekly_ad_assets",
            },
        ),
    )

    response = await client.get("/sources")

    assert response.status_code == 200
    assert "Weekly Ad Assets" in response.text
    assert "https://cdn.hmart.com/weekly-ad-page.jpg" in response.text


@pytest.mark.anyio
async def test_sources_page_shows_item_level_empty_state(client):
    response = await client.get("/sources")

    assert response.status_code == 200
    assert "Item-Level Data" in response.text
    assert "No extracted H Mart items yet." in response.text


@pytest.mark.anyio
async def test_sources_page_shows_item_level_rows(client, tmp_db):
    from lifesource.sources.weekly_items import WeeklyAdItem, replace_weekly_ad_items

    replace_weekly_ad_items(
        tmp_db,
        store="hmart",
        region="texas",
        items=[
            WeeklyAdItem(
                store="hmart",
                region="texas",
                source_url=HMART_TEXAS_WEEKLY_AD_URL,
                item_name="Short Rib",
                category="meat",
                sale_price=8.99,
                unit="lb",
                confidence=0.91,
            )
        ],
    )

    response = await client.get("/sources")

    assert response.status_code == 200
    assert "Short Rib" in response.text
    assert "$8.99" in response.text
    assert "pending_review" in response.text


@pytest.mark.anyio
async def test_sources_check_redirects_back_to_sources(client, monkeypatch):
    class FakeSource:
        store = "hmart"
        region = "texas"
        source_type = "weekly_ad"

        def check(self):
            return WeeklyAdInspection(
                source_url=HMART_TEXAS_WEEKLY_AD_URL,
                fingerprint="def456",
                assets=["https://cdn.hmart.com/weekly-ad-page.jpg"],
                metadata={"strategy": "weekly_ad_assets"},
                warnings=[],
            )

    from lifesource.dashboard import routes

    monkeypatch.setattr(routes, "HmartTexasWeeklyAdSource", FakeSource)

    response = await client.post("/sources/hmart-texas/check")

    assert response.status_code == 303
    assert response.headers["location"] == "/sources?checked=1&changed=1"
