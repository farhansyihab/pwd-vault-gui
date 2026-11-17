import os

HOST = "127.0.0.1"
PORT = 8000
BACKEND_DIR = os.path.expanduser("~/Proyek/pwd-vault")
BACKEND_PYTHON = os.path.join(BACKEND_DIR, ".venv", "bin", "python")
LOG_FILE = os.path.join("logs", "server.log")
AUTO_LOCK_TIMEOUT = 300  # 5 menit
PASSWORD_HIDE_TIMEOUT = 15
CLIPBOARD_CLEAR_TIMEOUT = 30
