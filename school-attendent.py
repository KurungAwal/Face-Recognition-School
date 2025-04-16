import cv2
import face_recognition
import os
import numpy as np
import json
import tkinter as tk
from tkinter import simpledialog
from collections import deque
from datetime import datetime
import pyttsx3

# Inisialisasi folder penyimpanan wajah
REGISTERED_FACES_DIR = "c:\\Users\\Lenovo\\Documents\\Foto Siswa"
os.makedirs(REGISTERED_FACES_DIR, exist_ok=True)

# Threshold dan buffer
FACE_RECOGNITION_THRESHOLD = 0.4
DETECTION_BUFFER_SIZE = 5
detection_buffer = deque(maxlen=DETECTION_BUFFER_SIZE)

# Inisialisasi text-to-speech
engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

# Fungsi menyimpan wajah baru
def register_face(face_encoding, name, role):
    encoding_file = os.path.join(REGISTERED_FACES_DIR, f"{name}_{role}.jpg")
    json_file = os.path.join(REGISTERED_FACES_DIR, f"{name}_{role}.json")

    np.save(encoding_file, face_encoding)
    with open(json_file, 'w') as f:
        json.dump({
            "name": name,
            "role": role,
            "file_path": encoding_file
        }, f, indent=4)

    print(f"Wajah {name} sebagai {role} telah terdaftar.")
    speak(f"Registrasi berhasil, {name} sebagai {role}")

# Pengecekan wajah dikenal
def check_known_face(face_encoding):
    results = []
    for file in os.listdir(REGISTERED_FACES_DIR):
        if file.endswith(".npy"):
            known_encoding = np.load(os.path.join(REGISTERED_FACES_DIR, file))
            distance = face_recognition.face_distance([known_encoding], face_encoding)[0]
            if distance < FACE_RECOGNITION_THRESHOLD:
                name_role = os.path.splitext(file)[0]
                name, role = name_role.split('_')
                results.append((name, role))
    return results

# Meningkatkan pencahayaan
def improve_lighting(image):
    yuv = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
    yuv[:, :, 0] = cv2.equalizeHist(yuv[:, :, 0])
    return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)

# Proses video
def start_video_stream():
    video_capture = cv2.VideoCapture(0)
    arrival_times = {}
    departure_times = {}

    while True:
        ret, frame = video_capture.read()
        if not ret:
            break

        frame = improve_lighting(frame)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        detected_names = set()

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            names_roles = check_known_face(face_encoding)

            if names_roles:
                for name, role in names_roles:
                    detected_names.add(name)
                    now = datetime.now()
                    current_hour = now.hour

                    # Catat kedatangan
                    if name not in arrival_times:
                        arrival_times[name] = now.strftime("%Y-%m-%d %H:%M:%S")
                        print(f"{name} ({role}) datang pada {arrival_times[name]}")
                        speak(f"Selamat datang, {name}")

                    # Catat pulang jika muncul lagi setelah jam 15:00
                    elif current_hour >= 15 and name not in departure_times:
                        departure_times[name] = now.strftime("%Y-%m-%d %H:%M:%S")
                        print(f"{name} ({role}) pulang pada {departure_times[name]}")
                        speak(f"Selamat jalan, {name}")

                    label = f"{name} ({role})"
            else:
                label = "Press 'S' to register"

            # Kotak dan label wajah
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            cv2.putText(frame, label, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 1)

        # Label jika wajah tidak dikenali
        if not detected_names:
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                cv2.putText(frame, "Press 'S' to register", (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 1.0,
                            (255, 255, 255), 1)

        cv2.imshow('Video', frame)
        key = cv2.waitKey(1) & 0xFF

        # Registrasi wajah
        if key == ord('s'):
            root = tk.Tk()
            root.withdraw()
            name = simpledialog.askstring("Registrasi", "Masukkan nama:")
            role = simpledialog.askstring("Registrasi", "Sebagai apa:")
            if name and role:
                for face_encoding in face_encodings:
                    register_face(face_encoding, name, role)
            root.destroy()

        # Keluar dari aplikasi
        elif key == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()

# Jalankan video
start_video_stream()
