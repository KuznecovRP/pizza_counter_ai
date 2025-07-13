from flask import Flask, request, render_template, jsonify, send_file
from ultralytics import YOLO
import cv2
import numpy as np
import os
from datetime import datetime
import sqlite3
from reportlab.pdfgen import canvas
from openpyxl import Workbook

app = Flask(__name__)
model = YOLO('yolov8n.pt')  # скачает при первом запуске

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

def save_to_db(file_type, count):
    conn = sqlite3.connect('history.db')
    conn.execute("INSERT INTO requests (timestamp, file_type, count) VALUES (?, ?, ?)",
                 (datetime.now().isoformat(), file_type, count))
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
    save_to_db('image', count)
    return jsonify({'count': count})

@app.route('/process_video', methods=['POST'])
def process_video():
    file = request.files['video']
    filepath = 'temp_video.mp4'
    file.save(filepath)
    cap = cv2.VideoCapture(filepath)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('static/result_video.mp4', fourcc, 20.0, (int(cap.get(3)), int(cap.get(4))))
    max_count = 0
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
    save_to_db('video', max_count)
    return jsonify({'count': max_count})

@app.route('/result_video')
def get_video():
    return send_file('static/result_video.mp4', mimetype='video/mp4')

@app.route('/report/pdf')
def generate_pdf():
    filename = 'report.pdf'
    conn = sqlite3.connect('history.db')
    cursor = conn.cursor()
    c = canvas.Canvas(filename)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, "Processing History Report")
    c.setFont("Helvetica", 12)
    c.drawString(50, 780, f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    cursor.execute('SELECT timestamp, file_type, count FROM requests ORDER BY id DESC')
    y = 750
    for timestamp, file_type, count in cursor.fetchall():
        line = f"Timestamp: {timestamp}  |  Type: {file_type}  |  Pizza count: {count}"
        c.drawString(50, y, line)
        y -= 20
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = 800
    c.save()
    conn.close()
    return send_file(filename, as_attachment=True)

@app.route('/report/excel')
def generate_excel():
    filename = 'report.xlsx'
    conn = sqlite3.connect('history.db')
    cursor = conn.cursor()
    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "Timestamp", "File Type", "Pizza Count"])
    for row in cursor.execute('SELECT * FROM requests'):
        ws.append(row)
    wb.save(filename)
    conn.close()
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
