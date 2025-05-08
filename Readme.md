# Dokumentasi Instalasi Project School Attendance

**Apa Saja yang Perlu di Install?**
1. cv2
2. face_recognition
3. os
4. numpy
5. json
6. tkinter
7. Pyttsx3
8. dlib 


# 1. Cara Menginstall CV2
OpenCV atau cv2 adalah library wajib untuk capture kamera dan proses gambar.

1. Buka terminal
    
    Install dengan: 
    
    pip install opencv-python

    atau pip3 install opencv-python untuk Mac

2. Verifikasi instalasi dengan menjalankan script python berikut:

    import cv2
    
    print(cv2.__version__)  # Cetak versi OpenCV

# 2. Cara Menginstall Face Recognition
face_recognition adalah library Python berbasis dlib untuk deteksi dan pengenalan wajah.

1. Buka CMD dan jalankan: 

    pip install cmake  # Wajib untuk kompilasi dlib
    
    pip install dlib   # Library machine learning untuk face_recognition
    
    pip install face_recognition 

2. Verifikasi instalasi

    import face_recognition
    
    print(face_recognition.__version__)  # Harusnya mencetak versi

# 3. Cara Menginstall OS 
Sistem Operasi adalah perangkat lunak inti yang mengelola seluruh operasi komputer. 
Fungsi utamanya adalah:

1. Manajemen Hardware: Mengontrol CPU, RAM, storage, dan perangkat input/output

2. Antarmuka Pengguna: Menyediakan GUI (Graphical User Interface) seperti Windows/macOS atau CLI (Command Line Interface) seperti Terminal Linux

3. Manajemen File: Mengatur penyimpanan data (create, read, update, delete file).

4. Manajemen Aplikasi: Menjalankan dan menghentikan program

Cara install:
1. Modul os sudah termasuk dalam instalasi standar Python

2. Gunakan, import os

Cara penggunaan modul os:
1. Mengecek Direktori Saat Ini

    import os

    print(os.getcwd())  # Output: /path/ke/direktori/anda

2. List File dalam Direktori

    files = os.listdir()  # List semua file di direktori saat ini

    print(files)

3. Membuat/Menghapus Direktori

    os.mkdir("folder_baru")  # Membuat folder baru

    os.rmdir("folder_baru")  # Menghapus folder (jika kosong)

4. Menjalankan Perintah Sistem

    Windows:
    os.system("dir")  # List file (seperti di CMD)

    macOS/Linux:
    os.system("ls")   # List file (seperti di Terminal)

5. Mengganti Nama File

    os.rename("file_lama.txt", "file_baru.txt")

# 4. Cara Menginstal NumPy
NumPy (Numerical Python) adalah library Python untuk komputasi saintifik dan analisis data. 

1. Buka command prompt (windows) atau terminal (macOS/linux)

2. Menjalankan perintah: 

    pip install numpy 
    
    atau pip3 install numpy untuk Mac

# 5. Cara Menginstal JSON
JSON (JavaScript Object Notation) adalah format pertukaran data yang ringan dan mudah dibaca oleh manusia maupun mesin.

Fungsi utamanya adalah: 
1. Penyimpanan Data

2. Komunikasi API: Mengirim/menerima data dari server

3. Pertukaran Data Antar Bahasa
Kompatibel dengan Python, JavaScript, Java, dll.

Cara install:
1. Untuk Python: Modul json sudah termasuk bawaan Python

2. import json  # Langsung bisa digunakan!

# 6. Cara Menginstall Tkinter
Tkinter adalah library standar Python untuk membuat GUI (Graphical User Interface) berbasis desktop. Ini adalah toolkit bawaan Python yang memungkinkan pembuatan aplikasi dengan jendela, tombol, input teks, dan komponen visual lainnya.

1. Tkinter biasanya sudah terpasang bersama Python

2. Cek dengan perintah berikut di terminal: 

    python -m tkinter

3. Jika muncul jendela kecil bertuliskan 

    "This is Tkinter version...", 
    
    artinya Tkinter sudah terinstal

# 7. Cara Menginstall Pyttsx3
Library ini memungkinkan program Python berbicara (text-to-speech) dengan suara sintetis. 

Fungsi utamanya adalah:
1. Konversi Teks ke Suara

Cara install:
1.  Instal via pip: 

    Buka terminal/CMD dan jalankan: 
    
    pip install pyttsx3

2. Jika di windows error: 

    Beberapa kasus membutuhkan pyaudio: 
    
    pip install pyaudio

3. MacOS: 
    
    Pastikan sudah instal Homebrew: 
    
    brew install espeak 

4. Verifikasi Instalasi:

    import pyttsx3

    engine = pyttsx3.init()

    engine.say("Halo, pyttsx3 berhasil diinstal")

    engine.runAndWait()

Trouble dan Solusinya
1. No module named 'pyttsx3'

    Solusi: Pastikan pip/Python versi terbaru 

    (python -m pip install --upgrade pip)

2. Suara tidak keluar

    Solusi: Cek volume sistem atau Install driver TTS: 
    
    Control Panel > Speech Recognition > Text to Speech

# Cara Menginstall Dlib
Fungsi utama dlib antara lain: 
1. DLib dapat mengidentifikasi 68 titik kunci (landmark) pada wajah manusia, seperti Bentuk wajah (garis rahang, dagu), Alis (titik kiri dan kanan), Mata (kelopak, pupil), Hidung (ujung, pangkal hidung), Mulut (bibir atas dan bawah, sudut mulut)

Cara install untuk window:
1. Instal CMake (diperlukan untuk kompilasi): 

pip install cmake

2. Install Dlib: pip install dlib

3. Jika mengalami masalah, Anda bisa mencoba menginstal binary yang sudah dikompilasi: 

pip install dlib-19.19.0-cp38-cp38-win_amd64.whl

Cara install untuk MacOS:
1. Pastikan Anda memiliki Xcode dan command line tools terinstal:

xcode-select --install

2. Instal dependensi dengan Homebrew:

brew install cmake
brew install boost
brew install boost-python3

3. Instal DLib melalui pip:

pip install dlib

4. Verifikasi instalasi:

import dlib
print(dlib.__version__)


# Dokumentasi Cara Kerja
1. Import Library: Mengimpor semua modul yang dibutuhkan seperti yang sudah di cantumkan di atas.

2. Membuat folder penyimpanan data wajah yang terdaftar dan hasil deteksi

4. Inisialisasi text-to-speech: Menyiapkan sistem suara untuk menyapa pengguna

5. Mengaktifkan kamera dan memproses untuk mendeteksi wajah secara langsung menggunakan start_video_stream()

6. Membaca dan mengambil gambar setiap frame dari webcam

7. Supaya wajah lebih mudah dikenali sistem akan meningkatkan pencahayaan pada gambar menggunakan improve_lighting(image)

8. Mendeteksi wajah dan menghitung encodingnya 

9. Mengenali dan membandingkan wajah yang terdeteksi dengan data yang sudah tersimpan dan memberikan nama serta peran yang sesuai dengan wajah menggunakan check_known_face

10. Jika wajah dikenal saat pertama kali hadir maka sistem akan menyimpan waktu kedatangan, berikan ucapan selamat datang dan menyimoan foto wajah

11. Jika wajahdikenal setekah jam 15.00 maka sistem akan menyimpan waktu pulang, memberikan ucapan selamat jalan dan menyimpan foto wajah

12. Jika wajah tidak bisa dikenali maka siste akan menampilkan label press s untuk registrasi

13. Layar akan menampilkan kotak yang bertuliskan nama pemilik wajah tersebut

14. Untuk registrasi wajah baru maka setelah menekan s maka akan menampilkan dialog untuk imput nama dan peran serta menyimpan wajah yang terdeteksi

15. Untuk keluar dari program tekan q maka akan menutup kamera dan jendela video

16. Jalankan start_video_stram() untuk memulai proses seperti sebelumnya
 

# Dokumentasi Cara Penggunaan untuk User
1. Pastikan wajah kamu terlihat jelas di depan kamera

2. Jika wajahmu sudah terdaftar: kamera akan otomatis mengenali wajahmu dan akan mendengar suara "Selamat datang, [Nama]" maka kamu sudah terabsen hadir.

3. Jika wajahmu belum terdaftar: Layar akan menunjukkan press S to register. Kamu akan diminta untuk menuliskan nama lengkap dan peran. Setelah terdaftar maka wajahmu dapat dikenali secara otomatis saat absensi berikutnya.

4. Setelah jam 15.00, ulangi menghadap kamera, setelah kamera mengenali dan menyapa "Selamat Jalan [Nama]" maka kamu sudah terabsen pulang.
