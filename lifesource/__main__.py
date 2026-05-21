"""Entry point: python -m lifesource starts the FastAPI server."""
import uvicorn

from lifesource.config import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "lifesource.server:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
