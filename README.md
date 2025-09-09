# 🛡️ DroneGuard Performance Comparison System

A comprehensive system to compare FastAPI vs Spring Boot drone detection applications side-by-side with real-time performance monitoring.

<div align="center">
  <img src="drone_detection_two_apps.gif" alt="Drone Detection in Two Apps" />
  <br>
  <em>Drone Live Detection: FastAPI vs. Spring Boot</em>
</div>

## 🏗️ System Architecture

```
 ┌───────────────────┐    ┌───────────────────────┐
 │ FastAPI DroneGuard│    │Spring Boot DroneGuard │
 │   (Port 8000)     │    │    (Port 8080)        │
 └─────────┬─────────┘    └─────────┬─────────────┘
           │                        │
           │                        │
 ┌─────────▼────────────────────────▼─────────────┐
 │           Performance Monitor                  │
 │           (Port 3000)                          │
 └────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
drone-comparison/
├── droneguard-fastapi/       # FastAPI app
├── droneguard-springboot/    # Spring Boot app
├── performance-monitor/      # Monitors system resources
├── .gitignore                # Ignore selected files
├── LICENSE                   # MIT
└── README.md                 # This document
```

## 🚀 Quick Setup

### Install Dependencies

```bash
cd droneguard-fastapi
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
```

In a new terminal:

```bash
cd performance-monitor
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Application Configurations

**FastAPI (config.yaml):**
```yaml
video:
  source: 1  # Webcam
```

**Spring Boot (application.yml):**
```yaml
video:
  source: 0  # Webcam
```

### Start All Services

**Manual Start (Recommended for testing)**

```bash
# Terminal 1: FastAPI App (droneguard-fastapi) -> activate the env
python run.py
# video stream @ http://localhost:8000

# Terminal 2: Spring Boot App 
cd droneguard-springboot && mvn clean spring-boot:run
# video stream @ http://localhost:8080

# Terminal 3: Performance Monitor (performance-monitor) -> activate the env
python dashboard.py
# dashboard @ http://localhost:3000

```


### Access the Comparison

Open your browser and navigate to: **http://localhost:3000**

## 📊 What You'll See

### Real-time Comparison Dashboard Features:

1. **Side-by-side Video Streams** 
   - Left: FastAPI detection feed
   - Right: Spring Boot detection feed
   - Health status (green/red dots)

2. **Performance Metrics Cards**
   - CPU Usage (%)
   - Memory Usage (MB)
   - Response Time (ms)
   - Thread Count

3. **Interactive Charts**
   - CPU usage over time
   - Memory consumption trends
   - Response time comparison
   - System resource utilization

## 🔧 Performance Metrics Explained

### Key Metrics for Drone Applications:

| Metric | Importance | Observed Values / Ideal |
|--------|------------|------------------------|
| **Response Time** | Critical for real-time detection | FastAPI: 3.6 ms (mean), Spring Boot: 4.1 ms (mean); ideal < 50 ms |
| **Memory Usage** | Resource efficiency per process | FastAPI: 714 MB, Spring Boot: 416 MB; ideal < 500 MB |
| **CPU Usage** | Processing efficiency per process | FastAPI: 19.3 %, Spring Boot: 6.4 %; ideal < 80 % |
| **Threads** | Number of active threads per app | FastAPI: 31, Spring Boot: 109 |
| **System Resources** | Overall system usage | CPU: ~60 %, Memory: ~63 % |

### Observations:

- **Detection Speed:** FastAPI consistently delivers faster response times.  
- **Resource Usage:** Spring Boot consumes slightly less CPU and memory per process but runs more threads.  
- **System Load:** Both apps maintain moderate system resource usage, indicating stability.  

## License

This project is licensed under the **MIT License**.  

## Contributions

Contributions, suggestions, and improvements are welcome! Feel free to submit issues or pull requests to help enhance the project.
