import threading


class GraphState:
    def __init__(self):
        self._generation = 0
        self._lock = threading.Lock()

    def mark_dirty(self) -> None:
        with self._lock:
            self._generation += 1

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation


graph_state = GraphState()
