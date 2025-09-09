import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DroneDetector:
    def __init__(self, model_path: str, confidence_threshold: float = 0.5, iou_threshold: float = 0.4):
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the YOLO model"""
        try:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Model file not found: {self.model_path}")
            
            logger.info(f"Loading YOLO model from {self.model_path}")
            self.model = YOLO(str(self.model_path))
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def detect(self, frame: np.ndarray) -> Tuple[np.ndarray, List[dict]]:
        """
        Detect drones in the given frame
        
        Args:
            frame: Input image as numpy array
            
        Returns:
            Tuple of (annotated_frame, detections_list)
        """
        if self.model is None:
            logger.error("Model not loaded")
            return frame, []
        
        try:
            # Run inference
            results = self.model(frame, conf=self.confidence_threshold, iou=self.iou_threshold, verbose=False)
            
            # Parse results
            detections = []
            annotated_frame = frame.copy()
            
            if results and len(results) > 0:
                result = results[0]
                
                if result.boxes is not None and len(result.boxes) > 0:
                    for box in result.boxes:
                        # Extract box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                        confidence = float(box.conf[0].cpu().numpy())
                        
                        # Store detection info
                        detection = {
                            'bbox': [x1, y1, x2, y2],
                            'confidence': confidence,
                            'class': 'drone'
                        }
                        detections.append(detection)
                        
                        # Draw bounding box
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        
                        # Draw label
                        label = f"Drone {confidence:.2f}"
                        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                        cv2.rectangle(annotated_frame, (x1, y1 - label_size[1] - 10), 
                                    (x1 + label_size[0], y1), (0, 255, 0), -1)
                        cv2.putText(annotated_frame, label, (x1, y1 - 5), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            
            return annotated_frame, detections
            
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return frame, []
    
    def get_model_info(self) -> dict:
        """Get model information"""
        if self.model is None:
            return {"status": "Model not loaded"}
        
        return {
            "model_path": str(self.model_path),
            "confidence_threshold": self.confidence_threshold,
            "iou_threshold": self.iou_threshold,
            "model_loaded": True
        }