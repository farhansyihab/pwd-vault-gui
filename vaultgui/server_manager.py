import subprocess
import time
import httpx
import os
from pathlib import Path
from vaultgui import config

class ServerManager:
    def __init__(self):
        self.process = None
        self.log_file = Path(config.LOG_FILE)
        self.log_file.parent.mkdir(exist_ok=True)

    def is_running(self) -> bool:
        try:
            response = httpx.get(f"http://{config.HOST}:{config.PORT}/openapi.json", timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("info", {}).get("title") == "pwd-vault"
        except (httpx.RequestError, httpx.HTTPStatusError):
            pass
        return False

    def start_server(self):
        if self.is_running():
            return
        
        with open(self.log_file, "a") as f:
            self.process = subprocess.Popen(
                [config.BACKEND_PYTHON, "-m", "uvicorn", "app.main:create_app", 
                 "--factory", "--host", config.HOST, "--port", str(config.PORT)],
                cwd=config.BACKEND_DIR,
                stdout=f,
                stderr=subprocess.STDOUT
            )

    def stop_server(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
