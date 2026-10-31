"""Simple in-memory limit on AI calls, so a public demo cannot use up the API quota."""
import threading
import time
from collections import deque


class RateLimiter:
    def __init__(self, max_calls, period_seconds=60):
        self.max_calls = max_calls  # 0 or less means no limit
        self.period_seconds = period_seconds
        self._calls = deque()
        self._lock = threading.Lock()

    def allow(self):
        """Record a call and return True, or return False if the limit has been reached."""
        if self.max_calls <= 0:
            return True

        now = time.monotonic()
        with self._lock:
            # Forget calls that are older than the time window
            while self._calls and now - self._calls[0] >= self.period_seconds:
                self._calls.popleft()
            if len(self._calls) >= self.max_calls:
                return False
            self._calls.append(now)
            return True
