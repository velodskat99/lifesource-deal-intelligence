from fastapi import APIRouter, BackgroundTasks

from lifesource.daily.job import run_daily_job


def create_job_router(db_path: str) -> APIRouter:
    router = APIRouter()

    @router.post("/job/run")
    def trigger_daily_job(background_tasks: BackgroundTasks):
        """Manually trigger the daily scraping job."""
        background_tasks.add_task(run_daily_job, db_path)
        return {"status": "started", "message": "Daily job triggered in background"}

    return router
