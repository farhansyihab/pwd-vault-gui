import tkinter as tk

import pytest

from vaultgui import clipboard


@pytest.fixture
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


def test_copy_stores_value_in_clipboard(tk_root):
    clipboard.copy_to_clipboard("rahasia-palsu-123", clear_after=60)
    tk_root.update()
    assert tk_root.clipboard_get() == "rahasia-palsu-123"


def test_clear_if_same_clears_when_unchanged(tk_root):
    tk_root.clipboard_clear()
    tk_root.clipboard_append("rahasia-palsu-123")
    tk_root.update()
    clipboard._clear_if_same(tk_root, "rahasia-palsu-123")
    try:
        current = tk_root.clipboard_get()
    except tk.TclError:
        current = ""
    assert current == ""


def test_clear_if_same_keeps_when_different(tk_root):
    tk_root.clipboard_clear()
    tk_root.clipboard_append("nilai-lain")
    tk_root.update()
    clipboard._clear_if_same(tk_root, "rahasia-palsu-123")
    assert tk_root.clipboard_get() == "nilai-lain"


def test_clear_if_same_handles_empty_clipboard(tk_root):
    tk_root.clipboard_clear()
    tk_root.update()
    # Should not raise even when clipboard is empty.
    clipboard._clear_if_same(tk_root, "rahasia-palsu-123")


def test_copy_replaces_value_and_updates_timer(tk_root):
    clipboard.copy_to_clipboard("first-palsu", clear_after=60)
    tk_root.update()
    clipboard.copy_to_clipboard("second-palsu", clear_after=60)
    tk_root.update()
    assert tk_root.clipboard_get() == "second-palsu"
    assert clipboard._cleared_token is not None