#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p static/uploads static/sessions static/profiles

echo "Build completed successfully"