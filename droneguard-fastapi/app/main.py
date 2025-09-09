from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import logging
import uvicorn
from contextlib import asynccontextmanager

from app.config import config
from app.models.detection import DroneDetector
from app.services.video_capture import VideoCaptureService
from app.services.stream_service import StreamService
from app.routers import video

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global services
video_service = None
detector = None
stream_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global video_service, detector, stream_service

    # Startup
    try:
        logger.info("Starting DroneGuard FastAPI application")

        # Initialize detector
        logger.info("Loading drone detection model")
        detector = DroneDetector(
            model_path=config.model_path,
            confidence_threshold=config.confidence_threshold,
            iou_threshold=config.iou_threshold,
        )

        # Initialize video service
        logger.info("Initializing video capture service")
        video_service = VideoCaptureService(
            source=config.video_source,
            width=config.video_width,
            height=config.video_height,
            fps=config.video_fps,
            buffer_size=config.buffer_size,
        )

        # Attach detector
        video_service.set_detector(detector)

        # Initialize stream service
        stream_service = StreamService(
            video_service=video_service,
            quality=config.streaming_quality,
        )

        # Inject services into router
        video.set_services(video_service, stream_service)

        # Start video capture
        video_service.start()

        logger.info("Application startup complete")

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application")
    if video_service:
        video_service.stop()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=config.app_title,
    description=config.app_description,
    version=config.app_version,
    lifespan=lifespan,
)

# Include video router
app.include_router(video.router)


@app.get("/")
async def root():
    """Redirect root to video stream"""
    return RedirectResponse(url="/api/video/stream")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "DroneGuard API is running"}


@app.get("/info")
async def get_app_info():
    """Get application information"""
    model_info = detector.get_model_info() if detector else {"status": "Not loaded"}

    return {
        "app": {
            "title": config.app_title,
            "version": config.app_version,
            "description": config.app_description,
        },
        "model": model_info,
        "video": {
            "source": config.video_source,
            "resolution": f"{config.video_width}x{config.video_height}",
            "fps": config.video_fps,
        },
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level="info",
    )
