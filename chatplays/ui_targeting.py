from __future__ import annotations

from typing import Any

from .target import WindowInfo, target_score


def choose_target_window(
    windows: list[WindowInfo],
    saved_target: dict[str, Any] | None,
    selected_window: WindowInfo | None = None,
) -> WindowInfo | None:
    """Choose one unambiguous window for the desktop UI.

    Prefer the exact window the user already selected. Otherwise reuse the
    saved target identity. If multiple windows tie for the best match, return
    None so the UI asks the user instead of silently choosing the wrong game.
    """
    if selected_window is not None:
        for window in windows:
            if window.hwnd == selected_window.hwnd and window.pid == selected_window.pid:
                return window

    target = dict(saved_target or {})
    preferred_pid = int(target.get("pid") or 0)
    scored = [(target_score(window, target, preferred_pid), window) for window in windows]
    best_score = max((score for score, _window in scored), default=0)
    if best_score <= 0:
        return None

    matches = [window for score, window in scored if score == best_score]
    if len(matches) != 1:
        return None
    return matches[0]
