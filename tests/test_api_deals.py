import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app(tmp_db):
    from lifesource.db import init_db, get_connection
    from lifesource.server import create_app

    init_db(tmp_db)

    conn = get_connection(tmp_db)
    conn.execute(
        """INSERT INTO deals (store, item_name, category, regular_price, sale_price,
           unit, start_date, end_date, source_type)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("heb", "Large Eggs 18ct", "dairy", 3.49, 1.99, "each",
         "2026-04-06", "2026-04-12", "scraper"),
    )
    conn.execute(
        """INSERT INTO deals (store, item_name, category, regular_price, sale_price,
           unit, start_date, end_date, source_type)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("heb", "Whole Milk 1gal", "dairy", 4.99, 3.49, "each",
         "2026-04-06", "2026-04-12", "scraper"),
    )
    conn.commit()
    conn.close()

    return create_app(db_path=tmp_db)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_get_deals(client):
    response = await client.get("/api/deals")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


async def test_get_deals_filter_by_store(client):
    response = await client.get("/api/deals?store=heb")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(d["store"] == "heb" for d in data)


async def test_get_deals_search(client):
    response = await client.get("/api/deals/search?q=eggs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["item_name"] == "Large Eggs 18ct"
