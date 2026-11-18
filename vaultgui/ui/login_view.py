import tkinter as tk
from tkinter import ttk
from vaultgui.api_client import AuthError, RateLimitError
from vaultgui.ui.entries_view import EntriesView

class LoginView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Login pwd-vault", font=("TkDefaultFont", 14, "bold")).pack(pady=(20, 10))
        
        ttk.Label(self, text="Akun dibuat via CLI di folder backend ~/Proyek/pwd-vault", 
                  foreground="gray", wraplength=350).pack(pady=(0, 20))

        form = ttk.Frame(self)
        form.pack(pady=10)

        ttk.Label(form, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.username_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.username_var, width=30).grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(form, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(form, textvariable=self.password_var, show="•", width=30)
        self.password_entry.grid(row=1, column=1, pady=5, padx=5)

        self.error_var = tk.StringVar()
        ttk.Label(self, textvariable=self.error_var, foreground="red", wraplength=350).pack(pady=(5, 10))

        ttk.Button(self, text="Login", command=self._on_login).pack(pady=5)
        self.password_entry.bind("<Return>", lambda e: self._on_login())

    def _on_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        if not username or not password:
            self.error_var.set("Username dan password wajib diisi")
            return
        self.error_var.set("")
        self.app.worker.submit(
            self.app.api_client.login, username, password,
            on_result=self._on_login_success,
            on_error=self._on_login_error
        )

    def _on_login_success(self, result):
        from vaultgui.ui.entries_view import EntriesView
        self.app.switch_view(EntriesView)

    def _on_login_error(self, error):
        if isinstance(error, AuthError):
            self.error_var.set("Username atau password salah")
        elif isinstance(error, RateLimitError):
            self.error_var.set("Terlalu banyak percobaan. Coba lagi 5 menit.")
        else:
            self.error_var.set(f"Kesalahan: {error}")