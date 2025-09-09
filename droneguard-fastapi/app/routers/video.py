from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video", tags=["video"])

# Global variables to store services (will be injected by main app)
video_service = None
stream_service = None

def set_services(video_svc, stream_svc):
    """Set the service instances"""
    global video_service, stream_service
    video_service = video_svc
    stream_service = stream_svc

@router.get("/stream")
async def video_stream():
    """Stream video with drone detection"""
    try:
        if not stream_service:
            raise HTTPException(status_code=500, detail="Stream service not available")
        
        return StreamingResponse(
            stream_service.generate_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )
    except Exception as e:
        logger.error(f"Error starting video stream: {e}")
        raise HTTPException(status_code=500, detail="Failed to start video stream")

@router.get("/status")
async def get_video_status():
    """Get video capture status"""
    try:
        if not video_service:
            return {"status": "Service not available"}
        
        return {
            "is_active": video_service.is_active(),
            "frame_shape": video_service.get_frame_shape(),
            "source": video_service.source
        }
    except Exception as e:
        logger.error(f"Error getting video status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get video status")

@router.post("/start")
async def start_video():
    """Start video capture"""
    try:
        if not video_service:
            raise HTTPException(status_code=500, detail="Video service not available")
        
        if not video_service.is_active():
            video_service.start()
            return {"message": "Video capture started"}
        else:
            return {"message": "Video capture already running"}
    except Exception as e:
        logger.error(f"Error starting video capture: {e}")
        raise HTTPException(status_code=500, detail="Failed to start video capture")

@router.post("/stop")
async def stop_video():
    """Stop video capture"""
    try:
        if not video_service:
            raise HTTPException(status_code=500, detail="Video service not available")
        
        if video_service.is_active():
            video_service.stop()
            return {"message": "Video capture stopped"}
        else:
            return {"message": "Video capture not running"}
    except Exception as e:
        logger.error(f"Error stopping video capture: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop video capture")