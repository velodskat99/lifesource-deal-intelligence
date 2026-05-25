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
async def test_hmart_source_status_returns_empty_state_for_fresh_db(client):
    response = await client.get("/api/sources/hmart-texas/status")

    assert response.status_code == 200
    data = response.json()
    assert data["store"] == "hmart"
    assert data["region"] == "texas"
    assert data["source_url"] == HMART_TEXAS_WEEKLY_AD_URL
    assert data["has_snapshot"] is False
    assert data["asset_count"] == 0
    assert data["item_count"] == 0
    assert data["fingerprint"] is None


@pytest.mark.anyio
async def test_hmart_source_status_returns_latest_snapshot(client, tmp_db):
    record_source_snapshot(
        tmp_db,
        SourceSnapshot(
            store="hmart",
            region="texas",
            source_url=HMART_TEXAS_WEEKLY_AD_URL,
            source_type="weekly_ad",
            fingerprint="abc123456789",
            raw_metadata={"assets": ["https://cdn.hmart.com/ad-1.jpg"], "strategy": "weekly_ad_assets"},
        ),
    )

    response = await client.get("/api/sources/hmart-texas/status")

    assert response.status_code == 200
    data = response.json()
    assert data["has_snapshot"] is True
    assert data["asset_count"] == 1
    assert data["fingerprint"] == "abc123456789"
    assert data["strategy"] == "weekly_ad_assets"


@pytest.mark.anyio
async def test_hmart_source_status_counts_item_level_rows(client, tmp_db):
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
                sale_price=8.99,
            ),
            WeeklyAdItem(
                store="hmart",
                region="texas",
                source_url=HMART_TEXAS_WEEKLY_AD_URL,
                item_name="Napa Cabbage",
                sale_price=0.99,
            ),
        ],
    )

    response = await client.get("/api/sources/hmart-texas/status")

    assert response.status_code == 200
    data = response.json()
    assert data["item_count"] == 2


@pytest.mark.anyio
async def test_hmart_source_items_endpoint_returns_item_level_rows(client, tmp_db):
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
                asset_url="https://cdn.hmart.com/weekly-ad-page-1.jpg",
                item_name="Short Rib",
                category="meat",
                sale_price=8.99,
                unit="lb",
                confidence=0.91,
                raw_text="Short Rib $8.99/lb",
            )
        ],
    )

    response = await client.get("/api/sources/hmart-texas/items")

    assert response.status_code == 200
    data = response.json()
    assert data["store"] == "hmart"
    assert data["region"] == "texas"
    assert data["item_count"] == 1
    assert data["items"][0]["item_name"] == "Short Rib"
    assert data["items"][0]["sale_price"] == 8.99
    assert data["items"][0]["status"] == "pending_review"


@pytest.mark.anyio
async def test_hmart_source_items_endpoint_replaces_item_level_rows(client):
    response = await client.post(
        "/api/sources/hmart-texas/items",
        json={
            "items": [
                {
                    "source_url": HMART_TEXAS_WEEKLY_AD_URL,
                    "asset_url": "https://cdn.hmart.com/weekly-ad-page-1.jpg",
                    "item_name": "Short Rib",
                    "category": "meat",
                    "sale_price": 8.99,
                    "unit": "lb",
                    "confidence": 0.91,
                    "raw_text": "Short Rib $8.99/lb",
                }
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["item_count"] == 1
    assert data["items"][0]["item_name"] == "Short Rib"


@pytest.mark.anyio
async def test_hmart_source_extract_endpoint_skips_without_weekly_ad_assets(client):
    response = await client.post("/api/sources/hmart-texas/extract-items")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "skipped"
    assert data["reason"] == "no_weekly_ad_assets"
    assert data["item_count"] == 0


@pytest.mark.anyio
async def test_hmart_source_manual_asset_endpoint_adds_trusted_asset(client):
    asset_url = "https://hmartus.vtexassets.com/assets/vtex.file-manager-graphql/images/70013bcf-b50a-4332-94a7-dc1b2cb30e5c___0cb517b774be6bba75f676c52b3fbe85.jpg"

    response = await client.post(
        "/api/sources/hmart-texas/assets",
        json={"asset_url": asset_url},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"]["asset_count"] == 1
    assert data["status"]["assets"] == [asset_url]
    assert data["status"]["strategy"] == "manual_weekly_ad_assets"


@pytest.mark.anyio
async def test_hmart_source_manual_asset_endpoint_rejects_non_weekly_asset(client):
    response = await client.post(
        "/api/sources/hmart-texas/assets",
        json={
            "asset_url": "https://www.hmart.com/assets/vtex.file-manager-graphql/images/kakaotalk.jpg"
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Asset URL does not look like a H Mart weekly-ad image or PDF."


@pytest.mark.anyio
async def test_hmart_source_manual_asset_endpoint_rejects_non_hmart_host(client):
    response = await client.post(
        "/api/sources/hmart-texas/assets",
        json={"asset_url": "https://example.com/weekly-ads/texas/page-1.jpg"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Asset URL does not look like a H Mart weekly-ad image or PDF."


@pytest.mark.anyio
async def test_hmart_source_extract_endpoint_runs_vision_extractor(
    client,
    tmp_db,
    monkeypatch,
):
    asset_url = "https://cdn.hmart.com/weekly-ads/texas/page-1.jpg"
    record_source_snapshot(
        tmp_db,
        SourceSnapshot(
            store="hmart",
            region="texas",
            source_url=HMART_TEXAS_WEEKLY_AD_URL,
            source_type="weekly_ad",
            fingerprint="abc123456789",
            raw_metadata={"assets": [asset_url], "strategy": "weekly_ad_assets"},
        ),
    )
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "configured-test-key")

    from lifesource.config import get_settings
    from lifesource.api import sources

    get_settings.cache_clear()

    class FakeVisionExtractor:
        def __init__(self, api_key):
            assert api_key == "configured-test-key"

        def extract(self, asset_url):
            return [{"item_name": "Short Rib", "sale_price": 8.99, "unit": "lb"}]

    monkeypatch.setattr(sources, "VisionWeeklyAdAssetExtractor", FakeVisionExtractor)

    response = await client.post("/api/sources/hmart-texas/extract-items")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["item_count"] == 1
    assert data["items"][0]["item_name"] == "Short Rib"


@pytest.mark.anyio
async def test_hmart_source_manual_check_records_snapshot(client, monkeypatch):
    inspection = WeeklyAdInspection(
        source_url=HMART_TEXAS_WEEKLY_AD_URL,
        fingerprint="def456",
        assets=["https://cdn.hmart.com/ad-1.jpg", "https://cdn.hmart.com/ad-2.jpg"],
        metadata={"strategy": "weekly_ad_assets"},
        warnings=[],
    )

    class FakeSource:
        store = "hmart"
        region = "texas"
        source_type = "weekly_ad"

        def check(self):
            return inspection

    from lifesource.api import sources

    monkeypatch.setattr(sources, "HmartTexasWeeklyAdSource", FakeSource)

    response = await client.post("/api/sources/hmart-texas/check")

    assert response.status_code == 200
    data = response.json()
    assert data["changed"] is True
    assert data["status"]["asset_count"] == 2
    assert data["status"]["fingerprint"] == "def456"
