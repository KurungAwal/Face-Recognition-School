import cv2
import face_recognition
import os
import numpy as np
import sqlite3
import time
import queue
import threading
from datetime import datetime, time as dt_time
import tkinter as tk
from tkinter import simpledialog, messagebox
from collections import deque
import pyttsx3

# ===== Configuration =====
TIME_CATEGORIES = {
    'on_time': {
        'arrival': (dt_time(7, 30), dt_time(8, 0)),
        'label': 'Hadir Tepat Waktu'
    },
    'late': {
        'arrival': (dt_time(8, 1), dt_time(10, 0)),
        'label': 'Terlambat'
    },
    'permission': {
        'arrival': (dt_time(10, 1), dt_time(13, 59)),
        'label': 'Izin'
    },
    'departure': {
        'time': (dt_time(14, 0), dt_time(18, 0)),
        'label': 'Pulang'
    }
}

REGISTERED_FACES_DIR = "registered_faces"
os.makedirs(REGISTERED_FACES_DIR, exist_ok=True)
DB_FILE = "attendance.db"
FACE_RECOGNITION_THRESHOLD = 0.4
DETECTION_BUFFER_SIZE = 5

# ===== Thread-safe TTS Manager =====
class TTSManager:
    def __init__(self):
        self.queue = queue.Queue()
        self.engine = pyttsx3.init()
        self.thread = threading.Thread(target=self._run_tts, daemon=True)
        self.thread.start()
    
    def _run_tts(self):
        while True:
            text = self.queue.get()
            if text is None:
                break
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except RuntimeError:
                self.engine = pyttsx3.init()
                self.engine.say(text)
                self.engine.runAndWait()
            self.queue.task_done()
    
    def speak(self, text):
        self.queue.put(text)
    
    def shutdown(self):
        self.queue.put(None)
        self.thread.join()

tts_manager = TTSManager()

# ===== Database Initialization =====
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS registered_faces
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  role TEXT NOT NULL,
                  encoding_path TEXT NOT NULL,
                  image_path TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  role TEXT NOT NULL,
                  arrival_time TEXT NOT NULL,
                  arrival_status TEXT NOT NULL,
                  departure_time TEXT,
                  date TEXT NOT NULL,
                  notes TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ===== Face Registration with PNG =====
def register_face(face_encoding, name, role, face_image):
    try:
        timestamp = int(time.time())
        base_filename = f"{name}_{role}_{timestamp}"
        
        # Save face encoding
        encoding_file = os.path.join(REGISTERED_FACES_DIR, f"{base_filename}.npy")
        np.save(encoding_file, face_encoding)
        
        # Save face image as PNG
        image_file = os.path.join(REGISTERED_FACES_DIR, f"{base_filename}.png")
        cv2.imwrite(image_file, cv2.cvtColor(face_image, cv2.COLOR_RGB2BGR))
        
        # Save to database
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO registered_faces (name, role, encoding_path, image_path) VALUES (?, ?, ?, ?)",
                 (name, role, encoding_file, image_file))
        conn.commit()
        conn.close()
        
        print(f"Registered {name} as {role}")
        tts_manager.speak(f"Registrasi berhasil, {name} sebagai {role}")
        return True
    except Exception as e:
        print(f"Registration error: {e}")
        return False

# ===== Face Recognition =====
def check_known_face(face_encoding):
    results = []
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name, role, encoding_path FROM registered_faces")
    records = c.fetchall()
    conn.close()
    
    for name, role, encoding_path in records:
        try:
            known_encoding = np.load(encoding_path)
            distance = face_recognition.face_distance([known_encoding], face_encoding)[0]
            if distance < FACE_RECOGNITION_THRESHOLD:
                results.append((name, role))
        except Exception as e:
            print(f"Error loading encoding: {e}")
    
    return results

# ===== Time Classification =====
def get_time_category(check_time):
    check_time = check_time.time()
    
    if TIME_CATEGORIES['on_time']['arrival'][0] <= check_time <= TIME_CATEGORIES['on_time']['arrival'][1]:
        return 'on_time'
    elif TIME_CATEGORIES['late']['arrival'][0] <= check_time <= TIME_CATEGORIES['late']['arrival'][1]:
        return 'late'
    elif TIME_CATEGORIES['permission']['arrival'][0] <= check_time <= TIME_CATEGORIES['permission']['arrival'][1]:
        return 'permission'
    elif TIME_CATEGORIES['departure']['time'][0] <= check_time <= TIME_CATEGORIES['departure']['time'][1]:
        return 'departure'
    return 'outside_hours'

# ===== Attendance Recording =====
def record_attendance(name, role, record_time):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    current_date = record_time.strftime("%Y-%m-%d")
    current_time = record_time.strftime("%H:%M:%S")
    
    time_category = get_time_category(record_time)
    notes = ""
    
    if time_category == 'permission':
        notes = ask_permission_reason()
    
    c.execute("SELECT id FROM attendance_records WHERE name=? AND date=?", (name, current_date))
    record = c.fetchone()
    
    if not record:
        status_label = TIME_CATEGORIES[time_category]['label'] if time_category in ['on_time', 'late', 'permission'] else "Outside Hours"
        c.execute('''INSERT INTO attendance_records 
                    (name, role, arrival_time, arrival_status, date, notes) 
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (name, role, current_time, status_label, current_date, notes))
        
        if time_category == 'on_time':
            tts_manager.speak(f"Selamat pagi {name}, hadir tepat waktu")
        elif time_category == 'late':
            tts_manager.speak(f"{name}, terlambat")
        elif time_category == 'permission':
            tts_manager.speak(f"{name}, izin dengan alasan {notes}")
        
        print(f"{name} ({role}) {status_label} at {current_time}")
    
    elif time_category == 'departure':
        c.execute('''UPDATE attendance_records 
                    SET departure_time=? 
                    WHERE name=? AND date=?''',
                 (current_time, name, current_date))
        tts_manager.speak(f"Selamat jalan {name}")
        print(f"{name} ({role}) pulang pada {current_time}")
    
    conn.commit()
    conn.close()

# ===== Helper Functions =====
def ask_permission_reason():
    root = tk.Tk()
    root.withdraw()
    reason = simpledialog.askstring("Alasan Izin", "Masukkan alasan izin:")
    root.destroy()
    return reason if reason else "Tidak disebutkan"

def get_attendance_status(name, date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT arrival_status FROM attendance_records WHERE name=? AND date=?", 
             (name, date.strftime("%Y-%m-%d")))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "Belum tercatat"

# ===== Main Video Processing =====
def start_video_stream():
    video_capture = cv2.VideoCapture(0)
    video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    video_capture.set(cv2.CAP_PROP_FPS, 30)
    
    detection_buffer = deque(maxlen=DETECTION_BUFFER_SIZE)
    last_register_time = 0
    
    while True:
        ret, frame = video_capture.read()
        if not ret:
            break

        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        current_time = datetime.now()
        
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            top *= 2; right *= 2; bottom *= 2; left *= 2
            
            names_roles = check_known_face(face_encoding)
            
            if names_roles:
                for name, role in names_roles:
                    if name not in detection_buffer:
                        record_attendance(name, role, current_time)
                        detection_buffer.append(name)
                    
                    status = get_attendance_status(name, current_time.date())
                    label = f"{name} ({role}) - {status}"
            else:
                label = "Tekan 'R' untuk registrasi"
            
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            cv2.putText(frame, label, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1)

        cv2.imshow('Sistem Presensi Sekolah', frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('r') and (time.time() - last_register_time) > 3:
            if face_encodings:
                (top, right, bottom, left) = face_locations[0]
                face_image = rgb_small_frame[top:bottom, left:right]
                
                root = tk.Tk()
                root.withdraw()
                name = simpledialog.askstring("Registrasi", "Masukkan nama:")
                if name:
                    role = simpledialog.askstring("Registrasi", "Sebagai apa (Guru/Siswa/Staf):")
                    if role and register_face(face_encodings[0], name, role, face_image):
                        messagebox.showinfo("Sukses", "Registrasi berhasil!")
                root.destroy()
                last_register_time = time.time()
        elif key == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()
    tts_manager.shutdown()

if __name__ == "__main__":
    start_video_stream()