import cv2
import threading
import time
import logging
from typing import Optional, Union
import numpy as np
from queue import Queue
from app.models.detection import DroneDetector

logger = logging.getLogger(__name__)

class VideoCaptureService:
    def __init__(self, source: Union[int, str], width: int = 640, height: int = 480, 
                 fps: int = 30, buffer_size: int = 1):
        self.source = source
        self.width = width
        self.height = height
        self.fps = fps
        self.buffer_size = buffer_size
        
        self.cap = None
        self.detector = None
        self.frame_queue = Queue(maxsize=buffer_size)
        self.latest_frame = None
        self.is_running = False
        self.capture_thread = None
        self.frame_lock = threading.Lock()
        
        self._initialize_capture()
    
    def _initialize_capture(self):
        """Initialize video capture"""
        try:
            logger.info(f"Initializing video capture from source: {self.source}")
            self.cap = cv2.VideoCapture(self.source)
            
            if not self.cap.isOpened():
                raise RuntimeError(f"Failed to open video source: {self.source}")
            
            # Set capture properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Get actual properties
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Video capture initialized: {actual_width}x{actual_height} @ {actual_fps} FPS")
            
        except Exception as e:
            logger.error(f"Failed to initialize video capture: {e}")
            raise
    
    def set_detector(self, detector: DroneDetector):
        """Set the drone detector"""
        self.detector = detector
        logger.info("Drone detector set")
    
    def start(self):
        """Start video capture in a separate thread"""
        if self.is_running:
            logger.warning("Video capture already running")
            return
        
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        logger.info("Video capture started")
    
    def stop(self):
        """Stop video capture"""
        self.is_running = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        if self.cap:
            self.cap.release()
        
        logger.info("Video capture stopped")
    
    def _capture_loop(self):
        """Main capture loop running in separate thread"""
        frame_time = 1.0 / self.fps
        
        while self.is_running:
            start_time = time.time()
            
            try:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("Failed to read frame")
                    if isinstance(self.source, str):  # Video file ended
                        break
                    continue
                
                # Process frame with detector if available
                if self.detector:
                    annotated_frame, detections = self.detector.detect(frame)
                else:
                    annotated_frame = frame
                
                # Update latest frame thread-safely
                with self.frame_lock:
                    self.latest_frame = annotated_frame.copy()
                
                # Maintain target FPS
                elapsed = time.time() - start_time
                sleep_time = frame_time - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                break
        
        self.is_running = False
        logger.info("Capture loop ended")
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the latest processed frame"""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def is_active(self) -> bool:
        """Check if capture is active"""
        return self.is_running
    
    def get_frame_shape(self) -> tuple:
        """Get the frame shape"""
        if self.latest_frame is not None:
            return self.latest_frame.shape
        return (self.height, self.width, 3)