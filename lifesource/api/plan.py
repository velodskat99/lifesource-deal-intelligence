from fastapi import APIRouter

from lifesource.scoring.planner import generate_shopping_plan


def create_plan_router(db_path: str) -> APIRouter:
    router = APIRouter()

    @router.get("/plan")
    def get_shopping_plan():
        return generate_shopping_plan(db_path)

    return router
