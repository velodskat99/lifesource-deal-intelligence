from fastapi import APIRouter

from lifesource.sources.hmart_weekly import HmartTexasWeeklyAdSource
from lifesource.sources.status import get_hmart_texas_status, record_hmart_texas_inspection


def create_sources_router(db_path: str) -> APIRouter:
    router = APIRouter()

    @router.get("/sources/hmart-texas/status")
    def hmart_texas_status():
        return get_hmart_texas_status(db_path)

    @router.post("/sources/hmart-texas/check")
    def check_hmart_texas():
        inspection = HmartTexasWeeklyAdSource().check()
        return record_hmart_texas_inspection(db_path, inspection)

    return router
