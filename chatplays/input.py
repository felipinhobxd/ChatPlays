import ctypes
import sys
import threading
import time
from collections.abc import Callable
from ctypes import wintypes
from typing import Any

from .target import TargetResolver

_WM_KEYDOWN = 0x0100
_WM_KEYUP = 0x0101
_WM_MOUSEMOVE = 0x0200
_WM_LBUTTONDOWN = 0x0201
_WM_LBUTTONUP = 0x0202
_WM_RBUTTONDOWN = 0x0204
_WM_RBUTTONUP = 0x0205
_WM_MBUTTONDOWN = 0x0207
_WM_MBUTTONUP = 0x0208
_MK_LBUTTON = 0x0001
_MK_RBUTTON = 0x0002
_MK_MBUTTON = 0x0010

_KEY_CODES: dict[str, tuple[int, bool]] = {
    "backspace": (0x08, False),
    "tab": (0x09, False),
    "enter": (0x0D, False),
    "shift": (0x10, False),
    "ctrl": (0x11, False),
    "alt": (0x12, False),
    "esc": (0x1B, False),
    "space": (0x20, False),
    "left": (0x25, True),
    "up": (0x26, True),
    "right": (0x27, True),
    "down": (0x28, True),
    "delete": (0x2E, True),
    **{str(number): (0x30 + number, False) for number in range(10)},
    **{chr(97 + index): (0x41 + index, False) for index in range(26)},
    **{f"f{index}": (0x6F + index, False) for index in range(1, 13)},
}
_KEY_ALIASES = {
    "control": "ctrl",
    "leftctrl": "ctrl",
    "leftcontrol": "ctrl",
    "leftshift": "shift",
    "leftalt": "alt",
    "return": "enter",
    "escape": "esc",
    "arrowup": "up",
    "arrowdown": "down",
    "arrowleft": "left",
    "arrowright": "right",
}
_MOUSE_MESSAGES = {
    "left": (_WM_LBUTTONDOWN, _WM_LBUTTONUP, _MK_LBUTTON),
    "right": (_WM_RBUTTONDOWN, _WM_RBUTTONUP, _MK_RBUTTON),
    "middle": (_WM_MBUTTONDOWN, _WM_MBUTTONUP, _MK_MBUTTON),
}


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class GameInput:
    """Keyboard/mouse backend that only posts messages to the chosen game window."""

    def __init__(
        self,
        target: dict[str, Any] | None = None,
        logger: Callable[[str], None] = print,
    ) -> None:
        if sys.platform != "win32":
            raise RuntimeError("ChatPlays input requires Windows.")
        self._user32 = ctypes.windll.user32
        self._user32.PostMessageW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        self._user32.PostMessageW.restype = wintypes.BOOL
        self._user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
        self._user32.MapVirtualKeyW.restype = wintypes.UINT
        self._user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
        self._user32.GetClientRect.restype = wintypes.BOOL
        self.target = TargetResolver(target or {}, logger=logger)
        self._lock = threading.RLock()
        self._held_keys: dict[str, int] = {}
        self._held_mouse: dict[str, int] = {}
        self._mouse_x: int | None = None
        self._mouse_y: int | None = None

    def prepare(self) -> None:
        self.target.prepare()

    @staticmethod
    def _combo_keys(combo: str) -> list[str]:
        keys = []
        for raw in combo.lower().replace(" ", "").split("+"):
            key = _KEY_ALIASES.get(raw, raw)
            if key not in _KEY_CODES:
                raise ValueError(f"unsupported key: {raw!r}")
            keys.append(key)
        if not keys:
            raise ValueError("empty key combo")
        return keys

    def _hwnd(self) -> int:
        return self.target.hwnd()

    def _post(self, hwnd: int, message: int, wparam: int, lparam: int) -> None:
        if not self._user32.PostMessageW(hwnd, message, wparam, lparam):
            raise ctypes.WinError()

    def _send_key(self, key: str, up: bool) -> None:
        hwnd = self._hwnd()
        vk, extended = _KEY_CODES[key]
        scan = int(self._user32.MapVirtualKeyW(vk, 0)) & 0xFF
        lparam = 1 | (scan << 16)
        if extended:
            lparam |= 1 << 24
        if up:
            lparam |= (1 << 30) | (1 << 31)
        self._post(hwnd, _WM_KEYUP if up else _WM_KEYDOWN, vk, lparam)

    def _client_size(self, hwnd: int) -> tuple[int, int]:
        rect = RECT()
        if not self._user32.GetClientRect(hwnd, ctypes.byref(rect)):
            raise ctypes.WinError()
        return max(1, rect.right - rect.left), max(1, rect.bottom - rect.top)

    @staticmethod
    def _pack_point(x: int, y: int) -> int:
        return ((y & 0xFFFF) << 16) | (x & 0xFFFF)

    def _mouse_point(self, hwnd: int) -> tuple[int, int]:
        width, height = self._client_size(hwnd)
        if self._mouse_x is None or self._mouse_y is None:
            self._mouse_x, self._mouse_y = width // 2, height // 2
        self._mouse_x = min(max(0, self._mouse_x), width - 1)
        self._mouse_y = min(max(0, self._mouse_y), height - 1)
        return self._mouse_x, self._mouse_y

    def key_down(self, combo: str) -> None:
        with self._lock:
            for key in self._combo_keys(combo):
                count = self._held_keys.get(key, 0)
                if not count:
                    self._send_key(key, False)
                self._held_keys[key] = count + 1

    def key_up(self, combo: str) -> None:
        with self._lock:
            for key in reversed(self._combo_keys(combo)):
                count = self._held_keys.get(key, 0)
                if count <= 1:
                    if count:
                        self._send_key(key, True)
                    self._held_keys.pop(key, None)
                else:
                    self._held_keys[key] = count - 1

    def press_key(self, combo: str, seconds: float) -> None:
        self.key_down(combo)
        try:
            time.sleep(seconds)
        finally:
            self.key_up(combo)

    def mouse_down(self, button: str) -> None:
        button = button.lower()
        if button not in _MOUSE_MESSAGES:
            raise ValueError(f"unsupported mouse button: {button!r}")
        with self._lock:
            count = self._held_mouse.get(button, 0)
            if not count:
                hwnd = self._hwnd()
                x, y = self._mouse_point(hwnd)
                down, _up, mask = _MOUSE_MESSAGES[button]
                self._post(hwnd, down, mask, self._pack_point(x, y))
            self._held_mouse[button] = count + 1

    def mouse_up(self, button: str) -> None:
        button = button.lower()
        if button not in _MOUSE_MESSAGES:
            raise ValueError(f"unsupported mouse button: {button!r}")
        with self._lock:
            count = self._held_mouse.get(button, 0)
            if count <= 1:
                if count:
                    hwnd = self._hwnd()
                    x, y = self._mouse_point(hwnd)
                    _down, up, _mask = _MOUSE_MESSAGES[button]
                    self._post(hwnd, up, 0, self._pack_point(x, y))
                self._held_mouse.pop(button, None)
            else:
                self._held_mouse[button] = count - 1

    def click(self, button: str, seconds: float = 0.05) -> None:
        self.mouse_down(button)
        try:
            time.sleep(seconds)
        finally:
            self.mouse_up(button)

    def move_relative(self, dx: int, dy: int) -> None:
        with self._lock:
            hwnd = self._hwnd()
            width, height = self._client_size(hwnd)
            x, y = self._mouse_point(hwnd)
            self._mouse_x = min(max(0, x + int(dx)), width - 1)
            self._mouse_y = min(max(0, y + int(dy)), height - 1)
            self._post(
                hwnd,
                _WM_MOUSEMOVE,
                0,
                self._pack_point(self._mouse_x, self._mouse_y),
            )

    def release_all(self) -> None:
        with self._lock:
            for key in tuple(self._held_keys):
                try:
                    self._send_key(key, True)
                except (OSError, RuntimeError):
                    pass
            for button in tuple(self._held_mouse):
                try:
                    hwnd = self._hwnd()
                    x, y = self._mouse_point(hwnd)
                    _down, up, _mask = _MOUSE_MESSAGES[button]
                    self._post(hwnd, up, 0, self._pack_point(x, y))
                except (OSError, RuntimeError):
                    pass
            self._held_keys.clear()
            self._held_mouse.clear()
