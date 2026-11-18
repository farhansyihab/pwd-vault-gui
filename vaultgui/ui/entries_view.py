"""Daftar entri dengan pencarian, plus aksi tampilkan/salin password dan buka URL."""

import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import urlparse
import webbrowser

import httpx

from vaultgui import config
from vaultgui.clipboard import copy_to_clipboard


class EntriesView(ttk.Frame):
    """Daftar entri (tanpa password) dengan pencarian provider/username.

    Stage 8 additions:
    - Tampilkan password: fetch via API, tampilkan sebentar di label,
      sembunyikan otomatis setelah HIDE_PASSWORD_MS (default 15 detik).
    - Salin password: fetch via API, salin ke clipboard dengan auto-clear
      setelah CLIPBOARD_CLEAR_SECONDS (default 30 detik, hanya jika isi
      clipboard masih sama).
    - Buka URL: ambil URL dari cache entri yang sudah dimuat, validasi skema
      hanya http/https, lalu buka di browser.
    """

    SEARCH_DEBOUNCE_MS = 300
    HIDE_PASSWORD_MS = config.PASSWORD_HIDE_TIMEOUT * 1000
    CLIPBOARD_CLEAR_SECONDS = config.CLIPBOARD_CLEAR_TIMEOUT

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._search_after_id = None
        self._hide_password_after_id = None
        self._entries_by_id = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, pady=5)

        ttk.Label(control_frame, text="Pencarian:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)
        self.search_entry = ttk.Entry(control_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Button(control_frame, text="Segarkan", command=self.refresh).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Logout", command=self._on_logout).pack(side=tk.RIGHT, padx=5)

        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(action_frame, text="Tambah", command=self._on_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Ubah", command=self._on_edit).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Hapus", command=self._on_delete).pack(side=tk.LEFT, padx=5)

        secret_frame = ttk.Frame(self)
        secret_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(
            secret_frame, text="Tampilkan Password", command=self._on_reveal_password
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            secret_frame, text="Salin Password", command=self._on_copy_password
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            secret_frame, text="Buka URL", command=self._on_open_url
        ).pack(side=tk.LEFT, padx=5)

        self.password_display_var = tk.StringVar(value="")
        self.password_display_label = ttk.Label(
            self,
            textvariable=self.password_display_var,
            foreground="darkgreen",
            font=("TkFixedFont", 10, "bold"),
            anchor=tk.W,
        )
        self.password_display_label.pack(fill=tk.X, pady=(2, 0))

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        columns = ("id", "provider", "username", "email")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for col, heading, width in (
            ("id", "ID", 50),
            ("provider", "Provider", 120),
            ("username", "Username", 150),
            ("email", "Email", 180),
        ):
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, stretch=True)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, foreground="gray").pack(fill=tk.X, pady=(5, 0))

    # ---------- Data loading ----------

    def _on_search_changed(self, *_args):
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(self.SEARCH_DEBOUNCE_MS, self.refresh)

    def refresh(self):
        if self._search_after_id is not None:
            try:
                self.after_cancel(self._search_after_id)
            except tk.TclError:
                pass
            self._search_after_id = None

        # Hide any password currently displayed; selection may change.
        self._hide_password()

        query = self.search_var.get().strip()
        self.status_var.set("Memuat...")
        self.app.worker.submit(
            self.app.api_client.get_entries,
            query,
            on_result=self._on_data_loaded,
            on_error=self._on_data_error,
        )

    def _on_data_loaded(self, entries):
        # Drop the previous cache and any displayed secret.
        self._hide_password()
        self._entries_by_id = {}
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not entries:
            if self.search_var.get().strip():
                self.status_var.set("Tidak ada entri yang cocok dengan pencarian.")
            else:
                self.status_var.set("Belum ada entri.")
            return

        for entry in entries:
            entry_id = entry.get("id")
            if entry_id is not None:
                self._entries_by_id[str(entry_id)] = entry
            self.tree.insert(
                "",
                tk.END,
                values=(
                    entry.get("id", ""),
                    entry.get("provider") or "-",
                    entry.get("username") or "-",
                    entry.get("email") or "-",
                ),
            )
        self.status_var.set(f"{len(entries)} entri ditampilkan.")

    def _on_data_error(self, error, action_msg="Gagal memuat entri"):
        # Lazy import to avoid circular dependency with login_view module.
        from vaultgui.ui.login_view import LoginView

        self.status_var.set("")

        if isinstance(error, httpx.HTTPStatusError) and error.response is not None:
            if error.response.status_code == 401:
                messagebox.showwarning(
                    "Sesi Berakhir",
                    "Sesi Anda telah berakhir. Silakan login kembali.",
                )
                self.app.switch_view(LoginView)
                return

        self.status_var.set(f"{action_msg}: {self._friendly_error(error)}")

    @staticmethod
    def _friendly_error(error):
        if isinstance(error, httpx.RequestError):
            return "Tidak dapat terhubung ke server. Pastikan server berjalan."
        if isinstance(error, httpx.HTTPStatusError) and error.response is not None:
            return f"Server mengembalikan status {error.response.status_code}."
        return str(error) or "Kesalahan tidak dikenal."

    # ---------- Selection helper ----------

    def _selected_values(self):
        selected = self.tree.selection()
        if not selected:
            return None
        return self.tree.item(selected[0])["values"]

    # ---------- Add / Edit / Delete ----------

    def _on_add(self):
        # Lazy import to avoid circular dependency with entry_form module.
        from vaultgui.ui.entry_form import EntryForm

        self.app.switch_view(EntryForm)

    def _on_edit(self):
        values = self._selected_values()
        if values is None:
            messagebox.showwarning(
                "Pilih entri", "Pilih entri yang ingin diubah terlebih dahulu."
            )
            return
        entry_id = values[0]
        self.status_var.set("Memuat data entri...")
        self.app.worker.submit(
            self.app.api_client.get_entry,
            entry_id,
            on_result=self._on_entry_loaded_for_edit,
            on_error=self._on_edit_load_error,
        )

    def _on_entry_loaded_for_edit(self, entry):
        # Lazy import to avoid circular dependency with entry_form module.
        from vaultgui.ui.entry_form import EntryForm

        self.status_var.set("")
        if not entry:
            self.status_var.set("Entri tidak ditemukan.")
            return
        self.app.switch_view(EntryForm, entry=entry)

    def _on_edit_load_error(self, error):
        self._on_data_error(error, action_msg="Gagal memuat entri untuk diubah")

    def _on_delete(self):
        values = self._selected_values()
        if values is None:
            messagebox.showwarning(
                "Pilih entri", "Pilih entri yang ingin dihapus terlebih dahulu."
            )
            return
        entry_id = values[0]
        provider = values[1]
        username = values[2]
        if not messagebox.askyesno(
            "Konfirmasi Hapus",
            f"Hapus entri '{provider}' untuk '{username}'? Tindakan ini tidak dapat dibatalkan.",
        ):
            return
        self.status_var.set("Menghapus...")
        self.app.worker.submit(
            self.app.api_client.delete_entry,
            entry_id,
            on_result=self._on_delete_success,
            on_error=self._on_delete_error,
        )

    def _on_delete_success(self, _result):
        self.refresh()

    def _on_delete_error(self, error):
        self._on_data_error(error, action_msg="Gagal menghapus entri")

    # ---------- Reveal password ----------

    def _on_reveal_password(self):
        values = self._selected_values()
        if values is None:
            messagebox.showwarning(
                "Pilih entri",
                "Pilih entri yang password-nya ingin ditampilkan terlebih dahulu.",
            )
            return
        entry_id = values[0]
        self.status_var.set("Memuat password...")
        self.app.worker.submit(
            self.app.api_client.get_entry_password,
            entry_id,
            on_result=self._on_reveal_success,
            on_error=self._on_reveal_error,
        )

    def _on_reveal_success(self, result):
        if not isinstance(result, dict) or "password" not in result:
            self._hide_password()
            self.status_var.set("Tidak dapat menampilkan password dari server.")
            return
        password = result.get("password") or ""
        self.password_display_var.set(password)
        self._schedule_password_hide()
        self.status_var.set(
            f"Password ditampilkan. Akan disembunyikan otomatis dalam "
            f"{self.HIDE_PASSWORD_MS // 1000} detik."
        )

    def _on_reveal_error(self, error):
        self._hide_password()
        self._on_data_error(error, action_msg="Gagal menampilkan password")

    def _schedule_password_hide(self):
        if self._hide_password_after_id is not None:
            try:
                self.after_cancel(self._hide_password_after_id)
            except tk.TclError:
                pass
        self._hide_password_after_id = self.after(
            self.HIDE_PASSWORD_MS, self._auto_hide_password
        )

    def _auto_hide_password(self):
        self._hide_password_after_id = None
        self.password_display_var.set("")
        self.status_var.set("Password disembunyikan otomatis.")

    def _hide_password(self):
        """Internal: clear the displayed password and cancel any pending hide."""
        if self._hide_password_after_id is not None:
            try:
                self.after_cancel(self._hide_password_after_id)
            except tk.TclError:
                pass
            self._hide_password_after_id = None
        if hasattr(self, "password_display_var"):
            self.password_display_var.set("")

    # ---------- Copy password ----------

    def _on_copy_password(self):
        values = self._selected_values()
        if values is None:
            messagebox.showwarning(
                "Pilih entri",
                "Pilih entri yang password-nya ingin disalin terlebih dahulu.",
            )
            return
        entry_id = values[0]
        self.status_var.set("Menyiapkan salin password...")
        self.app.worker.submit(
            self.app.api_client.get_entry_password,
            entry_id,
            on_result=self._on_copy_success,
            on_error=self._on_copy_error,
        )

    def _on_copy_success(self, result):
        if not isinstance(result, dict) or "password" not in result:
            self.status_var.set("Tidak dapat menyalin password dari server.")
            return
        password = result.get("password") or ""
        try:
            copy_to_clipboard(password, clear_after=self.CLIPBOARD_CLEAR_SECONDS)
        except Exception:
            self.status_var.set("Gagal menyalin password ke clipboard.")
            return
        self.status_var.set(
            f"Password disalin. Akan dihapus otomatis dalam "
            f"{self.CLIPBOARD_CLEAR_SECONDS} detik."
        )

    def _on_copy_error(self, error):
        self._on_data_error(error, action_msg="Gagal menyalin password")

    # ---------- Open URL ----------

    def _on_open_url(self):
        values = self._selected_values()
        if values is None:
            messagebox.showwarning(
                "Pilih entri",
                "Pilih entri yang URL-nya ingin dibuka terlebih dahulu.",
            )
            return
        entry_id = values[0]
        entry = self._entries_by_id.get(str(entry_id))
        if not entry:
            self.status_var.set(
                "Data entri tidak tersedia. Tekan Segarkan lalu coba lagi."
            )
            return
        url = (entry.get("url") or "").strip()
        if not url:
            messagebox.showinfo(
                "URL Kosong", "Entri ini tidak memiliki URL."
            )
            return
        if not self._is_safe_url(url):
            messagebox.showwarning(
                "URL Tidak Valid",
                "Hanya URL dengan skema http atau https yang dapat dibuka.",
            )
            return
        try:
            opened = webbrowser.open(url)
        except Exception:
            opened = False
        if opened:
            self.status_var.set("URL dibuka di browser.")
        else:
            self.status_var.set(
                "Gagal membuka URL di browser. Periksa pengaturan browser default."
            )

    @staticmethod
    def _is_safe_url(url):
        """True only for URLs whose scheme is exactly http or https."""
        try:
            parsed = urlparse(url)
        except Exception:
            return False
        return parsed.scheme in ("http", "https")

    # ---------- Logout ----------

    def _on_logout(self):
        # Lazy import to avoid circular dependency with login_view module.
        from vaultgui.ui.login_view import LoginView

        self.app.worker.submit(
            self.app.api_client.logout,
            on_result=lambda _result: self.app.switch_view(LoginView),
            on_error=lambda _error: self.app.switch_view(LoginView),
        )

    # ---------- Lifecycle ----------

    def destroy(self):
        # Cancel any pending timers and hide any displayed secret before the
        # widget goes away. Prevents TclError from `after` callbacks targeting
        # a destroyed widget.
        self._hide_password()
        if self._search_after_id is not None:
            try:
                self.after_cancel(self._search_after_id)
            except tk.TclError:
                pass
            self._search_after_id = None
        super().destroy()