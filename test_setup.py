#!/usr/bin/env python3
"""
Test script to diagnose common issues with the sports analysis app
"""

import sys
import os

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        import flask
        print("✅ Flask:", flask.__version__)
    except ImportError as e:
        print("❌ Flask import failed:", e)
        return False
    
    try:
        import cv2
        print("✅ OpenCV:", cv2.__version__)
    except ImportError as e:
        print("❌ OpenCV import failed:", e)
        return False
    
    try:
        import mediapipe as mp
        print("✅ MediaPipe:", mp.__version__)
    except ImportError as e:
        print("❌ MediaPipe import failed:", e)
        return False
    
    try:
        import numpy as np
        print("✅ NumPy:", np.__version__)
    except ImportError as e:
        print("❌ NumPy import failed:", e)
        return False
    
    try:
        import requests
        print("✅ Requests:", requests.__version__)
    except ImportError as e:
        print("❌ Requests import failed:", e)
        return False
    
    return True

def test_directories():
    """Test if required directories exist"""
    print("\n📁 Testing directories...")
    
    dirs = ['static', 'static/uploads', 'static/sessions', 'templates']
    
    for dir_path in dirs:
        if os.path.exists(dir_path):
            print(f"✅ {dir_path} exists")
        else:
            print(f"❌ {dir_path} missing")
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"✅ Created {dir_path}")
            except Exception as e:
                print(f"❌ Failed to create {dir_path}: {e}")
                return False
    
    return True

def test_templates():
    """Test if template files exist"""
    print("\n📄 Testing templates...")
    
    templates = ['templates/index.html', 'templates/analyze.html']
    
    for template in templates:
        if os.path.exists(template):
            print(f"✅ {template} exists")
        else:
            print(f"❌ {template} missing")
            return False
    
    return True

def test_environment():
    """Test environment variables"""
    print("\n🔧 Testing environment...")
    
    api_key = os.environ.get('GEMINI_API_KEY')
    if api_key:
        print("✅ GEMINI_API_KEY is set")
    else:
        print("⚠️  GEMINI_API_KEY not set (AI insights won't work)")
    
    flask_env = os.environ.get('FLASK_ENV', 'development')
    print(f"✅ FLASK_ENV: {flask_env}")
    
    return True

def test_basic_functionality():
    """Test basic app functionality"""
    print("\n🚀 Testing basic functionality...")
    
    try:
        # Import the app
        from app import app
        
        # Test if app can be created
        with app.test_client() as client:
            response = client.get('/')
            if response.status_code == 200:
                print("✅ App starts and responds to requests")
                return True
            else:
                print(f"❌ App returned status code: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ App test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Sports Analysis App - Setup Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_directories,
        test_templates,
        test_environment,
        test_basic_functionality
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your app should work correctly.")
    else:
        print("⚠️  Some tests failed. Check the issues above.")
        print("\n💡 Quick fixes:")
        print("1. Install missing dependencies: pip install -r requirements.txt")
        print("2. Create missing directories: mkdir -p static/uploads static/sessions")
        print("3. Set environment variables: export GEMINI_API_KEY=your_key")
        print("4. Check template files exist in templates/ folder")

if __name__ == "__main__":
    main()
