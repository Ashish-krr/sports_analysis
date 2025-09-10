#!/bin/bash

echo "🚀 Deploying Sports Analysis App..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit for deployment"
fi

# Check if remote exists
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "Please add your GitHub repository as origin:"
    echo "git remote add origin https://github.com/yourusername/sports-analyze.git"
    exit 1
fi

# Push to GitHub
echo "Pushing to GitHub..."
git add .
git commit -m "Deploy to free hosting platform"
git push origin main

echo "✅ Code pushed to GitHub!"
echo ""
echo "Now choose your deployment platform:"
echo "1. Render (Recommended): https://render.com"
echo "2. Railway: https://railway.app"
echo "3. Fly.io: https://fly.io"
echo ""
echo "Don't forget to set your GEMINI_API_KEY environment variable!"

