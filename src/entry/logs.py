"""进程内日志总线。转写进度推给网页，不阻塞主路径。"""

from __future__ import annotations

import threading
from collections import deque
from queue import Full, Queue

RECENT_LIMIT = 40


class LogBus:
    def __init__(self) -> None:
        self._subs: list[Queue] = []
        self._recent: deque[dict] = deque(maxlen=RECENT_LIMIT)
        self._lock = threading.Lock()

    def subscribe(self) -> tuple[Queue, list[dict]]:
        queue: Queue = Queue(maxsize=64)
        with self._lock:
            self._subs.append(queue)
            history = list(self._recent)
        return queue, history

    def unsubscribe(self, queue: Queue) -> None:
        with self._lock:
            if queue in self._subs:
                self._subs.remove(queue)

    def emit(self, payload: dict) -> None:
        with self._lock:
            self._recent.append(payload)
            subscribers = list(self._subs)
        for queue in subscribers:
            try:
                queue.put_nowait(payload)
            except Full:
                continue
