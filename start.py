#!/usr/bin/env python3
"""
🛡️ BlinkSafe / SleepGuard - Master One-Click Startup Script
Automatically verifies Python, handles virtual environment creation,
installs missing dependencies, downloads MediaPipe models, manages ports,
and launches Flask cross-platform (macOS, Linux, Windows).
"""

import os
import sys
import socket
import subprocess
import time
import urllib.request

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
os.chdir(SCRIPT_DIR)

def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a TCP port is free for binding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False

def find_available_port(start_port: int = 5001, max_tries: int = 50) -> int:
    """Find the first available port starting from start_port."""
    for p in range(start_port, start_port + max_tries):
        if is_port_free(p):
            return p
    return start_port

def main():
    print("========================================")
    print("          BLINKSAFE STARTUP             ")
    print("========================================")

    # [1/7] Checking Python
    print("[1/7] Checking Python...")
    if sys.version_info[0] < 3:
        print("❌ ERROR: Python 3 is required to run BlinkSafe.")
        print("Please install Python 3 and try again.")
        sys.exit(1)
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"✓ Python {py_ver} detected")

    # [2/7] Checking virtual environment
    print("[2/7] Checking virtual environment...")
    in_venv = (sys.prefix != sys.base_prefix)
    venv_dir = os.path.join(SCRIPT_DIR, "venv")
    
    if not in_venv:
        if not os.path.exists(venv_dir):
            print("📦 Creating virtual environment (venv)...")
            try:
                subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
            except Exception as e:
                print(f"❌ ERROR: Failed to create virtual environment: {e}")
                sys.exit(1)

        # Determine venv python binary path
        if os.name == 'nt':
            venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
        else:
            venv_python = os.path.join(venv_dir, "bin", "python")

        if os.path.exists(venv_python) and os.path.realpath(sys.executable) != os.path.realpath(venv_python):
            # Re-execute inside virtualenv
            res = subprocess.run([venv_python] + sys.argv)
            sys.exit(res.returncode)

    print("✓ Virtual environment ready")

    # [3/7] Checking dependencies
    print("[3/7] Checking dependencies...")
    try:
        # Upgrade pip silently in venv
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--quiet"], check=False)
    except Exception:
        pass

    required_imports = ["flask", "cv2", "mediapipe", "numpy"]
    missing = False
    for pkg in required_imports:
        try:
            __import__(pkg)
        except ImportError:
            missing = True
            break

    if missing:
        print("📦 Missing Python dependencies detected. Installing from requirements.txt...")
        req_file = os.path.join(SCRIPT_DIR, "requirements.txt")
        if not os.path.exists(req_file):
            print("❌ ERROR: requirements.txt not found.")
            sys.exit(1)
        
        res = subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file])
        if res.returncode != 0:
            print("❌ ERROR: Failed to install project dependencies.")
            sys.exit(res.returncode)

        # Re-verify imports
        for pkg in required_imports:
            try:
                __import__(pkg)
            except ImportError:
                print(f"❌ ERROR: Package '{pkg}' could not be imported after installation.")
                sys.exit(1)

    print("✓ Dependencies ready")

    # [4/7] Checking MediaPipe & Face Recognition assets
    print("[4/7] Checking ML models & assets...")
    models_dir = os.path.join(SCRIPT_DIR, "models")
    os.makedirs(models_dir, exist_ok=True)
    
    # MediaPipe Face Landmarker
    mp_model_file = os.path.join(models_dir, "face_landmarker.task")
    mp_model_url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    if not os.path.exists(mp_model_file) or os.path.getsize(mp_model_file) == 0:
        print("📥 Downloading MediaPipe Face Landmarker model...")
        try:
            urllib.request.urlretrieve(mp_model_url, mp_model_file)
            print("✓ MediaPipe model downloaded")
        except Exception as e:
            print(f"❌ ERROR: Required MediaPipe model could not be downloaded: {e}")
            sys.exit(1)

    # OpenCV SFace ONNX model for Face Recognition embeddings
    sface_model_file = os.path.join(models_dir, "face_recognition_sface_2021dec.onnx")
    sface_model_url = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
    if not os.path.exists(sface_model_file) or os.path.getsize(sface_model_file) < 1000000:
        print("📥 Downloading OpenCV SFace Recognition ONNX model...")
        try:
            import ssl
            context = ssl._create_unverified_context()
            req = urllib.request.urlopen(sface_model_url, context=context)
            with open(sface_model_file, 'wb') as f:
                f.write(req.read())
            print("✓ SFace ONNX model downloaded successfully")
        except Exception as e:
            print(f"⚠️ WARNING: Could not download SFace model automatically: {e}")

    print("✓ Models and assets ready")

    # [5/7] Checking required directories
    print("[5/7] Checking directories...")
    required_dirs = [
        os.path.join(SCRIPT_DIR, "models"),
        os.path.join(SCRIPT_DIR, "data"),
        os.path.join(SCRIPT_DIR, "data", "sessions"),
        os.path.join(SCRIPT_DIR, "data", "faiss"),
        os.path.join(SCRIPT_DIR, "logs"),
        os.path.join(SCRIPT_DIR, "reports"),
    ]
    for d in required_dirs:
        os.makedirs(d, exist_ok=True)
    print("✓ Directories ready")

    # [6/7] Checking port & configuration
    print("[6/7] Checking port & configuration...")
    desired_port = 5001
    try:
        from config.config import FLASK_PORT
        desired_port = int(FLASK_PORT)
    except Exception:
        pass

    actual_port = desired_port
    if not is_port_free(desired_port):
        actual_port = find_available_port(desired_port + 1)
        print(f"⚠️ Port {desired_port} is in use. Using available port {actual_port} instead.")
        os.environ["PORT"] = str(actual_port)
    else:
        os.environ["PORT"] = str(desired_port)
        print(f"✓ Port {actual_port} available")

    # [7/7] Starting BlinkSafe
    print("[7/7] Starting BlinkSafe...")
    print("✓ Flask server starting...")
    print("========================================")
    print(f"BlinkSafe Dashboard:\nhttp://localhost:{actual_port}/")
    print(f"Live Monitor:\nhttp://localhost:{actual_port}/session")
    print("Press Ctrl+C to stop.")
    print("========================================")

    # Launch browser automatically after server initializes
    def _open_browser_async():
        time.sleep(1.2)
        try:
            import webbrowser
            webbrowser.open(f"http://localhost:{actual_port}/")
        except Exception:
            pass

    import threading
    threading.Thread(target=_open_browser_async, daemon=True).start()

    app_py = os.path.join(SCRIPT_DIR, "app.py")
    try:
        subprocess.run([sys.executable, app_py], check=True)
    except KeyboardInterrupt:
        print("\n👋 BlinkSafe shut down gracefully.")
    except Exception as e:
        print(f"\n❌ ERROR: BlinkSafe failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
