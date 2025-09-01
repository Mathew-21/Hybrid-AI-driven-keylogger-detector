import os
import time
import psutil
import joblib
import numpy as np
from pynput import keyboard
from sklearn.ensemble import IsolationForest
from plyer import notification

# Real-time alert function
def show_alert(message):
    try:
        notification.notify(
            title="Security Alert",
            message=message,
            timeout=5
        )
    except Exception as e:
        print(f"[ERROR] Notification failed: {e}")
    print(message)

# Collect real keystroke timing data
def collect_training_data():
    keystroke_timings = []
    training_data = []
    start_time = time.time()
    print("[INFO] Press keys for 30 seconds to collect normal keystroke timing data.")

    def on_key_press(key):
        nonlocal keystroke_timings, training_data
        current_time = time.time()
        if len(keystroke_timings) > 0:
            time_diff = current_time - keystroke_timings[-1]
            training_data.append([time_diff])
        keystroke_timings.append(current_time)

    with keyboard.Listener(on_press=on_key_press) as listener:
        while time.time() - start_time < 30:
            time.sleep(0.1)
        listener.stop()

    if training_data:
        np.save("real_keystroke_data.npy", training_data)
        print(f"[INFO] Training data saved. Collected {len(training_data)} samples.")
    else:
        print("[WARNING] No keystroke data collected. Try again.")

# Train AI model
def train_ai_model():
    if not os.path.exists("real_keystroke_data.npy"):
        print("[ERROR] No training data found.")
        return
    training_data = np.load("real_keystroke_data.npy")
    model = IsolationForest(contamination=0.02)
    model.fit(training_data)
    joblib.dump(model, "keylogger_ai_model.pkl")
    print("[INFO] AI Model trained with keystroke data.")

# Load the AI model
def load_ai_model():
    if not os.path.exists("keylogger_ai_model.pkl"):
        print("[WARNING] AI model not found. Training a new model...")
        collect_training_data()
        train_ai_model()
    return joblib.load("keylogger_ai_model.pkl")

ai_model = load_ai_model()
keystroke_timings = []

# Detect suspicious processes
def detect_suspicious_processes():
    known_keyloggers = ["keylogger.exe", "stealth.exe", "logger.exe"]
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'].lower() in known_keyloggers:
                show_alert(f"[ALERT] Suspicious Process Detected: {proc.info['name']} (PID: {proc.info['pid']})")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

# Key press detection
def on_key_press(key):
    global keystroke_timings, ai_model
    current_time = time.time()

    if len(keystroke_timings) > 1:
        time_diff = current_time - keystroke_timings[-1]
        prediction = ai_model.predict([[time_diff]])
        if prediction[0] == -1:
            show_alert("[ALERT] Unusual Keystroke Timing Detected! Possible Keylogger Activity.")

    keystroke_timings.append(current_time)
    if len(keystroke_timings) > 100:
        keystroke_timings.pop(0)

# Start monitoring
def start_monitoring():
    print("[INFO] Press ESC to exit.")
    detect_suspicious_processes()

    def on_press(key):
        if key == keyboard.Key.esc:
            print("[INFO] Exiting Keylogger Detector...")
            return False
        on_key_press(key)

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

if __name__ == "__main__":
    start_monitoring()
