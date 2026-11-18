"""Form tambah/ubah entri. Password lama tidak pernah ditampilkan di UI."""

import tkinter as tk
from tkinter import ttk, messagebox

import httpx


class EntryForm(ttk.Frame):
    """Form untuk menambah entri baru atau mengubah entri yang sudah ada.

    Saat mode ubah dan kolom password dikosongkan, GUI mengambil password lama
    lewat API (`get_entry_password`) agar tidak perlu ditampilkan ke pengguna.

    Layout: the field area is wrapped in a scrollable canvas so it stays usable
    on short windows, while the Simpan/Batal buttons live in a fixed footer
    outside the scroll region. This guarantees the action buttons are always
    visible regardless of window height.

    Tahap 9: tombol "Acak..." di samping kolom password membuka
    GeneratorDialog; hasilnya langsung diisi ke kolom password.
    """

    FIELD_NAMES = ("provider", "username", "password", "email", "url", "keterangan")

    def __init__(self, parent, app, entry=None):
        super().__init__(parent)
        self.app = app
        self.entry = entry
        self.is_edit = entry is not None
        self._vars = {name: tk.StringVar() for name in self.FIELD_NAMES}
        self._canvas = None
        self._scrollable = None
        self._build_ui()
        if self.is_edit:
            self._populate(entry)
        # Focus the first editable field for faster data entry.
        self.after(50, lambda: self._first_entry.focus_set())

    # ---------- UI ----------

    def _build_ui(self):
        title = "Ubah Entri" if self.is_edit else "Tambah Entri"

        # Fixed header (title) at the top.
        ttk.Label(
            self, text=title, font=("TkDefaultFont", 12, "bold")
        ).pack(pady=(10, 5))

        # Fixed footer with action buttons, packed FIRST from the bottom so it
        # never gets pushed off-screen by the scrollable body.
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="Simpan", command=self._on_save).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="Batal", command=self._on_cancel).pack(
            side=tk.LEFT, padx=5
        )

        # Scrollable body: Canvas + vertical Scrollbar + inner Frame.
        body = ttk.Frame(self)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(body, highlightthickness=0, borderwidth=0)
        vbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)

        inner = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        self._canvas = canvas
        self._scrollable = inner

        # Keep the inner frame as wide as the canvas so fields stretch nicely.
        def _on_canvas_configure(event):
            canvas.itemconfigure(window_id, width=event.width)

        # Update scrollregion when inner content changes size.
        def _on_inner_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        canvas.bind("<Configure>", _on_canvas_configure)
        inner.bind("<Configure>", _on_inner_configure)

        # Mouse wheel scrolling only while the pointer is over the canvas.
        def _on_mousewheel(event):
            delta = -1 if event.delta > 0 else 1
            canvas.yview_scroll(delta, "units")

        def _bind_wheel(_event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
            canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        def _unbind_wheel(_event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)
        inner.bind("<Enter>", _bind_wheel)
        inner.bind("<Leave>", _unbind_wheel)

        # Form fields live inside the scrollable inner frame.
        form = ttk.Frame(inner)
        form.pack(pady=5, padx=10, fill=tk.X)

        labels = (
            ("provider", "Provider"),
            ("username", "Username"),
            ("password", "Password"),
            ("email", "Email"),
            ("url", "URL"),
            ("keterangan", "Keterangan"),
        )
        self._first_entry = None
        for i, (name, label) in enumerate(labels):
            ttk.Label(form, text=f"{label}:").grid(
                row=i, column=0, sticky=tk.W, pady=3, padx=5
            )
            show = "\u2022" if name == "password" else ""
            entry_widget = ttk.Entry(
                form, textvariable=self._vars[name], show=show, width=40
            )
            entry_widget.grid(row=i, column=1, sticky=tk.EW, pady=3, padx=5)
            if self._first_entry is None:
                self._first_entry = entry_widget
            if name == "password":
                ttk.Button(
                    form,
                    text="Acak...",
                    command=self._open_generator,
                    width=8,
                ).grid(row=i, column=2, sticky=tk.W, pady=3, padx=(0, 5))
        form.columnconfigure(1, weight=1)

        hint = (
            "Biarkan password kosong jika tidak ingin mengubah."
            if self.is_edit
            else "Provider, username, dan password wajib diisi."
        )
        ttk.Label(
            inner, text=hint, foreground="gray", wraplength=420
        ).pack(pady=(5, 5), padx=10)

        self.error_var = tk.StringVar()
        ttk.Label(
            inner, textvariable=self.error_var, foreground="red", wraplength=420
        ).pack(pady=(5, 5), padx=10)

    def _populate(self, entry):
        for field in ("provider", "username", "email", "url", "keterangan"):
            self._vars[field].set(entry.get(field) or "")
        # Password intentionally left empty.

    # ---------- Generator integration ----------

    def _open_generator(self):
        # Lazy import to avoid potential circular imports and keep the module
        # import graph light when the generator is never used.
        from vaultgui.ui.generator_dialog import GeneratorDialog

        GeneratorDialog(self, self.app, on_use=self._apply_generated_password)

    def _apply_generated_password(self, password):
        self._vars["password"].set(password)

    # ---------- Save ----------

    def _collect_payload(self):
        return {
            "provider": self._vars["provider"].get().strip(),
            "username": self._vars["username"].get().strip(),
            "password": self._vars["password"].get(),
            "email": self._vars["email"].get().strip() or None,
            "url": self._vars["url"].get().strip() or None,
            "keterangan": self._vars["keterangan"].get().strip() or None,
        }

    def _validate(self, payload):
        if not payload["provider"]:
            self.error_var.set("Provider wajib diisi.")
            return False
        if not payload["username"]:
            self.error_var.set("Username wajib diisi.")
            return False
        if not self.is_edit and not payload["password"]:
            self.error_var.set("Password wajib diisi.")
            return False
        return True

    def _on_save(self):
        payload = self._collect_payload()
        if not self._validate(payload):
            return
        self.error_var.set("")

        if self.is_edit and not payload["password"]:
            self._fetch_old_password_then_update(payload)
        elif self.is_edit:
            self._submit_update(payload)
        else:
            self._submit_create(payload)

    def _submit_create(self, payload):
        self.app.worker.submit(
            self.app.api_client.create_entry,
            payload,
            on_result=self._on_save_success,
            on_error=self._on_save_error,
        )

    def _submit_update(self, payload):
        self.app.worker.submit(
            self.app.api_client.update_entry,
            self.entry["id"],
            payload,
            on_result=self._on_save_success,
            on_error=self._on_save_error,
        )

    def _fetch_old_password_then_update(self, payload):
        self.app.worker.submit(
            self.app.api_client.get_entry_password,
            self.entry["id"],
            on_result=lambda result: self._on_old_password_fetched(result, payload),
            on_error=self._on_save_error,
        )

    def _on_old_password_fetched(self, result, payload):
        if not isinstance(result, dict) or "password" not in result:
            self.error_var.set(
                "Tidak dapat memuat password lama. Silakan isi password baru."
            )
            return
        payload["password"] = result.get("password") or ""
        self._submit_update(payload)

    def _on_save_success(self, _result):
        # Lazy import to avoid circular dependency with entries_view module.
        from vaultgui.ui.entries_view import EntriesView

        self.app.switch_view(EntriesView)

    def _on_save_error(self, error):
        # Lazy import to avoid circular dependency with login_view module.
        from vaultgui.ui.login_view import LoginView

        if isinstance(error, httpx.HTTPStatusError) and error.response is not None:
            status = error.response.status_code
            if status == 401:
                messagebox.showwarning(
                    "Sesi Berakhir",
                    "Sesi Anda telah berakhir. Silakan login kembali.",
                )
                self.app.switch_view(LoginView)
                return
            if status == 422:
                self.error_var.set(
                    "Input tidak valid:\n" + self._format_validation_error(error)
                )
                return

        self.error_var.set(f"Gagal menyimpan: {self._friendly_error(error)}")

    @staticmethod
    def _friendly_error(error):
        if isinstance(error, httpx.RequestError):
            return "Tidak dapat terhubung ke server."
        if isinstance(error, httpx.HTTPStatusError) and error.response is not None:
            return f"Server mengembalikan status {error.response.status_code}."
        return str(error) or "Kesalahan tidak dikenal."

    @staticmethod
    def _format_validation_error(error):
        try:
            data = error.response.json()
        except Exception:
            return "- (tidak dapat membaca detail)"
        detail = data.get("detail") if isinstance(data, dict) else None
        if isinstance(detail, list):
            lines = []
            for item in detail:
                if isinstance(item, dict):
                    loc = ".".join(
                        str(x) for x in item.get("loc", []) if x != "body"
                    )
                    msg = item.get("msg", "")
                    lines.append(f"- {loc}: {msg}" if loc else f"- {msg}")
                else:
                    lines.append(f"- {item}")
            return "\n".join(lines) if lines else "- (tidak ada detail)"
        if detail:
            return f"- {detail}"
        return "- (tidak ada detail)"

    def _on_cancel(self):
        # Lazy import to avoid circular dependency with entries_view module.
        from vaultgui.ui.entries_view import EntriesView

        self.app.switch_view(EntriesView)