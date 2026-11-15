"""Tiny in-memory login throttle (per process). Adequate for a single-instance demo."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

_LOCK = threading.Lock()
_FAILURES: dict[str, deque] = defaultdict(deque)
MAX_FAILURES = 8
WINDOW_SECONDS = 600


def is_blocked(key: str) -> bool:
    now = time.monotonic()
    with _LOCK:
        q = _FAILURES[key]
        while q and now - q[0] > WINDOW_SECONDS:
            q.popleft()
        return len(q) >= MAX_FAILURES


def record_failure(key: str) -> None:
    with _LOCK:
        _FAILURES[key].append(time.monotonic())


def reset(key: str) -> None:
    with _LOCK:
        _FAILURES.pop(key, None)
