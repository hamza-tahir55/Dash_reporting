#!/bin/bash
# Startup script for Railway deployment

# Use Railway's PORT or default to 8000
PORT=${PORT:-8000}

echo "Starting server on port $PORT"
uvicorn api:app --host 0.0.0.0 --port $PORT
