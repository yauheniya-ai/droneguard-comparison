# YOLOv8 Drone Detection with Python & FastAPI

A production-ready Python implementation of a YOLOv8-based drone detection system that processes live video streams in real-time.

## Project Structure

```bash
droneguard-fastapi/
├── models/
│   └── best.pt                # Trained YOLOv8 model
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI application entry point
│   ├── config.py              # Configuration settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── detection.py       # YOLO detection service
│   ├── services/
│   │   ├── __init__.py
│   │   ├── video_capture.py   # Video capture and processing
│   │   └── stream_service.py  # Video streaming service
│   └── routers/
│       ├── __init__.py
│       └── video.py           # Video streaming endpoints
├── requirements.txt           # Python dependencies
├── config.yaml                # Application configuration
└── run.py                     # Application runner
````


