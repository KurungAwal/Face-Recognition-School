import cv2
import face_recognition
import os
import numpy as np
import sqlite3
import time
import queue
import threading
from datetime import datetime, time as dt_time, timedelta
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from collections import deque
import pyttsx3
import bcrypt
import csv


# Program by Kelompok 2
TIME_CATEGORIES = {
    'on_time': {
        'arrival': (dt_time(7, 30), dt_time(8, 0)),
        'label': 'On time'
    },
    'late': {
        'arrival': (dt_time(8, 1), dt_time(10, 0)),
        'label': 'Late'
    },
    'permission': {
        'arrival': (dt_time(10, 1), dt_time(13, 59)),
        'label': 'Permission'
    },
    'departure': {
        'time': (dt_time(14, 0), dt_time(18, 0)),  # Jam pulang 14:00-18:00
        'label': 'Departure'
    }
}

# Class SD
SD_CLASSES = [
    "1", "2", "3", "4"
]

# Role options
ROLE_OPTIONS = [
    "Siswa",
    "Siswi",
    "Guru",
    "Staf"
]

SCHOOL_DURATION = timedelta(hours=18)  # Durasi jika siswa lupa absensi pulang
REGISTERED_FACES_DIR = "registered_faces"
os.makedirs(REGISTERED_FACES_DIR, exist_ok=True)
DB_FILE = "attendance.db"
FACE_RECOGNITION_THRESHOLD = 0.4
DETECTION_BUFFER_SIZE = 5
REGISTER_DELAY = 5
ADMIN_DELAY = 2
REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

# Inisialisasi Database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS registered_faces
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  role TEXT NOT NULL,
                  class TEXT,
                  encoding_path TEXT NOT NULL,
                  image_path TEXT NOT NULL,
                  registration_date TEXT NOT NULL,
                  last_update TEXT NOT NULL)''')
                  
    c.execute('''CREATE TABLE IF NOT EXISTS attendance_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  role TEXT NOT NULL,
                  class TEXT,
                  arrival_time TEXT NOT NULL,
                  arrival_status TEXT NOT NULL,
                  departure_time TEXT,
                  date TEXT NOT NULL,
                  notes TEXT,
                  auto_departure BOOLEAN DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS admin_users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL)''')
    
    # Check if admin exists, if not create default
    c.execute("SELECT COUNT(*) FROM admin_users")
    if c.fetchone()[0] == 0:
        default_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())
        c.execute("INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
                 ("admin", default_password))
    
    conn.commit()
    conn.close()

init_db()

# TTS Manager
class TTSManager:
    def __init__(self):
        self.queue = queue.Queue()
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.thread = threading.Thread(target=self._run_tts, daemon=True)
        self.thread.start()
    
    def _run_tts(self):
        while True:
            text = self.queue.get()
            if text is None:
                break
            self.engine.say(text)
            self.engine.runAndWait()
            self.queue.task_done()
    
    def speak(self, text):
        self.queue.put(text)
    
    def shutdown(self):
        self.queue.put(None)
        self.thread.join()

tts_manager = TTSManager()

# Pengenalan Muka
class FaceCache:
    def __init__(self):
        self.encodings = []
        self.names = []
        self.roles = []
        self.classes = []
        self.ids = []
        self.load_cache()
    
    def load_cache(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, name, role, class, encoding_path FROM registered_faces")
        
        self.encodings = []
        self.names = []
        self.roles = []
        self.classes = []
        self.ids = []
        
        for id, name, role, sclass, encoding_path in c.fetchall():
            try:
                encoding = np.load(encoding_path)
                self.encodings.append(encoding)
                self.names.append(name)
                self.roles.append(role)
                self.classes.append(sclass)
                self.ids.append(id)
            except Exception as e:
                print(f"Error loading encoding: {e}")
        
        conn.close()
    
    def get_matches(self, face_encoding):
        if not self.encodings:
            return []
        distances = face_recognition.face_distance(self.encodings, face_encoding)
        return [(self.ids[i], self.names[i], self.roles[i], self.classes[i]) for i, d in enumerate(distances) 
                if d < FACE_RECOGNITION_THRESHOLD]

face_cache = FaceCache()

# Sistem Absensi
class AttendanceSystem:
    def __init__(self):
        self.detection_buffer = deque(maxlen=DETECTION_BUFFER_SIZE)
        self.last_departure_check = datetime.min
    
    def get_time_category(self, check_time):
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
    
    def check_missing_departures(self):
        """Check and mark students who forgot to record departure"""
        now = datetime.now()
        
        if now.date() == self.last_departure_check.date() or now.time() < TIME_CATEGORIES['departure']['time'][1]:
            return
            
        self.last_departure_check = now
        today = now.strftime("%Y-%m-%d")
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute('''SELECT id, name, role, class, arrival_time 
                     FROM attendance_records 
                     WHERE date=? AND departure_time IS NULL''', (today,))
        
        missing_departures = c.fetchall()
        
        for record in missing_departures:
            record_id, name, role, sclass, arrival_time = record
            arrival_datetime = datetime.strptime(f"{today} {arrival_time}", "%Y-%m-%d %H:%M:%S")
            
            # Kalkulasi waktu kepulangan
            departure_time = (arrival_datetime + SCHOOL_DURATION).time().strftime("%H:%M:%S")
            
            # Memunculkan suara untuk absensi
            c.execute('''UPDATE attendance_records 
                        SET departure_time=?, auto_departure=1
                        WHERE id=?''', (departure_time, record_id))
            
            print(f"[AUTO] {name} ({role}) Kelas {sclass} marked as departed at {departure_time}")
            tts_manager.speak(f"Catatan: {name} kelas {sclass} dianggap pulang pukul {departure_time}")
        
        conn.commit()
        conn.close()
    
    def generate_monthly_report(self, year, month):
        """Generate a monthly attendance report in CSV format"""
        filename = os.path.join(REPORTS_DIR, f"attendance_report_{year}_{month:02d}.csv")
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Pencacatan bulanan
        month_start = f"{year}-{month:02d}-01"
        if month == 12:
            month_end = f"{year+1}-01-01"
        else:
            month_end = f"{year}-{month+1:02d}-01"
        
        c.execute('''SELECT name, role, class, date, arrival_time, arrival_status, 
                    departure_time, auto_departure, notes
                    FROM attendance_records
                    WHERE date >= ? AND date < ?
                    ORDER BY class, name, date''', (month_start, month_end))
        
        records = c.fetchall()
        
        if not records:
            return False, "Tidak ada catatan kehadiran untuk bulan yang dimaksud"
        
        # Format ke dalam CSV
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # Tulis dalam bahasa Indonesia
            writer.writerow(['Nama', 'Peran', 'Kelas', 'Tanggal', 'Waktu Datang', 'Status Datang',
                           'Waktu Pulang', 'Pulang Otomatis', 'Catatan'])
            
            for record in records:
                writer.writerow(record)
        
        conn.close()
        return True, filename
    
    def process_attendance(self, frame, current_time):
        if current_time.time() > TIME_CATEGORIES['departure']['time'][0]:
            self.check_missing_departures()
            
        # Konversi frame ke RGB untuk face-recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.5, fy=0.5)
        
        # Mencari lokasi wajah
        face_locations = face_recognition.face_locations(small_frame)
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)
        
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            # Skala
            top *= 2; right *= 2; bottom *= 2; left *= 2
            
            matches = face_cache.get_matches(face_encoding)
            
            if matches:
                for face_id, name, role, sclass in matches:
                    if name not in self.detection_buffer:
                        self.record_attendance(name, role, sclass, current_time)
                        self.detection_buffer.append(name)
                    
                    status = self.get_attendance_status(name, current_time.date())
                    class_display = f"Kelas {sclass}" if sclass else ""
                    label = f"{name} ({role}) {class_display} - {status}"
            else:
                label = "Tekan 'R' untuk registrasi (Admin)"
            
            # Gambar kotak pada frame asli
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            cv2.putText(frame, label, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1)
        
        return frame
    
    def record_attendance(self, name, role, sclass, record_time):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        current_date = record_time.strftime("%Y-%m-%d")
        current_time = record_time.strftime("%H:%M:%S")
        
        time_category = self.get_time_category(record_time)
        notes = ""
        
        if time_category == 'permission':
            notes = self.ask_permission_reason()
        
        c.execute("SELECT id, departure_time FROM attendance_records WHERE name=? AND date=?", (name, current_date))
        record = c.fetchone()
        
        if not record:
            # Rekord kedatangan
            status_label = TIME_CATEGORIES[time_category]['label'] if time_category in ['on_time', 'late', 'permission'] else "Outside Hours"
            c.execute('''INSERT INTO attendance_records 
                        (name, role, class, arrival_time, arrival_status, date, notes) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (name, role, sclass, current_time, status_label, current_date, notes))
            
            if time_category == 'on_time':
                tts_manager.speak(f"Selamat pagi {name}, hadir tepat waktu")
            elif time_category == 'late':
                tts_manager.speak(f"{name}, terlambat")
            elif time_category == 'permission':
                tts_manager.speak(f"{name}, izin dengan alasan {notes}")
            
            print(f"{name} ({role}) Kelas {sclass} {status_label} at {current_time}")
        
        elif time_category == 'departure' and not record[1]:
            # Rekord kepulangan jika tidak terjadi rekaman
            c.execute('''UPDATE attendance_records 
                        SET departure_time=?
                        WHERE id=?''',
                     (current_time, record[0]))
            tts_manager.speak(f"Selamat jalan {name}")
            print(f"{name} ({role}) Kelas {sclass} pulang pada {current_time}")
        
        conn.commit()
        conn.close()
    
    def ask_permission_reason(self):
        root = tk.Tk()
        root.withdraw()
        reason = simpledialog.askstring("Alasan Izin", "Masukkan alasan izin:")
        root.destroy()
        return reason if reason else "Tidak disebutkan"
    
    def get_attendance_status(self, name, date):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''SELECT arrival_status, departure_time, auto_departure 
                     FROM attendance_records 
                     WHERE name=? AND date=?''', 
                 (name, date.strftime("%Y-%m-%d")))
        result = c.fetchone()
        conn.close()
        
        if not result:
            return "Belum tercatat"
        
        status, departure, auto_departure = result
        if departure:
            if auto_departure:
                return f"{status} (Pulang otomatis: {departure})"
            return f"{status} (Pulang: {departure})"
        return status

attendance_system = AttendanceSystem()

# Sistem registrasi
class RegistrationSystem:
    def __init__(self):
        self.is_registering = False
        self.last_register_time = 0
    
    def authenticate_admin(self, show_message=True):
        root = tk.Tk()
        root.withdraw()
        username = simpledialog.askstring("Admin Login", "Admin username:")
        if not username:
            return False
            
        password = simpledialog.askstring("Admin Login", "Password:", show='*')
        if not password:
            return False
            
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, password_hash FROM admin_users WHERE username=?", (username,))
        result = c.fetchone()
        conn.close()
        
        if result and bcrypt.checkpw(password.encode('utf-8'), result[1]):
            if show_message:
                tts_manager.speak("Autentikasi berhasil")
            return result[0]  # Return admin ID
        else:
            if show_message:
                tts_manager.speak("Autentikasi gagal")
            return False
    
    def change_admin_credentials(self):
        # First authenticate the current admin
        admin_id = self.authenticate_admin(show_message=False)
        if not admin_id:
            tts_manager.speak("Autentikasi gagal")
            return False
        
        root = tk.Tk()
        root.withdraw()
        
        # Create admin management dialog
        admin_dialog = tk.Toplevel()
        admin_dialog.title("Ubah Kredensial Admin")
        admin_dialog.geometry("400x300")
        
        # Current username display
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT username FROM admin_users WHERE id=?", (admin_id,))
        current_username = c.fetchone()[0]
        conn.close()
        
        tk.Label(admin_dialog, text=f"Username saat ini: {current_username}").pack(pady=10)
        
        # New username field
        tk.Label(admin_dialog, text="Username Baru:").pack(pady=5)
        new_username_var = tk.StringVar()
        new_username_entry = tk.Entry(admin_dialog, textvariable=new_username_var)
        new_username_entry.pack(pady=5)
        
        # New password field
        tk.Label(admin_dialog, text="Password Baru:").pack(pady=5)
        new_password_var = tk.StringVar()
        new_password_entry = tk.Entry(admin_dialog, textvariable=new_password_var, show='*')
        new_password_entry.pack(pady=5)
        
        # Confirm password field
        tk.Label(admin_dialog, text="Konfirmasi Password:").pack(pady=5)
        confirm_password_var = tk.StringVar()
        confirm_password_entry = tk.Entry(admin_dialog, textvariable=confirm_password_var, show='*')
        confirm_password_entry.pack(pady=5)
        
        result = False
        
        def on_submit():
            nonlocal result
            new_username = new_username_var.get().strip()
            new_password = new_password_var.get()
            confirm_password = confirm_password_var.get()
            
            if not new_username and not new_password:
                messagebox.showerror("Error", "Harap masukkan username atau password baru")
                return
                
            if new_password and new_password != confirm_password:
                messagebox.showerror("Error", "Password tidak cocok")
                return
                
            # Update in database
            try:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                
                if new_username:
                    # Check if username already exists
                    c.execute("SELECT COUNT(*) FROM admin_users WHERE username=? AND id!=?", 
                             (new_username, admin_id))
                    if c.fetchone()[0] > 0:
                        messagebox.showerror("Error", "Username sudah digunakan")
                        return
                
                if new_password:
                    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                    c.execute("UPDATE admin_users SET password_hash=? WHERE id=?", 
                             (password_hash, admin_id))
                
                if new_username:
                    c.execute("UPDATE admin_users SET username=? WHERE id=?", 
                             (new_username, admin_id))
                
                conn.commit()
                messagebox.showinfo("Sukses", "Kredensial admin berhasil diperbarui")
                tts_manager.speak("Kredensial admin berhasil diperbarui")
                result = True
                admin_dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Gagal memperbarui kredensial: {str(e)}")
            finally:
                conn.close()
        
        def on_cancel():
            admin_dialog.destroy()
        
        tk.Button(admin_dialog, text="Submit", command=on_submit).pack(side=tk.LEFT, padx=10, pady=10)
        tk.Button(admin_dialog, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=10, pady=10)
        
        admin_dialog.wait_window()
        
        return result
    
    def register_new_face(self, frame):
        if self.is_registering or (time.time() - self.last_register_time) < REGISTER_DELAY:
            return
            
        if not self.authenticate_admin():
            return
            
        self.is_registering = True
        try:
            # Konversi wajah ke RGB untuk prosesi wajah
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.5, fy=0.5)
            face_locations = face_recognition.face_locations(small_frame)
            
            if not face_locations:
                tts_manager.speak("Tidak ada wajah terdeteksi")
                return
            
            (top, right, bottom, left) = face_locations[0]
            face_image = small_frame[top:bottom, left:right]
            face_encodings = face_recognition.face_encodings(small_frame, [face_locations[0]])
            
            if not face_encodings:
                tts_manager.speak("Gagal mengambil data wajah")
                return
            
            # Check if face already exists
            matches = face_cache.get_matches(face_encodings[0])
            if matches:
                face_id, name, role, sclass = matches[0]
                response = messagebox.askyesno("Wajah Terdaftar", 
                    f"Wajah ini sudah terdaftar sebagai {name} ({role}). Apakah Anda ingin memperbarui data?")
                if response:
                    self.update_existing_face(face_id, name, role, sclass, face_encodings[0], face_image)
                return
            
            # New registration
            registration_data = self.get_registration_data()
            if not registration_data:
                return
                
            name, role, sclass = registration_data
            
            if self.save_face_data(face_encodings[0], name, role, sclass, face_image, is_update=False):
                messagebox.showinfo("Sukses", "Registrasi berhasil!")
                tts_manager.speak(f"Registrasi berhasil untuk {name}")
            
        finally:
            self.is_registering = False
            self.last_register_time = time.time()
    
    def update_existing_face(self, face_id, current_name, current_role, current_class, face_encoding, face_image):
        try:
            registration_data = self.get_registration_data(current_name, current_role, current_class)
            if not registration_data:
                return
                
            name, role, sclass = registration_data
            
            # Update the face data
            if self.save_face_data(face_encoding, name, role, sclass, face_image, is_update=True, face_id=face_id):
                messagebox.showinfo("Sukses", "Data wajah berhasil diperbarui!")
                tts_manager.speak(f"Data {name} berhasil diperbarui")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal memperbarui data: {str(e)}")
    
    def get_registration_data(self, current_name="", current_role="", current_class=""):
        root = tk.Tk()
        root.withdraw()
        
        # Create registration dialog
        reg_dialog = tk.Toplevel()
        reg_dialog.title("Registrasi Wajah Baru")
        reg_dialog.geometry("400x300")
        
        # Name field
        tk.Label(reg_dialog, text="Nama:").pack(pady=5)
        name_var = tk.StringVar(value=current_name)
        name_entry = tk.Entry(reg_dialog, textvariable=name_var)
        name_entry.pack(pady=5)
        
        # Role selection
        tk.Label(reg_dialog, text="Peran:").pack(pady=5)
        role_var = tk.StringVar(value=current_role if current_role else ROLE_OPTIONS[0])
        role_combobox = ttk.Combobox(reg_dialog, textvariable=role_var, values=ROLE_OPTIONS, state="readonly")
        role_combobox.pack(pady=5)
        
        # Class selection (only for students)
        tk.Label(reg_dialog, text="Kelas (hanya untuk siswa):").pack(pady=5)
        class_var = tk.StringVar(value=current_class if current_class else SD_CLASSES[0])
        class_combobox = ttk.Combobox(reg_dialog, textvariable=class_var, values=SD_CLASSES, state="readonly")
        class_combobox.pack(pady=5)
        
        # Hide class selection if role is not student
        def update_class_visibility(*args):
            if role_var.get() == "Siswa":
                class_combobox.pack(pady=5)
                tk.Label(reg_dialog, text="Kelas (hanya untuk siswa):").pack(pady=5)
            else:
                class_combobox.pack_forget()
                tk.Label(reg_dialog, text="Kelas (hanya untuk siswa):").pack_forget()
        
        role_var.trace("w", update_class_visibility)
        update_class_visibility()  # Initial update
        
        result = []
        
        def on_submit():
            nonlocal result
            name = name_var.get().strip()
            role = role_var.get()
            sclass = class_var.get() if role == "Siswa" else ""
            
            if not name:
                messagebox.showerror("Error", "Nama tidak boleh kosong")
                return
                
            result = (name, role, sclass)
            reg_dialog.destroy()
        
        def on_cancel():
            reg_dialog.destroy()
        
        tk.Button(reg_dialog, text="Submit", command=on_submit).pack(side=tk.LEFT, padx=10, pady=10)
        tk.Button(reg_dialog, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=10, pady=10)
        
        reg_dialog.wait_window()
        
        return result if result else None
    
    def save_face_data(self, encoding, name, role, sclass, face_image, is_update=False, face_id=None):
        try:
            timestamp = int(time.time())
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            base_filename = f"{name}_{role}_{sclass}_{timestamp}" if sclass else f"{name}_{role}_{timestamp}"
            
            encoding_file = os.path.join(REGISTERED_FACES_DIR, f"{base_filename}.npy")
            np.save(encoding_file, encoding)
            
            image_file = os.path.join(REGISTERED_FACES_DIR, f"{base_filename}.png")
            cv2.imwrite(image_file, cv2.cvtColor(face_image, cv2.COLOR_RGB2BGR))
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            
            if is_update and face_id:
                # Update existing record
                c.execute('''UPDATE registered_faces 
                            SET name=?, role=?, class=?, encoding_path=?, image_path=?, last_update=?
                            WHERE id=?''',
                         (name, role, sclass, encoding_file, image_file, now, face_id))
            else:
                # Insert new record
                c.execute('''INSERT INTO registered_faces 
                            (name, role, class, encoding_path, image_path, registration_date, last_update) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (name, role, sclass, encoding_file, image_file, now, now))
            
            conn.commit()
            conn.close()
            
            face_cache.load_cache()
            return True
            
        except Exception as e:
            print(f"Registration error: {e}")
            messagebox.showerror("Error", f"Gagal menyimpan data: {str(e)}")
            return False
    
    def generate_monthly_report(self):
        if not self.authenticate_admin():
            return
            
        root = tk.Tk()
        root.withdraw()
        
        # Catatan tahun
        year = simpledialog.askinteger("Laporan Bulanan", "Masukkan tahun:", 
                                     minvalue=2000, maxvalue=2100)
        if not year:
            return
            
        month = simpledialog.askinteger("Laporan Bulanan", "Masukkan bulan (1-12):", 
                                       minvalue=1, maxvalue=12)
        if not month:
            return
            
        # Buat report
        success, result = attendance_system.generate_monthly_report(year, month)
        
        if success:
            messagebox.showinfo("Sukses", f"Laporan berhasil dibuat:\n{result}")
            tts_manager.speak("Laporan bulanan berhasil dibuat")
        else:
            messagebox.showerror("Error", result)
            tts_manager.speak("Gagal membuat laporan")

registration_system = RegistrationSystem()

# Aplikasi
class AttendanceApp:
    def __init__(self):
        self.video_capture = cv2.VideoCapture(0)
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
        self.video_capture.set(cv2.CAP_PROP_FPS, 30)
        self.last_admin_action = 0
    
    def run(self):
        tts_manager.speak("Sistem presensi siap digunakan")
        
        while True:
            ret, frame = self.video_capture.read()
            if not ret:
                break

            current_time = datetime.now()
            
            processed_frame = attendance_system.process_attendance(frame.copy(), current_time)
            
            # Menampilkan frame akhir
            cv2.imshow('Sistem Presensi Sekolah', processed_frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('r'):
                if (time.time() - self.last_admin_action) > ADMIN_DELAY:
                    registration_system.register_new_face(frame.copy())
                    self.last_admin_action = time.time()
            elif key == ord('p'):  # Pencet p untuk generate laporan bulanan
                if (time.time() - self.last_admin_action) > ADMIN_DELAY:
                    registration_system.generate_monthly_report()
                    self.last_admin_action = time.time()
            elif key == ord('a'):  # Pencet a untuk mengubah kredensial admin
                if (time.time() - self.last_admin_action) > ADMIN_DELAY:
                    registration_system.change_admin_credentials()
                    self.last_admin_action = time.time()
            elif key == ord('q'):
                break

        self.video_capture.release()
        cv2.destroyAllWindows()
        tts_manager.shutdown()

if __name__ == "__main__":
    app = AttendanceApp()
    app.run()
