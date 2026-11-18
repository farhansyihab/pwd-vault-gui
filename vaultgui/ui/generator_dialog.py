"""Dialog pembuat password acak.

Memanggil endpoint `GET /alat/password-acak` lewat `worker` dan
menyediakan opsi panjang (8-128) serta jenis karakter.

Hasil dapat langsung dipakai pada formulir lewat callback `on_use`,
yang dipanggil dengan string password hasil generate.
"""

import tkinter as tk
from tkinter import ttk, messagebox

import httpx


class GeneratorDialog(tk.Toplevel):
    MIN_LENGTH = 8
    MAX_LENGTH = 128

    def __init__(self, parent, app, on_use=None):
        super().__init__(parent)
        self.app = app
        self.on_use = on_use
        self._closed = False

        self.title("Buat Password Acak")
        self.resizable(False, False)
        try:
            self.transient(parent)
        except tk.TclError:
            pass

        self._length_var = tk.IntVar(value=16)
        self._lower_var = tk.BooleanVar(value=True)
        self._upper_var = tk.BooleanVar(value=True)
        self._digit_var = tk.BooleanVar(value=True)
        self._symbol_var = tk.BooleanVar(value=False)
        self._result_var = tk.StringVar(value="")
        self._show_var = tk.BooleanVar(value=False)
        self._status_var = tk.StringVar(value="")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._center_on_parent(parent)
        try:
            self.grab_set()
        except tk.TclError:
            # Some environments (e.g. withdrawn parents in tests)
            # cannot grab; the dialog still works, just not modal.
            pass

    # ---------- UI ----------

    def _build_ui(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        length_frame = ttk.Frame(frame)
        length_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(length_frame, text="Panjang:").pack(side=tk.LEFT, padx=(0, 5))
        self._length_spin = ttk.Spinbox(
            length_frame,
            from_=self.MIN_LENGTH,
            to=self.MAX_LENGTH,
            textvariable=self._length_var,
            width=8,
        )
        self._length_spin.pack(side=tk.LEFT)
        ttk.Label(
            length_frame,
            text=f"({self.MIN_LENGTH}-{self.MAX_LENGTH})",
            foreground="gray",
        ).pack(side=tk.LEFT, padx=(5, 0))

        opt_frame = ttk.LabelFrame(frame, text="Jenis Karakter", padding=5)
        opt_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Checkbutton(
            opt_frame, text="Huruf kecil (a-z)", variable=self._lower_var
        ).pack(anchor=tk.W)
        ttk.Checkbutton(
            opt_frame, text="Huruf besar (A-Z)", variable=self._upper_var
        ).pack(anchor=tk.W)
        ttk.Checkbutton(
            opt_frame, text="Angka (0-9)", variable=self._digit_var
        ).pack(anchor=tk.W)
        ttk.Checkbutton(
            opt_frame, text="Simbol (!@#...)", variable=self._symbol_var
        ).pack(anchor=tk.W)

        result_frame = ttk.Frame(frame)
        result_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(result_frame, text="Hasil:").pack(side=tk.LEFT, padx=(0, 5))
        self._result_entry = ttk.Entry(
            result_frame,
            textvariable=self._result_var,
            show="\u2022",
            width=30,
            state="readonly",
        )
        self._result_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Checkbutton(
            result_frame,
            text="Tampilkan",
            variable=self._show_var,
            command=self._toggle_show,
        ).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(
            frame, textvariable=self._status_var, foreground="gray", wraplength=380
        ).pack(fill=tk.X, pady=(0, 5))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_frame, text="Acak", command=self._on_generate).pack(
            side=tk.LEFT, padx=5
        )
        self._use_btn = ttk.Button(
            btn_frame,
            text="Gunakan",
            command=self._on_use_click,
            state=tk.DISABLED,
        )
        self._use_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Batal", command=self._on_close).pack(
            side=tk.LEFT, padx=5
        )

    def _toggle_show(self):
        try:
            self._result_entry.configure(show="" if self._show_var.get() else "\u2022")
        except tk.TclError:
            pass

    def _center_on_parent(self, parent):
        try:
            self.update_idletasks()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            if pw <= 1 or ph <= 1:
                return
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            w = self.winfo_width()
            h = self.winfo_height()
            x = max(0, px + (pw - w) // 2)
            y = max(0, py + (ph - h) // 2)
            self.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    # ---------- Validation ----------

    def _validate_options(self):
        try:
            length = int(self._length_var.get())
        except (ValueError, tk.TclError):
            self._status_var.set(
                f"Panjang harus angka {self.MIN_LENGTH}-{self.MAX_LENGTH}."
            )
            return None
        if not (self.MIN_LENGTH <= length <= self.MAX_LENGTH):
            self._status_var.set(
                f"Panjang harus {self.MIN_LENGTH}-{self.MAX_LENGTH}."
            )
            return None
        if not (
            self._lower_var.get()
            or self._upper_var.get()
            or self._digit_var.get()
            or self._symbol_var.get()
        ):
            self._status_var.set("Pilih minimal satu jenis karakter.")
            return None
        return length

    # ---------- Actions ----------

    def _on_generate(self):
        length = self._validate_options()
        if length is None:
            return
        self._status_var.set("Membuat password...")
        self.app.worker.submit(
            self.app.api_client.generate_password,
            length=length,
            huruf_kecil=self._lower_var.get(),
            huruf_besar=self._upper_var.get(),
            angka=self._digit_var.get(),
            simbol=self._symbol_var.get(),
            on_result=self._on_generated,
            on_error=self._on_error,
        )

    def _on_generated(self, result):
        if self._closed or not self.winfo_exists():
            return
        if not isinstance(result, dict) or "password" not in result:
            self._status_var.set(
                "Server tidak mengembalikan password yang valid."
            )
            return
        password = result.get("password") or ""
        if not password:
            self._status_var.set("Server mengembalikan password kosong.")
            return
        self._result_var.set(password)
        try:
            self._use_btn.configure(state=tk.NORMAL)
        except tk.TclError:
            pass
        self._status_var.set("Password berhasil dibuat.")

    def _on_error(self, error):
        if self._closed or not self.winfo_exists():
            return
        if isinstance(error, httpx.HTTPStatusError) and error.response is not None:
            if error.response.status_code == 401:
                messagebox.showwarning(
                    "Sesi Berakhir",
                    "Sesi Anda telah berakhir. Silakan login kembali.",
                    parent=self,
                )
                self._on_close()
                return
            self._status_var.set(
                f"Gagal membuat password: server mengembalikan status "
                f"{error.response.status_code}."
            )
            return
        if isinstance(error, httpx.RequestError):
            self._status_var.set(
                "Tidak dapat terhubung ke server. Pastikan server berjalan."
            )
            return
        self._status_var.set(f"Gagal membuat password: {error}")

    def _on_use_click(self):
        password = self._result_var.get()
        if not password:
            messagebox.showwarning(
                "Belum Ada Password",
                "Klik Acak terlebih dahulu untuk membuat password.",
                parent=self,
            )
            return
        if self.on_use:
            self.on_use(password)
        self._on_close()

    def _on_close(self):
        self._closed = True
        try:
            self.destroy()
        except tk.TclError:
            pass