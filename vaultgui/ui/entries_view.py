import tkinter as tk
from tkinter import ttk

class EntriesView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        ttk.Label(self, text="Daftar Entri (belum diimplementasikan)").pack(pady=20)
        ttk.Button(self, text="Logout", command=self._on_logout).pack(pady=10)

    def _on_logout(self):
        self.app.worker.submit(
            self.app.api_client.logout,
            on_result=lambda _: self.app.switch_view("LoginView")
        )