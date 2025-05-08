# Dokumentasi Hasil Riset
**Library Alternatif**
1. Dear PyGui sebagai pengganti tkinter
2. MediaPipe sebagai pengganti dlib
3. Coqui TTS sebagai pengganti pyttsx3

# Dear PyGui
**Perbandingannya dengan tkinter:**
1. Dear PyGui memiliki performansi yang sangat cepat (GPU-Accelerated) dibandingkan dengan tkinter yang lambat untuk mendeteksi secara real time (CPU-Based)
2. Dear PyGui memiliki tampilan UI yang lebih modern

**Cara Instalasi Dear PyGui**
1. Menjalankan perintah: 
pip install dearpygui

**Penggunaan di Python**

import dearpygui.dearpygui as dpg

import cv2

# MediaPipe
**Kelebihan MediaPipe Dibandingkan dengan dlib**
1. Deteksi wajah 468 landmark (lebih detail dari Dlib)
2. Optimasi untuk real-time (30+ FPS di CPU/GPU)
3. Sudah include pose, tangan, dan object detection

**Cara Instalasi MediaPipe**
1. Menjalankan printah:
pip install mediapipe opencv-python

**Penggunaan MediaPipe di Python Sebagai Face Detection**

import cv2

import mediapipe as mp

# Coqui TTS 
**Perbandingan Coqui TTS dengan tkinter untuk Text-to-Speech**
1. Coqui TTS memiliki suara yang lebih natural dibandingkan dengan pyttsx3 (lebih robotik)
2. Coqui TTS dapat berbicara lebih dari 70 bahasa (Multibahasa) dibandingkan dengan pyttsx3 yang tergantung OS
3. Instalasinya lebih kompleks karena membutuhkan dependencies, sedangakan untuk pyttx3 sangant mudah  (menggunakan pip install)


**Cara Instalasi Coqui TTS**
1. Pastikan sudah install PyTorch terlebih dahulu (https://pytorch.org/)
2. Menjalankan perintah: pip install torch torchaudio dan pip install TTS

**Penggunaan Coqui TTS di Python**

from TTS.api import TTS

**#Generate speech (simpan ke file)**

tts.tts_to_file(text="(masukkan text)", 
                
                file_path="output.wav",
                
                speaker="female")

data, fs = sf.read("output.wav")

sd.play(data, fs)

sd.wait()

**Daftar Model Coqui TTS**
1. Bahasa Inggtis: tts_models/en/ljspeech/tacotron2-DDC	
2. Multibahasa: tts_models/multilingual/multi-dataset/your_tts
3. Jerman: tts_models/de/thorsten/tacotron2-DCA