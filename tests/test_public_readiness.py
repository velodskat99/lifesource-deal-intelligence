import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app(tmp_db):
    from lifesource.server import create_app

    return create_app(db_path=tmp_db)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/gas",
        "/watchlist",
        "/savings",
        "/api/gas",
        "/api/watchlist",
    ],
)
async def test_fresh_database_routes_load(client, path):
    response = await client.get(path)

    assert response.status_code == 200


async def test_savings_page_has_no_baked_in_personal_receipts(client):
    response = await client.get("/savings")

    assert response.status_code == 200
    assert "CHOBANI" not in response.text
    assert "DUMPLING" not in response.text
    assert "Costco receipts" not in response.text
