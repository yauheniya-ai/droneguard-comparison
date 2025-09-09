#!/bin/bash

# Start FastAPI App
echo "⚡ Starting FastAPI App on http://localhost:8000 ..."
cd droneguard-fastapi
source .venv/bin/activate   # adjust if your env path is different
python run.py &
FASTAPI_PID=$!
deactivate
cd ..

# Start Spring Boot App
echo "🌿 Starting Spring Boot App on http://localhost:8080 ..."
cd droneguard-springboot
mvn clean spring-boot:run &
SPRINGBOOT_PID=$!
cd ..

# Start Performance Monitor
echo "📈 Starting Performance Dashboard on http://localhost:3000 ..."
cd performance-monitor
source .venv/bin/activate   # adjust if needed
python dashboard.py &
DASHBOARD_PID=$!
deactivate
cd ..

# Wait for all background processes
echo "✅ All services started."
echo "Press Ctrl+C to stop everything."

trap "kill $FASTAPI_PID $SPRINGBOOT_PID $DASHBOARD_PID" SIGINT
wait
