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