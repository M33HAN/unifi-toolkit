"""
Wi-Fi Stalker FastAPI application factory
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from tools.wifi_stalker import __version__
from tools.wifi_stalker.routers import devices, config, webhooks

# Get the directory containing this file
BASE_DIR = Path(__file__).parent

# Set up templates and static files
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def create_app() -> FastAPI:
    """
    Create and configure the Wi-Fi Stalker sub-application

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Wi-Fi Stalker",
        version=__version__,
        description="Track specific Wi-Fi client devices through UniFi infrastructure"
    )

    # Mount static files
    app.mount(
        "/static",
        StaticFiles(directory=str(BASE_DIR / "static")),
        name="static"
    )

    # Include API routers
    app.include_router(devices.router)
    app.include_router(config.router)
    app.include_router(webhooks.router)

    # Dashboard route
    @app.get("/")
    async def dashboard(request: Request):
        """Serve the Wi-Fi Stalker dashboard"""
        return templates.TemplateResponse(
            "index.html",
            {"request": request}
        )

    return app
