import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app(tmp_db):
    from lifesource.db import init_db
    from lifesource.server import create_app

    init_db(tmp_db)
    return create_app(db_path=tmp_db)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_create_purchase(client):
    response = await client.post("/api/purchases", json={
        "store": "heb",
        "item_name": "Large Eggs 18ct",
        "price": 2.49,
        "quantity": 1,
        "unit": "each",
        "purchase_date": "2026-04-08",
        "source": "manual",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["item_name"] == "Large Eggs 18ct"
    assert data["id"] is not None


async def test_list_purchases(client):
    await client.post("/api/purchases", json={
        "store": "heb", "item_name": "Eggs", "price": 2.49,
        "purchase_date": "2026-04-08", "source": "manual",
    })
    await client.post("/api/purchases", json={
        "store": "heb", "item_name": "Milk", "price": 3.99,
        "purchase_date": "2026-04-08", "source": "manual",
    })

    response = await client.get("/api/purchases")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
