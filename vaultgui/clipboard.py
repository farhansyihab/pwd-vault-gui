import tkinter as tk

_cleared_token = None

def copy_to_clipboard(text: str, clear_after: int = 30):
    global _cleared_token
    root = tk._default_root
    if not root:
        root = tk.Tk()
        root.withdraw()
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()
    if _cleared_token:
        root.after_cancel(_cleared_token)
    _cleared_token = root.after(clear_after * 1000, lambda: _clear_if_same(root, text))

def _clear_if_same(root, original_text):
    try:
        current = root.clipboard_get()
        if current == original_text:
            root.clipboard_clear()
    except tk.TclError:
        pass