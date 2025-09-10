# 🔧 Troubleshooting Guide

## Common Errors and Solutions

### 1. **Import Errors**

#### Error: `ModuleNotFoundError: No module named 'cv2'`
**Solution:**
```bash
pip install opencv-python
```

#### Error: `ModuleNotFoundError: No module named 'mediapipe'`
**Solution:**
```bash
pip install mediapipe
```

#### Error: `ModuleNotFoundError: No module named 'flask'`
**Solution:**
```bash
pip install flask
```

### 2. **Template Errors**

#### Error: `TemplateNotFound: index.html`
**Solution:**
- Make sure `templates/` folder exists
- Check that `index.html` and `analyze.html` are in the `templates/` folder
- Verify file permissions

#### Error: `jinja2.exceptions.TemplateNotFound`
**Solution:**
- Check template file names are correct
- Ensure templates are in the right directory
- Check for typos in template names

### 3. **File Upload Errors**

#### Error: `FileNotFoundError: [Errno 2] No such file or directory: 'static/uploads'`
**Solution:**
```bash
mkdir -p static/uploads
mkdir -p static/sessions
```

#### Error: `PermissionError: [Errno 13] Permission denied`
**Solution:**
```bash
chmod 755 static/
chmod 755 static/uploads/
chmod 755 static/sessions/
```

### 4. **Video Processing Errors**

#### Error: `cv2.error: OpenCV(4.x.x) /tmp/opencv-xxx/modules/imgproc/src/color.cpp:xxx: error: (-215:Assertion failed) !src.empty() in function 'cvtColor'`
**Solution:**
- Check if video file is corrupted
- Verify video format is supported (MP4, AVI, MOV)
- Try with a different video file

#### Error: `MediaPipe` related errors
**Solution:**
- Update MediaPipe: `pip install --upgrade mediapipe`
- Check if video has people in it
- Ensure good lighting in video

### 5. **API Errors**

#### Error: `GEMINI_API_KEY not configured on server`
**Solution:**
- Set environment variable: `export GEMINI_API_KEY=your_key_here`
- Or create `.env` file with `GEMINI_API_KEY=your_key_here`

#### Error: `requests.exceptions.RequestException`
**Solution:**
- Check internet connection
- Verify API key is correct
- Check API quota limits

### 6. **Memory Errors**

#### Error: `MemoryError` or `Killed`
**Solution:**
- Use smaller video files
- Close other applications
- Increase system memory
- For deployment: upgrade hosting plan

### 7. **Port Errors**

#### Error: `Address already in use`
**Solution:**
```bash
# Find process using port 5000
lsof -i :5000
# Kill the process
kill -9 <PID>
# Or use different port
python app.py --port 5001
```

### 8. **Deployment Errors**

#### Error: `Build failed` on hosting platform
**Solution:**
- Check `requirements.txt` has all dependencies
- Verify Python version compatibility
- Check build logs for specific errors

#### Error: `Application failed to start`
**Solution:**
- Check environment variables are set
- Verify start command is correct
- Check application logs

## Quick Fixes

### 1. **Reset Everything**
```bash
# Remove virtual environment
rm -rf venv

# Create new virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p static/uploads static/sessions

# Run the app
python app.py
```

### 2. **Check Dependencies**
```bash
pip list | grep -E "(flask|opencv|mediapipe|numpy|requests)"
```

### 3. **Test with Simple Video**
- Use a short video (5-10 seconds)
- Ensure video shows a person doing push-ups
- Check video is not corrupted

### 4. **Debug Mode**
Add this to your `app.py` for more detailed error messages:
```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

## Platform-Specific Issues

### Windows
- Use `venv\Scripts\activate` instead of `source venv/bin/activate`
- May need Visual C++ Build Tools for OpenCV
- Use PowerShell or Command Prompt

### macOS
- May need to install Xcode command line tools
- Use `python3` instead of `python`

### Linux
- May need additional system packages
- Check file permissions
- Use `python3` instead of `python`

## Getting Help

### 1. **Check Logs**
```bash
# Run with verbose output
python app.py --debug

# Check system logs
tail -f /var/log/syslog  # Linux
```

### 2. **Test Individual Components**
```python
# Test OpenCV
import cv2
print("OpenCV version:", cv2.__version__)

# Test MediaPipe
import mediapipe as mp
print("MediaPipe version:", mp.__version__)

# Test Flask
from flask import Flask
app = Flask(__name__)
print("Flask working")
```

### 3. **Minimal Test App**
Create `test_app.py`:
```python
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World!'

if __name__ == '__main__':
    app.run(debug=True)
```

## Still Having Issues?

1. **Share the exact error message**
2. **Include your operating system**
3. **Share the command you used to run the app**
4. **Include any log output**

Common error patterns:
- `ImportError` → Missing dependencies
- `FileNotFoundError` → Missing files/directories
- `PermissionError` → File permission issues
- `MemoryError` → Insufficient memory
- `ConnectionError` → Network/API issues
