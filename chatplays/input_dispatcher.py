from __future__ import annotations

import heapq
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import count
from threading import Condition, Event, Thread

from .commands import ParsedAction

ActionExecutor = Callable[[ParsedAction, Event], None]


@dataclass(order=True, slots=True)
class _QueuedAction:
    priority: int
    sequence: int
    action: ParsedAction = field(compare=False)


class InputDispatcher:
    """Serialize game input while allowing emergency release to preempt queued work."""

    NORMAL_PRIORITY = 10
    RELEASE_PRIORITY = 0

    def __init__(self, execute: ActionExecutor) -> None:
        self._execute = execute
        self._condition = Condition()
        self._items: list[_QueuedAction] = []
        self._sequence = count()
        self._closed = False
        self._active = False
        self._current_cancel: Event | None = None
        self._worker = Thread(target=self._run, name="ChatPlaysInput", daemon=False)
        self._worker.start()

    def submit(self, action: ParsedAction) -> bool:
        """Queue one action in arrival order.

        `release_all` is intentionally special: it interrupts a timed action,
        drops older pending input, then runs before any command submitted later.
        """
        with self._condition:
            if self._closed:
                return False

            if action.release_all:
                if self._current_cancel:
                    self._current_cancel.set()
                self._items.clear()
                priority = self.RELEASE_PRIORITY
            else:
                priority = self.NORMAL_PRIORITY

            heapq.heappush(
                self._items,
                _QueuedAction(priority, next(self._sequence), action),
            )
            self._condition.notify()
            return True

    def shutdown(self) -> None:
        """Stop accepting work, cancel current timed input and discard pending actions."""
        with self._condition:
            if not self._closed:
                self._closed = True
                self._items.clear()
                if self._current_cancel:
                    self._current_cancel.set()
                self._condition.notify_all()
        if self._worker.is_alive():
            self._worker.join()

    def wait_idle(self, timeout: float = 1.0) -> bool:
        """Wait until no action is running or queued. Primarily useful for tests."""
        deadline = time.monotonic() + max(0.0, timeout)
        with self._condition:
            while self._active or self._items:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return True

    def _run(self) -> None:
        while True:
            with self._condition:
                while not self._items and not self._closed:
                    self._condition.wait()
                if self._closed:
                    self._active = False
                    self._condition.notify_all()
                    return

                queued = heapq.heappop(self._items)
                cancel_event = Event()
                self._current_cancel = cancel_event
                self._active = True

            try:
                self._execute(queued.action, cancel_event)
            finally:
                with self._condition:
                    if self._current_cancel is cancel_event:
                        self._current_cancel = None
                    self._active = False
                    self._condition.notify_all()
