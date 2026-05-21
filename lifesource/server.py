from fastapi import FastAPI
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
from lifesource.dashboard.routes import create_dashboard_router
from lifesource.db import init_db


def create_app(db_path: str | None = None) -> FastAPI:
    """Create the FastAPI application."""
    if db_path is None:
        from lifesource.config import get_settings
        db_path = get_settings().db_path

    init_db(db_path)

    app = FastAPI(title="LifeSource", version="0.1.0")

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

    # Dashboard routes (HTML pages)
    app.include_router(create_dashboard_router(db_path))

    # Static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app
