#!/usr/bin/env python3
"""
DroneGuard FastAPI Application Runner
"""

import uvicorn
from app.config import config

if __name__ == "__main__":
    print("🚁 Starting DroneGuard FastAPI Server...")
    print(f"📹 Video Source: {config.video_source}")
    print(f"🤖 Model Path: {config.model_path}")
    print(f"🌐 Server: http://{config.host}:{config.port}")
    print("-" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level="info",
        access_log=True
    )