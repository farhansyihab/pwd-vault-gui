import tkinter as tk
from tkinter import ttk, messagebox

import httpx


class EntriesView(ttk.Frame):
    """Daftar entri (tanpa password) dengan pencarian provider/username."""

    SEARCH_DEBOUNCE_MS = 300

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._search_after_id = None
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

        query = self.search_var.get().strip()
        self.status_var.set("Memuat...")
        self.app.worker.submit(
            self.app.api_client.get_entries,
            query,
            on_result=self._on_data_loaded,
            on_error=self._on_data_error,
        )

    def _on_data_loaded(self, entries):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not entries:
            if self.search_var.get().strip():
                self.status_var.set("Tidak ada entri yang cocok dengan pencarian.")
            else:
                self.status_var.set("Belum ada entri.")
            return

        for entry in entries:
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

    # ---------- Add / Edit / Delete ----------

    def _selected_values(self):
        selected = self.tree.selection()
        if not selected:
            return None
        return self.tree.item(selected[0])["values"]

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

    # ---------- Logout ----------

    def _on_logout(self):
        # Lazy import to avoid circular dependency with login_view module.
        from vaultgui.ui.login_view import LoginView

        self.app.worker.submit(
            self.app.api_client.logout,
            on_result=lambda _result: self.app.switch_view(LoginView),
            on_error=lambda _error: self.app.switch_view(LoginView),
        )