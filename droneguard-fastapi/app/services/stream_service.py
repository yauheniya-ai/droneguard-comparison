import cv2
import asyncio
import logging
from typing import Generator
from app.services.video_capture import VideoCaptureService

logger = logging.getLogger(__name__)

class StreamService:
    def __init__(self, video_service: VideoCaptureService, quality: int = 90):
        self.video_service = video_service
        self.quality = quality
        self.encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    
    def generate_frames(self) -> Generator[bytes, None, None]:
        """Generate MJPEG frames for streaming"""
        while True:
            try:
                frame = self.video_service.get_latest_frame()
                
                if frame is None:
                    # Send a black frame if no frame available
                    frame = self._create_placeholder_frame()
                
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame, self.encode_params)
                if not ret:
                    logger.error("Failed to encode frame")
                    continue
                
                # Convert to bytes
                frame_bytes = buffer.tobytes()
                
                # Yield frame in MJPEG format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                # Small delay to prevent overwhelming
                asyncio.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                logger.error(f"Error generating frame: {e}")
                break
    
    def _create_placeholder_frame(self):
        """Create a placeholder frame when video is not available"""
        height, width = 480, 640
        frame = cv2.zeros((height, width, 3), dtype=cv2.uint8)
        
        # Add text
        text = "No Video Feed"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        color = (255, 255, 255)
        thickness = 2
        
        # Get text size to center it
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = (width - text_size[0]) // 2
        text_y = (height + text_size[1]) // 2
        
        cv2.putText(frame, text, (text_x, text_y), font, font_scale, color, thickness)
        
        return frame
    
    async def generate_frames_async(self) -> Generator[bytes, None, None]:
        """Async version of frame generation"""
        while True:
            try:
                frame = self.video_service.get_latest_frame()
                
                if frame is None:
                    frame = self._create_placeholder_frame()
                
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame, self.encode_params)
                if not ret:
                    logger.error("Failed to encode frame")
                    await asyncio.sleep(0.1)
                    continue
                
                frame_bytes = buffer.tobytes()
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                await asyncio.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                logger.error(f"Error in async frame generation: {e}")
                await asyncio.sleep(0.1)