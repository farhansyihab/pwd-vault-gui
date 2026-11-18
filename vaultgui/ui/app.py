import tkinter as tk
from tkinter import ttk, messagebox
from vaultgui.server_manager import ServerManager
from vaultgui.api_client import APIClient, AuthError, RateLimitError
from vaultgui.worker import Worker
from vaultgui import config

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("pwd-vault")
        self.root.geometry("500x400")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.server_manager = ServerManager()
        self.api_client = APIClient()
        self.worker = Worker(root)
        self.current_view = None

        self._build_ui()
        self._auto_start_server()

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.server_frame = ttk.LabelFrame(main_frame, text="Server Backend", padding=10)
        self.server_frame.pack(fill=tk.X, pady=(0, 10))

        self.server_status = ttk.Label(self.server_frame, text="Status: Memeriksa...", foreground="blue")
        self.server_status.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_start = ttk.Button(self.server_frame, text="Mulai", command=self.start_server)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        self.btn_stop = ttk.Button(self.server_frame, text="Hentikan", command=self.stop_server, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.content_frame = ttk.Frame(main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

    def _auto_start_server(self):
        if not self.server_manager.is_running():
            self.start_server()
        else:
            self._update_server_status(True)

    def _update_server_status(self, running: bool):
        if running:
            self.server_status.config(text="Status: Berjalan", foreground="green")
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
        else:
            self.server_status.config(text="Status: Berhenti", foreground="red")
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)

    def start_server(self):
        self.btn_start.config(state=tk.DISABLED)
        self.server_status.config(text="Status: Memulai...", foreground="orange")
        self.worker.submit(self.server_manager.start_server, on_result=self._on_start_done, on_error=self._on_start_error)

    def _on_start_done(self, result=None):
        self._update_server_status(self.server_manager.is_running())

    def _on_start_error(self, error):
        self.server_status.config(text=f"Status: Gagal ({error})", foreground="red")
        self.btn_start.config(state=tk.NORMAL)

    def stop_server(self):
        self.btn_stop.config(state=tk.DISABLED)
        self.server_status.config(text="Status: Menghentikan...", foreground="orange")
        self.worker.submit(self.server_manager.stop_server, on_result=self._on_stop_done)

    def _on_stop_done(self, result=None):
        self._update_server_status(False)

    def switch_view(self, view_class, *args, **kwargs):
        if self.current_view:
            self.current_view.destroy()
        self.current_view = view_class(self.content_frame, self, *args, **kwargs)
        self.current_view.pack(fill=tk.BOTH, expand=True)

    def on_close(self):
        if self.server_manager.process:
            if messagebox.askyesno("Keluar", "Server backend akan dihentikan. Lanjutkan?"):
                self.server_manager.stop_server()
                self.worker.shutdown()
                self.root.destroy()
        else:
            self.worker.shutdown()
            self.root.destroy()