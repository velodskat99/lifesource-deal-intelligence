import hashlib
import hmac
from fastapi import FastAPI
from fastapi import Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from lifesource.api.deals import create_deals_router
from lifesource.api.purchases import create_purchases_router
from lifesource.api.job import create_job_router
from lifesource.api.plan import create_plan_router
from lifesource.api.shopping_list import create_shopping_list_router
from lifesource.api.gas import create_gas_router
from lifesource.api.receipts import create_receipts_router
from lifesource.api.watchlist import create_watchlist_router
from lifesource.api.analytics import create_analytics_router
from lifesource.api.settings import create_settings_router
from lifesource.api.sources import create_sources_router
from lifesource.dashboard.routes import create_dashboard_router
from lifesource.db import init_db


def _auth_cookie_value(access_pin: str) -> str:
    return hmac.new(
        access_pin.encode("utf-8"),
        b"lifesource-local-access",
        hashlib.sha256,
    ).hexdigest()


def _is_public_mobile_path(path: str) -> bool:
    return (
        path == "/login"
        or path == "/manifest.webmanifest"
        or path == "/service-worker.js"
        or path.startswith("/static/")
    )


def create_app(db_path: str | None = None, access_pin: str | None = None) -> FastAPI:
    """Create the FastAPI application."""
    if db_path is None:
        from lifesource.config import get_settings
        settings = get_settings()
        db_path = settings.db_path
        access_pin = access_pin if access_pin is not None else settings.access_pin

    init_db(db_path)

    app = FastAPI(title="LifeSource", version="0.1.0")
    static_dir = Path(__file__).parent / "static"

    if access_pin:
        expected_cookie = _auth_cookie_value(access_pin)

        @app.middleware("http")
        async def local_access_guard(request: Request, call_next):
            if _is_public_mobile_path(request.url.path):
                return await call_next(request)
            if request.cookies.get("lifesource_auth") == expected_cookie:
                return await call_next(request)
            if request.url.path.startswith("/api/"):
                return JSONResponse({"detail": "LifeSource access PIN required"}, status_code=401)
            return RedirectResponse("/login", status_code=303)

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def web_manifest():
        return JSONResponse(
            {
                "name": "LifeSource",
                "short_name": "LifeSource",
                "description": "Local-first grocery deal intelligence and shopping planner.",
                "start_url": "/",
                "scope": "/",
                "display": "standalone",
                "background_color": "#faf9f7",
                "theme_color": "#1c1917",
                "icons": [
                    {
                        "src": "/static/icons/lifesource.svg",
                        "sizes": "any",
                        "type": "image/svg+xml",
                        "purpose": "any maskable",
                    }
                ],
            },
            media_type="application/manifest+json",
        )

    @app.get("/service-worker.js", include_in_schema=False)
    def service_worker():
        return FileResponse(
            static_dir / "service-worker.js",
            media_type="application/javascript",
        )

    @app.get("/login", response_class=HTMLResponse, include_in_schema=False)
    def login_page():
        return HTMLResponse(
            """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#1c1917">
  <title>LifeSource Access</title>
  <style>
    body{margin:0;min-height:100vh;display:grid;place-items:center;background:#faf9f7;color:#1c1917;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    main{width:min(24rem,calc(100vw - 2rem));padding:2rem;background:white;border:1px solid rgba(28,25,23,.1);box-shadow:0 20px 60px rgba(28,25,23,.08)}
    h1{margin:0 0 .5rem;font-size:1.6rem}
    p{margin:0 0 1.25rem;color:#57534e}
    label{display:block;margin-bottom:.4rem;font-size:.85rem;font-weight:650}
    input{width:100%;box-sizing:border-box;padding:.85rem;border:1px solid #d6d3d1;font:inherit}
    button{width:100%;margin-top:1rem;padding:.85rem;border:0;background:#1c1917;color:white;font:inherit;font-weight:700}
  </style>
</head>
<body>
  <main>
    <h1>LifeSource Access</h1>
    <p>Enter your local PIN to open this private household app.</p>
    <form method="post" action="/login">
      <label for="pin">PIN</label>
      <input id="pin" name="pin" type="password" inputmode="numeric" autocomplete="current-password" autofocus required>
      <button type="submit">Unlock</button>
    </form>
  </main>
</body>
</html>"""
        )

    @app.post("/login", include_in_schema=False)
    def login(pin: str = Form()):
        if not access_pin or not hmac.compare_digest(pin, access_pin):
            return HTMLResponse("Invalid LifeSource access PIN.", status_code=401)
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            "lifesource_auth",
            _auth_cookie_value(access_pin),
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 30,
        )
        return response

    @app.post("/logout", include_in_schema=False)
    def logout():
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie("lifesource_auth")
        return response

    # API routes
    app.include_router(create_deals_router(db_path), prefix="/api")
    app.include_router(create_purchases_router(db_path), prefix="/api")
    app.include_router(create_job_router(db_path), prefix="/api")
    app.include_router(create_plan_router(db_path), prefix="/api")
    app.include_router(create_shopping_list_router(db_path), prefix="/api")
    app.include_router(create_gas_router(db_path), prefix="/api")
    app.include_router(create_receipts_router(db_path), prefix="/api")
    app.include_router(create_watchlist_router(db_path), prefix="/api")
    app.include_router(create_analytics_router(db_path), prefix="/api")
    app.include_router(create_settings_router(db_path), prefix="/api")
    app.include_router(create_sources_router(db_path), prefix="/api")

    # Dashboard routes (HTML pages)
    app.include_router(create_dashboard_router(db_path))

    # Static files
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app
