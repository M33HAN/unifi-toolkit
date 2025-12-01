"""
UniFi Toolkit - Unified FastAPI Application

This is the main application that mounts all available tools as sub-applications.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from shared.database import get_database
from shared.config import get_settings
from shared.websocket_manager import get_ws_manager
from tools.wifi_stalker.main import create_app as create_stalker_app
from tools.wifi_stalker.scheduler import start_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Template directory for main dashboard
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager - handles startup and shutdown events
    """
    # Startup
    logger.info("Starting UniFi Toolkit...")
    settings = get_settings()
    logger.info(f"Log level: {settings.log_level}")

    # Initialize database
    logger.info("Initializing database...")
    db = get_database()
    await db.init_db()
    logger.info("Database initialized")

    # Start Wi-Fi Stalker scheduler
    logger.info("Starting Wi-Fi Stalker scheduler...")
    await start_scheduler()
    logger.info("Wi-Fi Stalker scheduler started")

    logger.info("UniFi Toolkit started successfully")

    yield

    # Shutdown
    logger.info("Shutting down UniFi Toolkit...")

    # Stop Wi-Fi Stalker scheduler
    logger.info("Stopping Wi-Fi Stalker scheduler...")
    await stop_scheduler()
    logger.info("Wi-Fi Stalker scheduler stopped")

    logger.info("UniFi Toolkit shut down complete")


# Create main application
app = FastAPI(
    title="UniFi Toolkit",
    description="Comprehensive toolkit for UniFi network management and monitoring",
    version="1.1.0",
    lifespan=lifespan
)

# Mount Wi-Fi Stalker sub-application
stalker_app = create_stalker_app()
app.mount("/stalker", stalker_app)

# Mount main app static files (for dashboard)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Main dashboard - shows available tools
    """
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    """
    return {
        "status": "healthy",
        "version": "1.1.0",
        "tools": {
            "wifi_stalker": "0.6.0"
        }
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket):
    """
    WebSocket endpoint for real-time updates
    """
    ws_manager = get_ws_manager()
    await ws_manager.connect(websocket)
    try:
        while True:
            # Wait for messages from client (e.g., ping)
            data = await websocket.receive_text()

            if data == "ping":
                # Respond with pong
                await websocket.send_json({"type": "pong"})
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()

    # Set log level based on settings
    log_level = settings.log_level.lower()

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level=log_level
    )
