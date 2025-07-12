from flask import Flask, request, render_template, jsonify, send_file
from ultralytics import YOLO
import cv2
import numpy as np
import os
from datetime import datetime
import sqlite3
import json

app = Flask(__name__)
model = YOLO('yolov8n.pt')  # скачает при первом запуске

# Создание базы данных
def init_db():
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            file_type TEXT,
            count INTEGER
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_image', methods=['POST'])
def process_image():
    file = request.files['image']
    img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)

    results = model(img)[0]
    result_img = results.plot()

    count = sum(1 for box in results.boxes if model.names[int(box.cls[0])] == "pizza")

    cv2.imwrite('static/result.jpg', result_img)

    conn = sqlite3.connect('history.db')
    conn.execute("INSERT INTO requests (timestamp, file_type, count) VALUES (?, ?, ?)",
                 (datetime.now().isoformat(), 'image', count))
    conn.commit()
    conn.close()

    return jsonify({'count': count})


@app.route('/process_video', methods=['POST'])
def process_video():
    file = request.files['video']
    filepath = 'temp_video.mp4'
    file.save(filepath)

    cap = cv2.VideoCapture(filepath)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('static/result_video.mp4', fourcc, 20.0, (
        int(cap.get(3)), int(cap.get(4))))

    max_count = 0  # Максимум пицц на кадр

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        results = model(frame)[0]
        frame_count = sum(1 for box in results.boxes if model.names[int(box.cls[0])] == "pizza")
        if frame_count > max_count:
            max_count = frame_count
        annotated = results.plot()
        out.write(annotated)

    cap.release()
    out.release()
    os.remove(filepath)

    conn = sqlite3.connect('history.db')
    conn.execute("INSERT INTO requests (timestamp, file_type, count) VALUES (?, ?, ?)",
                 (datetime.now().isoformat(), 'video', max_count))
    conn.commit()
    conn.close()

    return jsonify({'count': max_count})


@app.route('/result_video')
def get_video():
    return send_file('static/result_video.mp4', mimetype='video/mp4')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
