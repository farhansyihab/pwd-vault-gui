import pytest
import tkinter as tk
from unittest.mock import patch, MagicMock
from vaultgui.ui.login_view import LoginView
from vaultgui.api_client import AuthError, RateLimitError

@pytest.fixture
def app_mock():
    root = tk.Tk()
    root.withdraw()
    app = MagicMock()
    app.worker = MagicMock()
    app.api_client = MagicMock()
    yield app
    root.destroy()

def test_login_view_shows_error_on_empty_fields(app_mock):
    view = LoginView(None, app_mock)
    view.username_var.set("")
    view.password_var.set("")
    view._on_login()
    assert view.error_var.get() == "Username dan password wajib diisi"
    app_mock.worker.submit.assert_not_called()

def test_login_view_calls_worker_on_valid_input(app_mock):
    view = LoginView(None, app_mock)
    view.username_var.set("user")
    view.password_var.set("pass")
    view._on_login()
    app_mock.worker.submit.assert_called_once()
    args, kwargs = app_mock.worker.submit.call_args
    assert args[0] == app_mock.api_client.login
    assert args[1] == "user"
    assert args[2] == "pass"

def test_login_success_switches_view(app_mock):
    from vaultgui.ui.entries_view import EntriesView
    view = LoginView(None, app_mock)
    view._on_login_success({})
    app_mock.switch_view.assert_called_once_with(EntriesView)

def test_login_auth_error_shows_message(app_mock):
    view = LoginView(None, app_mock)
    view._on_login_error(AuthError("bad"))
    assert view.error_var.get() == "Username atau password salah"

def test_login_rate_limit_shows_message(app_mock):
    view = LoginView(None, app_mock)
    view._on_login_error(RateLimitError("locked"))
    assert view.error_var.get() == "Terlalu banyak percobaan. Coba lagi 5 menit."