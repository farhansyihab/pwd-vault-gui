import tkinter as tk
from unittest.mock import MagicMock, patch

import httpx
import pytest

from vaultgui.ui.generator_dialog import GeneratorDialog


@pytest.fixture
def app_mock():
    root = tk.Tk()
    root.withdraw()
    app = MagicMock()
    app.root = root
    app.worker = MagicMock()
    app.api_client = MagicMock()
    yield app
    root.destroy()


def _cleanup(dialog):
    try:
        if dialog.winfo_exists():
            dialog.destroy()
    except tk.TclError:
        pass


# ---------- Defaults ----------


def test_dialog_default_values(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    try:
        assert dialog._length_var.get() == 16
        assert dialog._lower_var.get() is True
        assert dialog._upper_var.get() is True
        assert dialog._digit_var.get() is True
        assert dialog._symbol_var.get() is False
        assert dialog._result_var.get() == ""
    finally:
        _cleanup(dialog)


def test_dialog_use_button_initially_disabled(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    try:
        assert str(dialog._use_btn.cget("state")) == "disabled"
    finally:
        _cleanup(dialog)


# ---------- Validation ----------


def test_generate_rejects_length_below_minimum(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    try:
        dialog._length_var.set(5)
        app_mock.worker.submit.reset_mock()
        dialog._on_generate()
        app_mock.worker.submit.assert_not_called()
        status = dialog._status_var.get().lower()
        assert "panjang" in status
    finally:
        _cleanup(dialog)


def test_generate_rejects_length_above_maximum(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    try:
        dialog._length_var.set(999)
        app_mock.worker.submit.reset_mock()
        dialog._on_generate()
        app_mock.worker.submit.assert_not_called()
        assert "panjang" in dialog._status_var.get().lower()
    finally:
        _cleanup(dialog)


def test_generate_requires_at_least_one_char_type(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    try:
        dialog._lower_var.set(False)
        dialog._upper_var.set(False)
        dialog._digit_var.set(False)
        dialog._symbol_var.set(False)
        app_mock.worker.submit.reset_mock()
        dialog._on_generate()
        app_mock.worker.submit.assert_not_called()
        assert "jenis karakter" in dialog._status_var.get().lower()
    finally:
        _cleanup(dialog)


# ---------- API call ----------


def test_generate_calls_api(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    try:
        app_mock.worker.submit.reset_mock()
        dialog._on_generate()
        args, _kwargs = app_mock.worker.submit.call_args
        assert args[0] == app_mock.api_client.generate_password
    finally:
        _cleanup(dialog)


def test_generate_passes_options_as_kwargs(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    try:
        dialog._length_var.set(24)
        dialog._symbol_var.set(True)
        dialog._digit_var.set(False)
        app_mock.worker.submit.reset_mock()
        dialog._on_generate()
        _args, kwargs = app_mock.worker.submit.call_args
        assert kwargs["length"] == 24
        assert kwargs["huruf_kecil"] is True
        assert kwargs["huruf_besar"] is True
        assert kwargs["angka"] is False
        assert kwargs["simbol"] is True
        assert "on_result" in kwargs
        assert "on_error" in kwargs
    finally:
        _cleanup(dialog)


# ---------- Result handling ----------


def test_generated_success_shows_result_and_enables_use(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    try:
        dialog._on_generated({"password": "password-palsu-123"})
        assert dialog._result_var.get() == "password-palsu-123"
        assert str(dialog._use_btn.cget("state")) == "normal"
        assert "berhasil" in dialog._status_var.get().lower()
    finally:
        _cleanup(dialog)


def test_generated_invalid_result_shows_status(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    try:
        dialog._on_generated({"not_password": "x"})
        assert dialog._result_var.get() == ""
        assert "valid" in dialog._status_var.get().lower()
    finally:
        _cleanup(dialog)


def test_generated_empty_password_shows_status(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    try:
        dialog._on_generated({"password": ""})
        assert dialog._result_var.get() == ""
        assert "kosong" in dialog._status_var.get().lower()
    finally:
        _cleanup(dialog)


# ---------- Error handling ----------


def test_error_network_shows_friendly_message(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    try:
        dialog._on_error(httpx.ConnectError("connection refused"))
        msg = dialog._status_var.get().lower()
        assert "terhubung" in msg
        assert "connection refused" not in msg
    finally:
        _cleanup(dialog)


def test_error_server_status_shows_status_code(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    try:
        request = httpx.Request("GET", "http://127.0.0.1:8000/alat/password-acak")
        response = httpx.Response(500, request=request)
        error = httpx.HTTPStatusError("err", request=request, response=response)
        dialog._on_error(error)
        assert "500" in dialog._status_var.get()
    finally:
        _cleanup(dialog)


def test_error_401_shows_warning_and_closes(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    request = httpx.Request("GET", "http://127.0.0.1:8000/alat/password-acak")
    response = httpx.Response(401, request=request)
    error = httpx.HTTPStatusError("unauth", request=request, response=response)

    with patch("vaultgui.ui.generator_dialog.messagebox.showwarning") as mock_warn:
        dialog._on_error(error)
        mock_warn.assert_called_once()

    # Dialog should be closed after 401.
    try:
        assert not dialog.winfo_exists()
    except tk.TclError:
        # A destroyed Toplevel might raise on winfo_exists; that also counts
        # as closed.
        pass


# ---------- Use flow ----------


def test_use_without_result_warns_and_keeps_dialog(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    try:
        with patch(
            "vaultgui.ui.generator_dialog.messagebox.showwarning"
        ) as mock_warn:
            dialog._on_use_click()
            mock_warn.assert_called_once()
        assert dialog.winfo_exists()
    finally:
        _cleanup(dialog)


def test_use_with_result_calls_callback_and_closes(app_mock):
    used = []
    dialog = GeneratorDialog(
        app_mock.root, app_mock, on_use=lambda p: used.append(p)
    )
    dialog._result_var.set("password-palsu-123")
    dialog._on_use_click()
    assert used == ["password-palsu-123"]


def test_toggle_show_unmasks_result(app_mock):
    dialog = GeneratorDialog(app_mock.root, app_mock)
    try:
        assert dialog._result_entry.cget("show") == "\u2022"
        dialog._show_var.set(True)
        dialog._toggle_show()
        assert dialog._result_entry.cget("show") == ""
        dialog._show_var.set(False)
        dialog._toggle_show()
        assert dialog._result_entry.cget("show") == "\u2022"
    finally:
        _cleanup(dialog)