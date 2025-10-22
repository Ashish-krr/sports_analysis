from flask import Flask, render_template, request, redirect, url_for, Response, jsonify, send_file, session, flash
import os
import uuid
import time
import hashlib
import json
from datetime import datetime
# import threading  # Removed: not used
import cv2
import numpy as np

# Try to import mediapipe, with fallback
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
    print("MediaPipe loaded successfully")
except ImportError:
    print("Warning: MediaPipe not available. Using basic video analysis mode.")
    MEDIAPIPE_AVAILABLE = False
    mp = None
import csv
import requests

# Flask app setup
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static', 'uploads')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# User data storage (in production, use a proper database)
USERS_FILE = 'users.json'
QUESTIONS_FILE = 'questions.json'

def load_users():
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_questions():
    """Load questions from JSON file"""
    if os.path.exists(QUESTIONS_FILE):
        try:
            with open(QUESTIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_questions(questions):
    """Save questions to JSON file"""
    with open(QUESTIONS_FILE, 'w') as f:
        json.dump(questions, f, indent=2)

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """Verify password against hash"""
    return hash_password(password) == hashed

# Initialize MediaPipe Pose
if MEDIAPIPE_AVAILABLE:
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
else:
    mp_pose = None
    mp_drawing = None

# In-memory session store
sessions = {}
session_history = []  # lightweight metadata records for history page


GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def calculate_angle(a, b, c):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle


def aggregate_session_summary(records: list[dict]) -> dict:
    summary = {
        'total_frames': 0,
        'total_reps': 0,
        'duration_ms': 0.0,
        'avg_elbow_angle': 0.0,
        'avg_hip_angle': 0.0,
        'min_elbow_angle': None,
        'max_elbow_angle': None,
        'min_hip_angle': None,
        'max_hip_angle': None,
        'hip_warning_frames': 0,
        'go_lower_frames': 0,
        'good_form_frames': 0,
        'last_feedback': ''
    }
    if not records:
        return summary

    total_elbow = 0.0
    total_hip = 0.0
    min_e = float('inf')
    max_e = float('-inf')
    min_h = float('inf')
    max_h = float('-inf')

    for r in records:
        e = float(r.get('elbow_angle', 0.0))
        h = float(r.get('hip_angle', 0.0))
        total_elbow += e
        total_hip += h
        min_e = min(min_e, e)
        max_e = max(max_e, e)
        min_h = min(min_h, h)
        max_h = max(max_h, h)
        fb = r.get('feedback', '')
        if fb == 'Keep your hips straight!':
            summary['hip_warning_frames'] += 1
        elif fb == 'Go lower!':
            summary['go_lower_frames'] += 1
        elif fb == 'Good form!':
            summary['good_form_frames'] += 1
        summary['last_feedback'] = fb

    summary['total_frames'] = len(records)
    summary['total_reps'] = int(records[-1].get('count', 0))
    first_ts = float(records[0].get('timestamp_ms', 0.0))
    last_ts = float(records[-1].get('timestamp_ms', 0.0))
    if last_ts >= first_ts:
        summary['duration_ms'] = last_ts - first_ts
    summary['avg_elbow_angle'] = total_elbow / len(records)
    summary['avg_hip_angle'] = total_hip / len(records)
    summary['min_elbow_angle'] = min_e if min_e != float('inf') else 0.0
    summary['max_elbow_angle'] = max_e if max_e != float('-inf') else 0.0
    summary['min_hip_angle'] = min_h if min_h != float('inf') else 0.0
    summary['max_hip_angle'] = max_h if max_h != float('-inf') else 0.0
    return summary


def analyze_video_simple(session_id: str, cap):
    """Simple video analysis without MediaPipe (fallback)"""
    session = sessions.get(session_id)
    if not session:
        return

    count = 0
    records = []
    frame_count = 0
    exercise = session.get('exercise', 'pushup')
    
    # Basic timing for different exercises
    count_interval = {
        'pushup': 45,
        'pullup': 60, 
        'situp': 40,
        'jumping_jack': 30,
        'plank': 30  # For plank, count seconds
    }.get(exercise, 45)

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            current_timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
            
            # Exercise-specific counting
            if exercise == 'plank':
                # Count seconds for plank
                count = frame_count // 30  # Assuming 30 FPS
                feedback = "Hold steady position"
            else:
                # Count reps for other exercises
                if frame_count % count_interval == 0:
                    count += 1
                feedback = f"Basic {exercise.replace('_', ' ')} analysis"

            record = {
                "frame": frame_count,
                "timestamp_ms": float(current_timestamp_ms) if current_timestamp_ms is not None else 0.0,
                "elbow_angle": 90.0,
                "hip_angle": 180.0,
                "stage": "up",
                "count": count,
                "feedback": feedback,
            }
            records.append(record)

            # Update live metrics
            session['current_metrics'] = {
                'count': count,
                'feedback': feedback,
                'elbow_angle': 90,
                'hip_angle': 180,
            }

            # Draw overlay
            label = "Secs" if exercise == 'plank' else "Reps"
            cv2.putText(frame, f"{label}: {count}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(frame, "Basic Analysis Mode", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 165, 0), 2, cv2.LINE_AA)
            cv2.putText(frame, exercise.replace('_', ' ').title(), (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)

            ret2, buffer = cv2.imencode('.jpg', frame)
            if not ret2:
                continue
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            time.sleep(0.01)
    finally:
        cap.release()
        # Save CSV
        session['records'] = records
        try:
            if records:
                csv_dir = os.path.join('static', 'sessions')
                os.makedirs(csv_dir, exist_ok=True)
                csv_path = os.path.join(csv_dir, f'{session_id}.csv')
                fieldnames = [
                    "frame", "timestamp_ms", "elbow_angle", "hip_angle", "stage", "count", "feedback"
                ]
                with open(csv_path, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(records)
                session['csv_path'] = csv_path
                # Append to history
                try:
                    session_history.append({
                        'session_id': session_id,
                        'exercise': session.get('exercise', 'pushup'),
                        'total_reps': int(records[-1].get('count', 0)),
                        'duration_s': round((records[-1].get('timestamp_ms', 0.0) - records[0].get('timestamp_ms', 0.0))/1000.0, 2) if len(records) > 1 else 0,
                        'created_at': time.time(),
                        'user_id': session.get('user_id'),
                    })
                    
                    # Add to user's session history
                    if session.get('user_id'):
                        users = load_users()
                        user_email = None
                        for email, user_data in users.items():
                            if user_data.get('id') == session.get('user_id'):
                                user_email = email
                                break
                        
                        if user_email:
                            session_summary = {
                                'session_id': session_id,
                                'exercise': session.get('exercise', 'pushup'),
                                'total_reps': int(records[-1].get('count', 0)),
                                'duration_s': round((records[-1].get('timestamp_ms', 0.0) - records[0].get('timestamp_ms', 0.0))/1000.0, 2) if len(records) > 1 else 0,
                                'created_at': datetime.now().isoformat(),
                            }
                            users[user_email]['sessions'].append(session_summary)
                            save_users(users)
                except Exception:
                    pass
        except Exception:
            session['csv_path'] = None
        session['is_done'] = True


def analyze_video_generator(session_id: str):
    session = sessions.get(session_id)
    if not session:
        return

    video_path = session['video_path']
    cap = cv2.VideoCapture(video_path)
    
    if not MEDIAPIPE_AVAILABLE:
        # Fallback: simple video processing without pose detection
        yield from analyze_video_simple(session_id, cap)
        return
    
    pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    count = 0
    stage = "up"
    feedback = ""
    records = []
    exercise = session.get('exercise', 'pushup')
    start_ms = None

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = pose.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            try:
                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark

                    shoulder = [landmarks[11].x, landmarks[11].y]
                    elbow = [landmarks[13].x, landmarks[13].y]
                    wrist = [landmarks[15].x, landmarks[15].y]
                    hip = [landmarks[23].x, landmarks[23].y]
                    ankle = [landmarks[27].x, landmarks[27].y]
                    shoulder_r = [landmarks[12].x, landmarks[12].y]
                    wrist_r = [landmarks[16].x, landmarks[16].y]
                    ankle_r = [landmarks[28].x, landmarks[28].y]
                    # nose = [landmarks[0].x, landmarks[0].y]  # Removed: not used

                    elbow_angle = calculate_angle(shoulder, elbow, wrist)
                    hip_angle = calculate_angle(shoulder, hip, ankle)

                    current_frame_index = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                    current_timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                    if start_ms is None and current_timestamp_ms is not None:
                        start_ms = current_timestamp_ms

                    if exercise == 'pushup':
                        if elbow_angle <= 90 and hip_angle > 160:
                            stage = "down"
                        if elbow_angle >= 160 and hip_angle > 160 and stage == "down":
                            count += 1
                            stage = "up"

                        if hip_angle < 160:
                            feedback = "Keep your hips straight!"
                        elif elbow_angle > 100 and stage == "down":
                            feedback = "Go lower!"
                        else:
                            feedback = "Good form!"

                    elif exercise == 'pullup':
                        # Simple elbow flexion based heuristic for pull-ups
                        # Down (bottom) ~ elbow extended; Up (top) ~ elbow flexed
                        if elbow_angle >= 150:
                            stage = "down"
                        if elbow_angle <= 70 and stage == "down":
                            count += 1
                            stage = "up"
                        # Form: encourage full range and avoid swinging (approx via hip angle stability)
                        if elbow_angle > 160:
                            feedback = "Fully hang before pulling."
                        elif elbow_angle < 60:
                            feedback = "Strong pull! Control the descent."
                        else:
                            feedback = "Keep pulling vertically."

                    elif exercise == 'situp':
                        # Use hip angle closing to detect the up position
                        if hip_angle >= 150:
                            stage = "down"
                        if hip_angle <= 100 and stage == "down":
                            count += 1
                            stage = "up"
                        if hip_angle > 170:
                            feedback = "Start from flat back."
                        elif hip_angle < 90:
                            feedback = "Good sit-up height."
                        else:
                            feedback = "Curl up smoothly; avoid neck strain."

                    elif exercise == 'jumping_jack':
                        # Consider "open" when feet apart and hands high; "closed" when feet together and hands low
                        feet_apart_x = abs(ankle[0] - ankle_r[0])
                        hands_high = (wrist[1] < shoulder[1] - 0.1) and (wrist_r[1] < shoulder_r[1] - 0.1)
                        open_pos = feet_apart_x > 0.35 and hands_high
                        if open_pos:
                            stage = "open"
                        if not open_pos and stage == "open":
                            count += 1
                            stage = "closed"
                        feedback = "Arms overhead, feet wide" if open_pos else "Return to start position"

                    elif exercise == 'plank':
                        # Count seconds of good plank (hip straight). Use time diff.
                        good_form = hip_angle > 165
                        if good_form and current_timestamp_ms is not None and start_ms is not None:
                            count = int(max(0, (current_timestamp_ms - start_ms) / 1000.0))
                        feedback = "Hips level" if good_form else "Lift hips to neutral"
                    else:
                        # Default to pushup logic
                        if elbow_angle <= 90 and hip_angle > 160:
                            stage = "down"
                        if elbow_angle >= 160 and hip_angle > 160 and stage == "down":
                            count += 1
                            stage = "up"
                        feedback = "Good form!"
                    record = {
                        "frame": current_frame_index,
                        "timestamp_ms": float(current_timestamp_ms) if current_timestamp_ms is not None else 0.0,
                        "elbow_angle": float(elbow_angle),
                        "hip_angle": float(hip_angle),
                        "stage": stage,
                        "count": int(count),
                        "feedback": feedback,
                    }
                    records.append(record)

                    # Update live metrics
                    session['current_metrics'] = {
                        'count': int(count),
                        'feedback': feedback,
                        'elbow_angle': int(elbow_angle),
                        'hip_angle': int(hip_angle),
                    }

                    # Draw overlays
                    label = "Secs" if exercise == 'plank' else "Reps"
                    cv2.putText(image, f"{label}: {count}", (20, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                    cv2.putText(image, f"Feedback: {feedback}", (20, 80),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2, cv2.LINE_AA)
                    cv2.putText(image, f"Elbow: {int(elbow_angle)}", (20, 120),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA)
                    cv2.putText(image, f"Hip: {int(hip_angle)}", (20, 150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA)

                    mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            except Exception:
                pass

            ret2, buffer = cv2.imencode('.jpg', image)
            if not ret2:
                continue
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            time.sleep(0.01)
    finally:
        cap.release()
        if 'pose' in locals() and pose is not None:
            pose.close()
        # Save CSV
        session['records'] = records
        try:
            if records:
                csv_dir = os.path.join('static', 'sessions')
                os.makedirs(csv_dir, exist_ok=True)
                csv_path = os.path.join(csv_dir, f'{session_id}.csv')
                fieldnames = [
                    "frame", "timestamp_ms", "elbow_angle", "hip_angle", "stage", "count", "feedback"
                ]
                with open(csv_path, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(records)
                session['csv_path'] = csv_path
                # Append to history
                try:
                    session_history.append({
                        'session_id': session_id,
                        'exercise': session.get('exercise', 'pushup'),
                        'total_reps': int(records[-1].get('count', 0)),
                        'duration_s': round((records[-1].get('timestamp_ms', 0.0) - records[0].get('timestamp_ms', 0.0))/1000.0, 2) if len(records) > 1 else 0,
                        'created_at': time.time(),
                        'user_id': session.get('user_id'),
                    })
                    
                    # Add to user's session history
                    if session.get('user_id'):
                        users = load_users()
                        user_email = None
                        for email, user_data in users.items():
                            if user_data.get('id') == session.get('user_id'):
                                user_email = email
                                break
                        
                        if user_email:
                            session_summary = {
                                'session_id': session_id,
                                'exercise': session.get('exercise', 'pushup'),
                                'total_reps': int(records[-1].get('count', 0)),
                                'duration_s': round((records[-1].get('timestamp_ms', 0.0) - records[0].get('timestamp_ms', 0.0))/1000.0, 2) if len(records) > 1 else 0,
                                'created_at': datetime.now().isoformat(),
                            }
                            users[user_email]['sessions'].append(session_summary)
                            save_users(users)
                except Exception:
                    pass
        except Exception:
            session['csv_path'] = None
        session['is_done'] = True


@app.route('/', methods=['GET'])
def index():
    """Landing page with user type selection"""
    return render_template('landing.html')

@app.route('/app', methods=['GET'])
def app_main():
    """Main application (requires authentication)"""
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('index.html')

@app.route('/main', methods=['GET'])
def main_app():
    """Legacy route for the main app functionality"""
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user_type = session.get('user_type', 'athlete')
    return redirect(url_for('dashboard', user_type=user_type))

@app.route('/signup', methods=['POST'])
def signup():
    """Handle user registration"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        user_type = data.get('userType', '').strip()
        
        if not all([name, email, password, user_type]):
            return jsonify({'success': False, 'message': 'All fields are required'})
        
        if user_type not in ['professional', 'athlete', 'coach']:
            return jsonify({'success': False, 'message': 'Invalid user type'})
        
        if len(password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters'})
        
        users = load_users()
        
        if email in users:
            return jsonify({'success': False, 'message': 'Email already registered'})
        
        # Create new user
        user_id = str(uuid.uuid4())
        users[email] = {
            'id': user_id,
            'name': name,
            'email': email,
            'password': hash_password(password),
            'user_type': user_type,
            'created_at': datetime.now().isoformat(),
            'sessions': [],
            'profile_picture': None
        }
        
        save_users(users)
        
        # Set session
        session['user_id'] = user_id
        session['user_email'] = email
        session['user_type'] = user_type
        session['user_name'] = name
        
        return jsonify({'success': True, 'message': 'Account created successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Registration failed. Please try again.'})

@app.route('/signin', methods=['POST'])
def signin():
    """Handle user login"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password are required'})
        
        users = load_users()
        
        if email not in users:
            return jsonify({'success': False, 'message': 'Invalid email or password'})
        
        user = users[email]
        
        if not verify_password(password, user['password']):
            return jsonify({'success': False, 'message': 'Invalid email or password'})
        
        # Set session
        session['user_id'] = user['id']
        session['user_email'] = email
        session['user_type'] = user['user_type']
        session['user_name'] = user['name']
        
        return jsonify({
            'success': True, 
            'message': 'Signed in successfully',
            'userType': user['user_type']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Sign in failed. Please try again.'})

@app.route('/signout', methods=['POST'])
def signout():
    """Handle user logout"""
    session.clear()
    return jsonify({'success': True, 'message': 'Signed out successfully'})

@app.route('/dashboard/<user_type>')
def dashboard(user_type):
    """User-specific dashboard"""
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    if session.get('user_type') != user_type:
        return redirect(url_for('dashboard', user_type=session.get('user_type', 'athlete')))
    
    users = load_users()
    user_email = session.get('user_email')
    
    if user_email not in users:
        session.clear()
        return redirect(url_for('index'))
    
    user = users[user_email]
    user_sessions = user.get('sessions', [])
    
    return render_template('dashboard.html', 
                         user=user, 
                         user_type=user_type,
                         sessions=user_sessions[-10:])  # Show last 10 sessions


@app.route('/profile')
def profile():
    """User profile page"""
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    users = load_users()
    user_email = session.get('user_email')
    
    if user_email not in users:
        session.clear()
        return redirect(url_for('index'))
    
    user = users[user_email]
    user_sessions = user.get('sessions', [])
    
    # Calculate stats
    total_reps = sum(session.get('total_reps', 0) for session in user_sessions)
    total_duration = round(sum(session.get('duration_s', 0) for session in user_sessions) / 60, 1)
    best_session = max([session.get('total_reps', 0) for session in user_sessions], default=0)
    
    return render_template('profile.html', 
                         user=user, 
                         user_type=session.get('user_type', 'athlete'),
                         sessions=user_sessions,
                         total_reps=total_reps,
                         total_duration=total_duration,
                         best_session=best_session)


@app.route('/profile/picture', methods=['POST'])
def upload_profile_picture():
    """Handle profile picture upload"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    if 'profile_picture' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'})
    
    file = request.files['profile_picture']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    # Check file type
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        return jsonify({'success': False, 'message': 'Invalid file type. Please upload an image.'})
    
    # Create profile pictures directory
    profile_dir = os.path.join('static', 'profiles')
    os.makedirs(profile_dir, exist_ok=True)
    
    # Generate unique filename
    user_id = session.get('user_id')
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{user_id}_profile{file_extension}"
    file_path = os.path.join(profile_dir, filename)
    
    try:
        # Save file
        file.save(file_path)
        
        # Update user data
        users = load_users()
        user_email = session.get('user_email')
        
        if user_email in users:
            users[user_email]['profile_picture'] = f'/static/profiles/{filename}'
            save_users(users)
            
            # Update session
            session['profile_picture'] = f'/static/profiles/{filename}'
            
            return jsonify({'success': True, 'message': 'Profile picture updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'User not found'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Failed to save file'})


@app.route('/profile/edit', methods=['POST'])
def edit_profile():
    """Handle profile editing"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        
        if not all([name, email]):
            return jsonify({'success': False, 'message': 'Name and email are required'})
        
        users = load_users()
        user_email = session.get('user_email')
        
        if user_email not in users:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Check if email is being changed and if it's already taken
        if email != user_email and email in users:
            return jsonify({'success': False, 'message': 'Email already in use'})
        
        # Update user data
        user = users[user_email]
        user['name'] = name
        
        # If email is changing, update the key
        if email != user_email:
            users[email] = user
            del users[user_email]
            session['user_email'] = email
        
        user['email'] = email
        save_users(users)
        
        # Update session
        session['user_name'] = name
        
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Failed to update profile'})


@app.route('/analyze', methods=['POST'])
def analyze():
    # Check if user is authenticated
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    if 'video' not in request.files:
        return redirect(url_for('dashboard', user_type=session.get('user_type', 'athlete')))
    file = request.files['video']
    if file.filename == '':
        return redirect(url_for('dashboard', user_type=session.get('user_type', 'athlete')))

    session_id = str(uuid.uuid4())
    filename = f"{session_id}_{file.filename}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)

    exercise = (request.form.get('exercise') or 'pushup').strip().lower()
    if exercise not in { 'pushup', 'pullup', 'situp', 'jumping_jack', 'plank' }:
        exercise = 'pushup'

    def create_session(video_path, exercise, user_id):
        return {
            'video_path': video_path,
            'records': [],
            'current_metrics': {'count': 0, 'feedback': '', 'elbow_angle': 0, 'hip_angle': 0},
            'is_done': False,
            'csv_path': None,
            'exercise': exercise,
            'user_id': user_id,
            'created_at': datetime.now().isoformat()
        }

    sessions[session_id] = create_session(save_path, exercise, session['user_id'])

    return redirect(url_for('view_analysis', session_id=session_id))


@app.route('/view/<session_id>', methods=['GET'])
def view_analysis(session_id):
    if session_id not in sessions:
        return redirect(url_for('dashboard', user_type=session.get('user_type', 'athlete')))
    
    # Check if user owns this session
    session_data = sessions[session_id]
    if session_data.get('user_id') != session.get('user_id'):
        return redirect(url_for('dashboard', user_type=session.get('user_type', 'athlete')))
    
    ex = session_data.get('exercise', 'pushup')
    return render_template('analyze.html', session_id=session_id, exercise=ex)


@app.route('/history', methods=['GET'])
def history():
    # Return latest 50 sessions, newest first
    items = sorted(session_history, key=lambda x: x.get('created_at', 0), reverse=True)[:50]
    return render_template('history.html', sessions=items)


@app.route('/stream/<session_id>')
def stream(session_id):
    if session_id not in sessions:
        return Response(status=404)

    return Response(analyze_video_generator(session_id), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/metrics/<session_id>')
def metrics(session_id):
    session = sessions.get(session_id)
    if not session:
        return jsonify({}), 404
    return jsonify({
        'count': session['current_metrics'].get('count', 0),
        'feedback': session['current_metrics'].get('feedback', ''),
        'elbow_angle': session['current_metrics'].get('elbow_angle', 0),
        'hip_angle': session['current_metrics'].get('hip_angle', 0),
        'is_done': session.get('is_done', False)
    })


@app.route('/download/<session_id>')
def download_csv(session_id):
    session = sessions.get(session_id)
    if not session:
        return Response(status=404)
    csv_path = session.get('csv_path')
    if not csv_path or not os.path.exists(csv_path):
        return Response("CSV not ready yet", status=404)
    return send_file(csv_path, as_attachment=True, download_name=f'{session_id}.csv')


@app.route('/qa')
def qa_page():
    """Q&A page for athletes to ask questions"""
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    questions = load_questions()
    # Sort by newest first
    questions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return render_template('qa.html', 
                         questions=questions,
                         user_type=session.get('user_type', 'athlete'))

@app.route('/qa/ask', methods=['POST'])
def ask_question():
    """Handle new question submission"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    try:
        data = request.get_json()
        question_text = data.get('question', '').strip()
        category = data.get('category', 'general').strip()
        
        if not question_text:
            return jsonify({'success': False, 'message': 'Question cannot be empty'})
        
        questions = load_questions()
        
        new_question = {
            'id': str(uuid.uuid4()),
            'question': question_text,
            'category': category,
            'author_id': session['user_id'],
            'author_name': session['user_name'],
            'author_type': session['user_type'],
            'created_at': datetime.now().isoformat(),
            'answers': [],
            'status': 'open'
        }
        
        questions.append(new_question)
        save_questions(questions)
        
        return jsonify({'success': True, 'message': 'Question posted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Failed to post question'})

@app.route('/qa/answer', methods=['POST'])
def answer_question():
    """Handle answer submission"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    # Only coaches and professionals can answer
    if session.get('user_type') not in ['coach', 'professional']:
        return jsonify({'success': False, 'message': 'Only coaches and professionals can answer questions'})
    
    try:
        data = request.get_json()
        question_id = data.get('question_id', '').strip()
        answer_text = data.get('answer', '').strip()
        
        if not question_id or not answer_text:
            return jsonify({'success': False, 'message': 'Question ID and answer are required'})
        
        questions = load_questions()
        
        # Find the question
        question = None
        for q in questions:
            if q['id'] == question_id:
                question = q
                break
        
        if not question:
            return jsonify({'success': False, 'message': 'Question not found'})
        
        new_answer = {
            'id': str(uuid.uuid4()),
            'answer': answer_text,
            'author_id': session['user_id'],
            'author_name': session['user_name'],
            'author_type': session['user_type'],
            'created_at': datetime.now().isoformat()
        }
        
        question['answers'].append(new_answer)
        question['status'] = 'answered'
        
        save_questions(questions)
        
        return jsonify({'success': True, 'message': 'Answer posted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Failed to post answer'})

@app.route('/insights/<session_id>', methods=['POST'])
def insights(session_id):
    session = sessions.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        return jsonify({'error': 'GEMINI_API_KEY not configured on server'}), 400

    user_prompt = ''
    try:
        data = request.get_json(silent=True) or {}
        user_prompt = data.get('prompt', '').strip()
    except Exception:
        user_prompt = ''

    records = session.get('records', [])
    summary = aggregate_session_summary(records)

    ex = session.get('exercise', 'pushup')
    ex_name = {
        'pushup': 'push-up',
        'pullup': 'pull-up',
        'situp': 'sit-up',
        'jumping_jack': 'jumping jack',
        'plank': 'plank',
    }.get(ex, ex)
    base_instruction = (
        f"You are a certified strength coach. Analyze this {ex_name} session and provide: "
        "1) brief form assessment, 2) top improvement priorities, 3) best exercises and progressions "
        "tailored to the observed data (with sets/reps and cues), 4) safety notes."
    )

    context_block = (
        f"Total reps: {summary['total_reps']}\n"
        f"Duration (s): {round(summary['duration_ms']/1000.0, 2)}\n"
        f"Avg elbow angle: {round(summary['avg_elbow_angle'],1)}\n"
        f"Avg hip angle: {round(summary['avg_hip_angle'],1)}\n"
        f"Min/Max elbow: {round(summary['min_elbow_angle'],1)}/{round(summary['max_elbow_angle'],1)}\n"
        f"Min/Max hip: {round(summary['min_hip_angle'],1)}/{round(summary['max_hip_angle'],1)}\n"
        f"Hip warning frames: {summary['hip_warning_frames']}\n"
        f"Go lower frames: {summary['go_lower_frames']}\n"
        f"Good form frames: {summary['good_form_frames']}\n"
        f"Last feedback: {summary['last_feedback']}\n"
    )

    final_prompt = (
        f"{base_instruction}\n\nSESSION SUMMARY:\n{context_block}\n"
        f"USER REQUEST (optional): {user_prompt if user_prompt else 'Provide your best, concise plan.'}"
    )

    try:
        resp = requests.post(
            GEMINI_URL,
            params={'key': GEMINI_API_KEY},
            json={
                'contents': [
                    {
                        'role': 'user',
                        'parts': [{'text': final_prompt}]
                    }
                ]
            },
            timeout=30
        )
        if resp.status_code != 200:
            return jsonify({'error': 'Gemini API error', 'status': resp.status_code, 'detail': resp.text[:500]}), 502
        payload = resp.json()
        text = ''
        try:
            candidates = payload.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                if parts:
                    text = parts[0].get('text', '')
        except Exception:
            text = ''
        if not text:
            text = 'No insights returned.'
        return jsonify({'insights': text})
    except requests.RequestException as e:
        return jsonify({'error': 'Request failed', 'detail': str(e)}), 502


if __name__ == '__main__':
    # For local development; on deployment, use a WSGI server.
    app.run(host='0.0.0.0', port=5000, debug=True)
