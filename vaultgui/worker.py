import threading
import queue
from typing import Callable, Any

class Worker:
    def __init__(self, root):
        self.root = root
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.running = True
        self.worker_thread = threading.Thread(target=self._run, daemon=True)
        self.worker_thread.start()
        self.root.after(50, self._process_results)

    def _run(self):
        while self.running:
            try:
                func, args, kwargs, on_result, on_error = self.task_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                result = func(*args, **kwargs)
                self.result_queue.put(("result", on_result, result))
            except Exception as e:
                self.result_queue.put(("error", on_error, e))

    def submit(self, func: Callable, *args, on_result: Callable = None, on_error: Callable = None, **kwargs):
        self.task_queue.put((func, args, kwargs, on_result, on_error))

    def _process_results(self):
        while True:
            try:
                item = self.result_queue.get_nowait()
            except queue.Empty:
                break
            if item[0] == "result":
                _, callback, result = item
                if callback:
                    self.root.after(0, callback, result)
            elif item[0] == "error":
                _, callback, error = item
                if callback:
                    self.root.after(0, callback, error)
        if self.running:
            self.root.after(50, self._process_results)

    def shutdown(self):
        self.running = False