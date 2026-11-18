import time

import httpx
import pytest
import tkinter as tk
from unittest.mock import MagicMock, patch

from vaultgui.ui.entries_view import EntriesView
from vaultgui.ui.login_view import LoginView


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


def test_entries_view_loads_data(app_mock):
    entries = [
        {"id": 1, "provider": "google", "username": "me", "email": "me@example.com"}
    ]
    view = EntriesView(None, app_mock)
    view._on_data_loaded(entries)

    children = view.tree.get_children()
    assert len(children) == 1
    values = view.tree.item(children[0])["values"]
    assert str(values[0]) == "1"
    assert values[1] == "google"
    assert values[2] == "me"
    assert values[3] == "me@example.com"


def test_entries_view_empty_without_query_shows_empty_message(app_mock):
    view = EntriesView(None, app_mock)
    view._on_data_loaded([])

    assert view.tree.get_children() == ()
    assert "Belum ada entri" in view.status_var.get()


def test_entries_view_empty_with_query_shows_filter_message(app_mock):
    view = EntriesView(None, app_mock)
    view.search_var.set("tidak-ada")
    view._on_data_loaded([])

    assert "cocok" in view.status_var.get().lower()


def test_entries_view_401_switches_to_login(app_mock):
    request = httpx.Request("GET", "http://127.0.0.1:8000/entri")
    response = httpx.Response(401, request=request)
    error = httpx.HTTPStatusError("unauthorized", request=request, response=response)

    view = EntriesView(None, app_mock)
    with patch("vaultgui.ui.entries_view.messagebox.showwarning") as mock_warn:
        view._on_data_error(error)
        mock_warn.assert_called_once()
        app_mock.switch_view.assert_called_once_with(LoginView)


def test_entries_view_network_error_shows_friendly_message(app_mock):
    error = httpx.ConnectError("connection refused")

    view = EntriesView(None, app_mock)
    view._on_data_error(error)

    msg = view.status_var.get().lower()
    assert "terhubung" in msg
    assert "connection refused" not in msg


def test_entries_view_server_error_shows_status_code(app_mock):
    request = httpx.Request("GET", "http://127.0.0.1:8000/entri")
    response = httpx.Response(500, request=request)
    error = httpx.HTTPStatusError("server error", request=request, response=response)

    view = EntriesView(None, app_mock)
    view._on_data_error(error)

    assert "500" in view.status_var.get()


def test_refresh_passes_query_to_api_client(app_mock):
    view = EntriesView(None, app_mock)
    app_mock.worker.submit.reset_mock()

    view.search_var.set("github")
    view.refresh()

    args, _kwargs = app_mock.worker.submit.call_args
    assert args[0] == app_mock.api_client.get_entries
    assert args[1] == "github"


def test_logout_submits_api_logout(app_mock):
    view = EntriesView(None, app_mock)
    app_mock.worker.submit.reset_mock()

    view._on_logout()

    args, kwargs = app_mock.worker.submit.call_args
    assert args[0] == app_mock.api_client.logout
    assert "on_result" in kwargs
    assert "on_error" in kwargs


def test_search_is_debounced(app_mock):
    view = EntriesView(None, app_mock)
    view.SEARCH_DEBOUNCE_MS = 30
    app_mock.worker.submit.reset_mock()

    view.search_var.set("a")
    view.search_var.set("ab")
    view.search_var.set("abc")

    deadline = time.time() + 2.0
    while time.time() < deadline:
        app_mock.root.update()
        if app_mock.worker.submit.call_count >= 1:
            break
        time.sleep(0.01)

    assert app_mock.worker.submit.call_count == 1
    args, _kwargs = app_mock.worker.submit.call_args
    assert args[1] == "abc"


def test_password_not_shown_in_list(app_mock):
    entries = [
        {
            "id": 1,
            "provider": "google",
            "username": "me",
            "password": "rahasia-palsu-123",
            "email": "me@example.com",
        }
    ]
    view = EntriesView(None, app_mock)
    view._on_data_loaded(entries)

    children = view.tree.get_children()
    assert len(children) == 1
    values = view.tree.item(children[0])["values"]
    for cell in values:
        assert "rahasia-palsu-123" not in str(cell)


# ---------- Tahap 7: tombol Tambah / Ubah / Hapus ----------


def test_add_button_switches_to_entry_form(app_mock):
    view = EntriesView(None, app_mock)
    app_mock.switch_view.reset_mock()

    view._on_add()

    args, _kwargs = app_mock.switch_view.call_args
    assert args[0].__name__ == "EntryForm"


def test_edit_without_selection_shows_warning(app_mock):
    view = EntriesView(None, app_mock)
    app_mock.worker.submit.reset_mock()

    with patch("vaultgui.ui.entries_view.messagebox.showwarning") as mock_warn:
        view._on_edit()
        mock_warn.assert_called_once()

    app_mock.worker.submit.assert_not_called()


def test_edit_with_selection_fetches_entry(app_mock):
    view = EntriesView(None, app_mock)
    view.tree.insert("", tk.END, values=(5, "google", "me", "me@example.com"))
    children = view.tree.get_children()
    view.tree.selection_set(children[0])

    app_mock.worker.submit.reset_mock()
    view._on_edit()

    args, kwargs = app_mock.worker.submit.call_args
    assert args[0] == app_mock.api_client.get_entry
    assert str(args[1]) == "5"
    assert "on_result" in kwargs
    assert "on_error" in kwargs


def test_edit_result_switches_to_entry_form(app_mock):
    view = EntriesView(None, app_mock)
    app_mock.switch_view.reset_mock()

    view._on_entry_loaded_for_edit({"id": 5, "provider": "google", "username": "me"})

    args, kwargs = app_mock.switch_view.call_args
    assert args[0].__name__ == "EntryForm"
    assert kwargs["entry"]["id"] == 5


def test_delete_without_selection_shows_warning(app_mock):
    view = EntriesView(None, app_mock)
    app_mock.worker.submit.reset_mock()

    with patch("vaultgui.ui.entries_view.messagebox.showwarning") as mock_warn:
        view._on_delete()
        mock_warn.assert_called_once()

    app_mock.worker.submit.assert_not_called()


def test_delete_with_selection_asks_confirmation_and_calls_api(app_mock):
    view = EntriesView(None, app_mock)
    view.tree.insert("", tk.END, values=(5, "google", "me", "me@example.com"))
    children = view.tree.get_children()
    view.tree.selection_set(children[0])

    app_mock.worker.submit.reset_mock()
    with patch(
        "vaultgui.ui.entries_view.messagebox.askyesno", return_value=True
    ) as mock_ask:
        view._on_delete()
        mock_ask.assert_called_once()

    args, kwargs = app_mock.worker.submit.call_args
    assert args[0] == app_mock.api_client.delete_entry
    assert str(args[1]) == "5"
    assert "on_result" in kwargs
    assert "on_error" in kwargs


def test_delete_cancelled_does_not_call_api(app_mock):
    view = EntriesView(None, app_mock)
    view.tree.insert("", tk.END, values=(5, "google", "me", "me@example.com"))
    children = view.tree.get_children()
    view.tree.selection_set(children[0])

    app_mock.worker.submit.reset_mock()
    with patch("vaultgui.ui.entries_view.messagebox.askyesno", return_value=False):
        view._on_delete()

    app_mock.worker.submit.assert_not_called()


def test_delete_success_refreshes_list(app_mock):
    view = EntriesView(None, app_mock)
    app_mock.worker.submit.reset_mock()

    view._on_delete_success(None)

    args, _kwargs = app_mock.worker.submit.call_args
    assert args[0] == app_mock.api_client.get_entries


def test_delete_error_uses_specific_status_message(app_mock):
    view = EntriesView(None, app_mock)
    error = httpx.ConnectError("connection refused")
    view._on_delete_error(error)
    assert "menghapus" in view.status_var.get().lower()
    assert "connection refused" not in view.status_var.get()


# ---------- Tahap 8: tampilkan, salin, buka URL ----------


def test_cache_populated_on_load(app_mock):
    entries = [
        {"id": 1, "provider": "google", "username": "me", "url": "https://example.com"},
        {"id": 2, "provider": "github", "username": "me2"},
    ]
    view = EntriesView(None, app_mock)
    view._on_data_loaded(entries)

    assert "1" in view._entries_by_id
    assert "2" in view._entries_by_id
    assert view._entries_by_id["1"]["url"] == "https://example.com"


def test_cache_cleared_on_load(app_mock):
    view = EntriesView(None, app_mock)
    view._on_data_loaded([{"id": 1, "provider": "google"}])
    view._on_data_loaded([{"id": 2, "provider": "github"}])

    assert "1" not in view._entries_by_id
    assert "2" in view._entries_by_id


def test_reveal_password_without_selection_warns(app_mock):
    view = EntriesView(None, app_mock)
    app_mock.worker.submit.reset_mock()

    with patch("vaultgui.ui.entries_view.messagebox.showwarning") as mock_warn:
        view._on_reveal_password()
        mock_warn.assert_called_once()

    app_mock.worker.submit.assert_not_called()


def test_reveal_password_calls_api(app_mock):
    view = EntriesView(None, app_mock)
    view.tree.insert("", tk.END, values=(5, "google", "me", "me@example.com"))
    view.tree.selection_set(view.tree.get_children()[0])

    app_mock.worker.submit.reset_mock()
    view._on_reveal_password()

    args, kwargs = app_mock.worker.submit.call_args
    assert args[0] == app_mock.api_client.get_entry_password
    assert str(args[1]) == "5"
    assert "on_result" in kwargs
    assert "on_error" in kwargs


def test_reveal_password_success_shows_and_schedules_hide(app_mock):
    view = EntriesView(None, app_mock)

    view._on_reveal_success({"id": 5, "password": "rahasia-palsu-123"})

    assert view.password_display_var.get() == "rahasia-palsu-123"
    assert view._hide_password_after_id is not None
    # Cleanup pending timer before fixture teardown.
    view._hide_password()


def test_reveal_password_auto_hide_clears_display(app_mock):
    view = EntriesView(None, app_mock)

    view._on_reveal_success({"id": 5, "password": "rahasia-palsu-123"})
    view._auto_hide_password()

    assert view.password_display_var.get() == ""
    assert view._hide_password_after_id is None


def test_reveal_password_missing_field_clears_display(app_mock):
    view = EntriesView(None, app_mock)

    view._on_reveal_success({})

    assert view.password_display_var.get() == ""
    assert "tidak dapat" in view.status_var.get().lower()


def test_reveal_password_401_switches_to_login(app_mock):
    request = httpx.Request("GET", "http://127.0.0.1:8000/entri/5/password")
    response = httpx.Response(401, request=request)
    error = httpx.HTTPStatusError("unauthorized", request=request, response=response)

    view = EntriesView(None, app_mock)
    with patch("vaultgui.ui.entries_view.messagebox.showwarning") as mock_warn:
        view._on_reveal_error(error)
        mock_warn.assert_called_once()
        app_mock.switch_view.assert_called_once_with(LoginView)


def test_copy_password_without_selection_warns(app_mock):
    view = EntriesView(None, app_mock)
    app_mock.worker.submit.reset_mock()

    with patch("vaultgui.ui.entries_view.messagebox.showwarning") as mock_warn:
        view._on_copy_password()
        mock_warn.assert_called_once()

    app_mock.worker.submit.assert_not_called()


def test_copy_password_calls_api(app_mock):
    view = EntriesView(None, app_mock)
    view.tree.insert("", tk.END, values=(5, "google", "me", "me@example.com"))
    view.tree.selection_set(view.tree.get_children()[0])

    app_mock.worker.submit.reset_mock()
    view._on_copy_password()

    args, kwargs = app_mock.worker.submit.call_args
    assert args[0] == app_mock.api_client.get_entry_password
    assert str(args[1]) == "5"


def test_copy_password_success_calls_clipboard(app_mock):
    view = EntriesView(None, app_mock)

    with patch("vaultgui.ui.entries_view.copy_to_clipboard") as mock_copy:
        view._on_copy_success({"id": 5, "password": "rahasia-palsu-123"})

    mock_copy.assert_called_once()
    called_args, called_kwargs = mock_copy.call_args
    assert called_args[0] == "rahasia-palsu-123"
    # Auto-clear timeout must be passed through.
    assert called_kwargs.get("clear_after") == view.CLIPBOARD_CLEAR_SECONDS


def test_copy_password_missing_field_does_not_call_clipboard(app_mock):
    view = EntriesView(None, app_mock)

    with patch("vaultgui.ui.entries_view.copy_to_clipboard") as mock_copy:
        view._on_copy_success({})

    mock_copy.assert_not_called()
    assert "tidak dapat" in view.status_var.get().lower()


def test_copy_password_401_switches_to_login(app_mock):
    request = httpx.Request("GET", "http://127.0.0.1:8000/entri/5/password")
    response = httpx.Response(401, request=request)
    error = httpx.HTTPStatusError("unauthorized", request=request, response=response)

    view = EntriesView(None, app_mock)
    with patch("vaultgui.ui.entries_view.messagebox.showwarning"):
        view._on_copy_error(error)
        app_mock.switch_view.assert_called_once_with(LoginView)


def test_open_url_without_selection_warns(app_mock):
    view = EntriesView(None, app_mock)

    with patch("vaultgui.ui.entries_view.messagebox.showwarning") as mock_warn:
        view._on_open_url()
        mock_warn.assert_called_once()


def test_open_url_missing_from_cache_shows_status(app_mock):
    view = EntriesView(None, app_mock)
    view.tree.insert("", tk.END, values=(999, "google", "me", "me@example.com"))
    view.tree.selection_set(view.tree.get_children()[0])

    with patch("vaultgui.ui.entries_view.webbrowser.open") as mock_open:
        view._on_open_url()

    mock_open.assert_not_called()
    assert "tidak tersedia" in view.status_var.get().lower()


def test_open_url_empty_url_shows_message(app_mock):
    view = EntriesView(None, app_mock)
    view.tree.insert("", tk.END, values=(5, "google", "me", "me@example.com"))
    view.tree.selection_set(view.tree.get_children()[0])
    view._entries_by_id["5"] = {"id": 5}

    with patch("vaultgui.ui.entries_view.webbrowser.open") as mock_open:
        with patch(
            "vaultgui.ui.entries_view.messagebox.showinfo"
        ) as mock_info:
            view._on_open_url()
            mock_open.assert_not_called()
            mock_info.assert_called_once()


def test_open_url_valid_scheme_opens_browser(app_mock):
    view = EntriesView(None, app_mock)
    view.tree.insert("", tk.END, values=(5, "google", "me", "me@example.com"))
    view.tree.selection_set(view.tree.get_children()[0])
    view._entries_by_id["5"] = {"id": 5, "url": "https://example.com/login"}

    with patch(
        "vaultgui.ui.entries_view.webbrowser.open", return_value=True
    ) as mock_open:
        view._on_open_url()
        mock_open.assert_called_once_with("https://example.com/login")

    assert "dibuka" in view.status_var.get().lower()


def test_open_url_rejects_non_http_scheme(app_mock):
    view = EntriesView(None, app_mock)
    view.tree.insert("", tk.END, values=(5, "google", "me", "me@example.com"))
    view.tree.selection_set(view.tree.get_children()[0])
    view._entries_by_id["5"] = {"id": 5, "url": "javascript:alert(1)"}

    with patch("vaultgui.ui.entries_view.webbrowser.open") as mock_open:
        with patch(
            "vaultgui.ui.entries_view.messagebox.showwarning"
        ) as mock_warn:
            view._on_open_url()
            mock_open.assert_not_called()
            mock_warn.assert_called_once()


def test_open_url_rejects_ftp_scheme(app_mock):
    view = EntriesView(None, app_mock)
    view.tree.insert("", tk.END, values=(5, "google", "me", "me@example.com"))
    view.tree.selection_set(view.tree.get_children()[0])
    view._entries_by_id["5"] = {"id": 5, "url": "ftp://example.com/file"}

    with patch("vaultgui.ui.entries_view.webbrowser.open") as mock_open:
        with patch(
            "vaultgui.ui.entries_view.messagebox.showwarning"
        ):
            view._on_open_url()
            mock_open.assert_not_called()


def test_is_safe_url_static_helper():
    assert EntriesView._is_safe_url("http://example.com") is True
    assert EntriesView._is_safe_url("https://example.com/path") is True
    assert EntriesView._is_safe_url("HTTPS://EXAMPLE.COM") is True
    assert EntriesView._is_safe_url("ftp://example.com") is False
    assert EntriesView._is_safe_url("javascript:alert(1)") is False
    assert EntriesView._is_safe_url("file:///etc/passwd") is False
    assert EntriesView._is_safe_url("") is False
    assert EntriesView._is_safe_url("not-a-url") is False


def test_reveal_password_hidden_when_refresh_triggers(app_mock):
    view = EntriesView(None, app_mock)
    view._on_reveal_success({"id": 5, "password": "rahasia-palsu-123"})
    assert view.password_display_var.get() == "rahasia-palsu-123"

    app_mock.worker.submit.reset_mock()
    view.refresh()

    assert view.password_display_var.get() == ""


def test_destroy_cancels_pending_password_timer(app_mock):
    view = EntriesView(None, app_mock)
    view._on_reveal_success({"id": 5, "password": "rahasia-palsu-123"})
    assert view._hide_password_after_id is not None

    view.destroy()

    assert view._hide_password_after_id is None
