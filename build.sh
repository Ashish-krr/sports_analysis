#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit  # Exit on error

# Install Python dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p static/uploads
mkdir -p static/sessions
mkdir -p static/profiles

echo "Build completed successfully - MediaPipe disabled for compatibility"