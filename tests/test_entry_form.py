import tkinter as tk
from unittest.mock import MagicMock

import httpx
import pytest

from vaultgui.ui.entry_form import EntryForm


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


def _make_http_error(method, url, status, json_body=None):
    request = httpx.Request(method, url)
    response = httpx.Response(status, json=json_body, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


def test_add_mode_shows_title(app_mock):
    view = EntryForm(None, app_mock)
    assert view.is_edit is False
    for name in EntryForm.FIELD_NAMES:
        assert name in view._vars


def test_edit_mode_shows_title_and_prefills_fields(app_mock):
    entry = {
        "id": 5,
        "provider": "google",
        "username": "me",
        "email": "me@example.com",
        "url": "https://example.com",
        "keterangan": "personal",
    }
    view = EntryForm(None, app_mock, entry=entry)
    assert view.is_edit is True
    assert view._vars["provider"].get() == "google"
    assert view._vars["username"].get() == "me"
    assert view._vars["email"].get() == "me@example.com"
    assert view._vars["url"].get() == "https://example.com"
    assert view._vars["keterangan"].get() == "personal"
    assert view._vars["password"].get() == ""


def test_add_mode_validation_requires_provider(app_mock):
    view = EntryForm(None, app_mock)
    app_mock.worker.submit.reset_mock()
    view._vars["username"].set("me")
    view._vars["password"].set("pass")
    view._on_save()
    assert "provider" in view.error_var.get().lower()
    app_mock.worker.submit.assert_not_called()


def test_add_mode_validation_requires_username(app_mock):
    view = EntryForm(None, app_mock)
    app_mock.worker.submit.reset_mock()
    view._vars["provider"].set("google")
    view._vars["password"].set("pass")
    view._on_save()
    assert "username" in view.error_var.get().lower()
    app_mock.worker.submit.assert_not_called()


def test_add_mode_validation_requires_password(app_mock):
    view = EntryForm(None, app_mock)
    app_mock.worker.submit.reset_mock()
    view._vars["provider"].set("google")
    view._vars["username"].set("me")
    view._on_save()
    assert "password" in view.error_var.get().lower()
    app_mock.worker.submit.assert_not_called()


def test_add_mode_submits_create_entry(app_mock):
    view = EntryForm(None, app_mock)
    app_mock.worker.submit.reset_mock()
    view._vars["provider"].set("google")
    view._vars["username"].set("me")
    view._vars["password"].set("password-palsu-123")
    view._vars["email"].set("me@example.com")
    view._on_save()

    args, _kwargs = app_mock.worker.submit.call_args
    assert args[0] == app_mock.api_client.create_entry
    payload = args[1]
    assert payload["provider"] == "google"
    assert payload["username"] == "me"
    assert payload["password"] == "password-palsu-123"
    assert payload["email"] == "me@example.com"


def test_edit_mode_with_new_password_submits_update(app_mock):
    entry = {"id": 5, "provider": "google", "username": "me"}
    view = EntryForm(None, app_mock, entry=entry)
    app_mock.worker.submit.reset_mock()
    view._vars["password"].set("new-password-palsu")
    view._on_save()

    args, _kwargs = app_mock.worker.submit.call_args
    assert args[0] == app_mock.api_client.update_entry
    assert args[1] == 5
    assert args[2]["password"] == "new-password-palsu"


def test_edit_mode_without_password_fetches_old_password(app_mock):
    entry = {"id": 5, "provider": "google", "username": "me"}
    view = EntryForm(None, app_mock, entry=entry)
    app_mock.worker.submit.reset_mock()
    view._on_save()

    args, kwargs = app_mock.worker.submit.call_args
    assert args[0] == app_mock.api_client.get_entry_password
    assert args[1] == 5
    assert "on_result" in kwargs
    assert "on_error" in kwargs

    app_mock.worker.submit.reset_mock()
    kwargs["on_result"]({"id": 5, "password": "old-secret-palsu"})

    args, _kwargs = app_mock.worker.submit.call_args
    assert args[0] == app_mock.api_client.update_entry
    assert args[1] == 5
    assert args[2]["password"] == "old-secret-palsu"


def test_edit_mode_old_password_missing_shows_error(app_mock):
    entry = {"id": 5, "provider": "google", "username": "me"}
    view = EntryForm(None, app_mock, entry=entry)
    app_mock.worker.submit.reset_mock()
    view._on_save()

    _args, kwargs = app_mock.worker.submit.call_args
    app_mock.worker.submit.reset_mock()
    kwargs["on_result"]({})

    app_mock.worker.submit.assert_not_called()
    assert "password lama" in view.error_var.get().lower()


def test_save_success_switches_to_entries_view(app_mock):
    view = EntryForm(None, app_mock)
    view._on_save_success({})
    args, _kwargs = app_mock.switch_view.call_args
    assert args[0].__name__ == "EntriesView"


def test_cancel_switches_to_entries_view(app_mock):
    view = EntryForm(None, app_mock)
    view._on_cancel()
    args, _kwargs = app_mock.switch_view.call_args
    assert args[0].__name__ == "EntriesView"


def test_save_401_switches_to_login(app_mock):
    view = EntryForm(None, app_mock)
    error = _make_http_error("POST", "http://127.0.0.1:8000/entri", 401)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "vaultgui.ui.entry_form.messagebox.showwarning",
            lambda *a, **k: None,
        )
        view._on_save_error(error)
    args, _kwargs = app_mock.switch_view.call_args
    assert args[0].__name__ == "LoginView"


def test_save_422_shows_validation_details(app_mock):
    view = EntryForm(None, app_mock)
    error = _make_http_error(
        "POST",
        "http://127.0.0.1:8000/entri",
        422,
        json_body={"detail": [{"loc": ["body", "provider"], "msg": "required"}]},
    )
    view._on_save_error(error)
    msg = view.error_var.get().lower()
    assert "provider" in msg
    assert "required" in msg


def test_save_network_error_shows_friendly_message(app_mock):
    view = EntryForm(None, app_mock)
    view._on_save_error(httpx.ConnectError("connection refused"))
    msg = view.error_var.get().lower()
    assert "terhubung" in msg
    assert "connection refused" not in msg


# ---------- Tahap 9: integrasi dengan generator password ----------


def test_open_generator_creates_dialog(app_mock):
    view = EntryForm(None, app_mock)
    with pytest.MonkeyPatch.context() as mp:
        mock_dialog = MagicMock()
        mp.setattr(
            "vaultgui.ui.generator_dialog.GeneratorDialog", mock_dialog
        )
        view._open_generator()
        mock_dialog.assert_called_once()
        _args, kwargs = mock_dialog.call_args
        assert "on_use" in kwargs
        assert callable(kwargs["on_use"])


def test_apply_generated_password_sets_field(app_mock):
    view = EntryForm(None, app_mock)
    view._apply_generated_password("password-palsu-123")
    assert view._vars["password"].get() == "password-palsu-123"


def test_generator_callback_does_not_touch_other_fields(app_mock):
    view = EntryForm(None, app_mock)
    view._vars["provider"].set("google")
    view._vars["username"].set("me")
    view._apply_generated_password("password-palsu-123")
    assert view._vars["provider"].get() == "google"
    assert view._vars["username"].get() == "me"
    assert view._vars["password"].get() == "password-palsu-123"