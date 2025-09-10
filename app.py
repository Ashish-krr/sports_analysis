from flask import Flask, render_template, request, redirect, url_for, Response, jsonify, send_file
import os
import uuid
import time
import threading
import cv2
import mediapipe as mp
import numpy as np
import csv
import requests

# Flask app setup
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# In-memory session store
sessions = {}


GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
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


def analyze_video_generator(session_id: str):
    session = sessions.get(session_id)
    if not session:
        return

    video_path = session['video_path']
    cap = cv2.VideoCapture(video_path)
    pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    count = 0
    stage = "up"
    feedback = ""
    records = []

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

                    elbow_angle = calculate_angle(shoulder, elbow, wrist)
                    hip_angle = calculate_angle(shoulder, hip, ankle)

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

                    current_frame_index = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                    current_timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
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
                    cv2.putText(image, f"Reps: {count}", (20, 40),
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
        except Exception:
            session['csv_path'] = None
        session['is_done'] = True


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    if 'video' not in request.files:
        return redirect(url_for('index'))
    file = request.files['video']
    if file.filename == '':
        return redirect(url_for('index'))

    session_id = str(uuid.uuid4())
    filename = f"{session_id}_{file.filename}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)

    sessions[session_id] = {
        'video_path': save_path,
        'records': [],
        'current_metrics': {'count': 0, 'feedback': '', 'elbow_angle': 0, 'hip_angle': 0},
        'is_done': False,
        'csv_path': None,
    }

    return redirect(url_for('view_analysis', session_id=session_id))


@app.route('/view/<session_id>', methods=['GET'])
def view_analysis(session_id):
    if session_id not in sessions:
        return redirect(url_for('index'))
    return render_template('analyze.html', session_id=session_id)


@app.route('/stream/<session_id>')
def stream(session_id):
    if session_id not in sessions:
        return Response(status=404)

    def run():
        return analyze_video_generator(session_id)

    return Response(run(), mimetype='multipart/x-mixed-replace; boundary=frame')


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


@app.route('/insights/<session_id>', methods=['POST'])
def insights(session_id):
    session = sessions.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

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

    base_instruction = (
        "You are a certified strength coach. Analyze the push-up session metrics and provide: "
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
