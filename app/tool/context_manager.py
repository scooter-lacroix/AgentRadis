from typing import Any
import threading

class GlobalContextManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(GlobalContextManager, cls).__new__(cls)
                    cls._instance.context = {}
        return cls._instance

    def update_context(self, key: str, value: Any):
        self.context[key] = value

    def get_context(self, key: str) -> Any:
        return self.context.get(key, None)

    def clear_context(self):
        self.context.clear() 