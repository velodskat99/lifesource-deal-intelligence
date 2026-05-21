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


async def test_manifest_exposes_installable_mobile_app_metadata(client):
    response = await client.get("/manifest.webmanifest")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/manifest+json")
    manifest = response.json()
    assert manifest["name"] == "LifeSource"
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/"
    assert any(icon["src"] == "/static/icons/lifesource.svg" for icon in manifest["icons"])


async def test_home_page_registers_pwa_assets(client):
    response = await client.get("/")

    assert response.status_code == 200
    assert 'rel="manifest"' in response.text
    assert "/service-worker.js" in response.text


async def test_service_worker_is_served_as_javascript(client):
    response = await client.get("/service-worker.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/javascript")
    assert "lifesource-static" in response.text


async def test_access_pin_redirects_private_pages_until_login(tmp_db):
    from lifesource.server import create_app

    protected_app = create_app(db_path=tmp_db, access_pin="2468")
    transport = ASGITransport(app=protected_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=False,
    ) as protected_client:
        response = await protected_client.get("/")
        assert response.status_code == 303
        assert response.headers["location"] == "/login"

        login_page = await protected_client.get("/login")
        assert login_page.status_code == 200
        assert "LifeSource Access" in login_page.text

        failed = await protected_client.post("/login", data={"pin": "0000"})
        assert failed.status_code == 401

        logged_in = await protected_client.post("/login", data={"pin": "2468"})
        assert logged_in.status_code == 303
        assert logged_in.headers["location"] == "/"
        assert "lifesource_auth=" in logged_in.headers["set-cookie"]

        cookie = logged_in.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]
        unlocked = await protected_client.get(
            "/",
            headers={"cookie": f"lifesource_auth={cookie}"},
        )
        assert unlocked.status_code == 200


def test_readme_documents_phone_lan_mode():
    readme = open("README.md", encoding="utf-8").read()

    assert "HOST=0.0.0.0" in readme
    assert "LIFESOURCE_ACCESS_PIN" in readme
    assert "Add to Home Screen" in readme
