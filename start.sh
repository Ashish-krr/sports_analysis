#!/bin/bash

# Sports Analysis App Startup Script

echo "Starting Sports Analysis App..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Copying from env.example..."
    cp env.example .env
    echo "Please edit .env file and add your GEMINI_API_KEY before running again."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check if GEMINI_API_KEY is set
if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "your_gemini_api_key_here" ]; then
    echo "Error: GEMINI_API_KEY not set in .env file"
    echo "Please edit .env file and add your actual Gemini API key"
    exit 1
fi

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "Docker detected. Starting with Docker Compose..."
    docker-compose up -d
    echo "App started! Access it at http://localhost:5000"
else
    echo "Docker not found. Starting with Python directly..."
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt
    
    # Start the app
    echo "Starting Flask app..."
    gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app
fi

