#!/usr/bin/env python3
"""
Optional MediaPipe installer for deployment environments
"""
import subprocess
import sys

def install_mediapipe():
    """Try to install MediaPipe, continue if it fails"""
    try:
        print("Attempting to install MediaPipe...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mediapipe>=0.10.0"])
        print("MediaPipe installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"MediaPipe installation failed: {e}")
        print("Continuing without MediaPipe - basic video analysis will be used")
        return False
    except Exception as e:
        print(f"Unexpected error during MediaPipe installation: {e}")
        return False

if __name__ == "__main__":
    install_mediapipe()