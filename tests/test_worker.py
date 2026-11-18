import pytest
import queue
import tkinter as tk
from vaultgui.worker import Worker

def test_worker_submits_and_receives():
    root = tk.Tk()
    root.withdraw()
    
    worker = Worker(root)
    result_queue = queue.Queue()
    
    def task():
        return "done"
    
    def on_result(result):
        result_queue.put(result)
    
    worker.submit(task, on_result=on_result)
    
    root.after(1000, root.quit)
    root.mainloop()
    
    assert result_queue.get(timeout=2) == "done"
    worker.shutdown()
    worker.worker_thread.join(timeout=1)
    root.destroy()