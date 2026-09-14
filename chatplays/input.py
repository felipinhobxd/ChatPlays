import ctypes
from ctypes import wintypes
import sys
import threading
import time


_KEYUP = 0x0002
_SCANCODE = 0x0008
_EXTENDED = 0x0001
_INPUT_MOUSE = 0
_INPUT_KEYBOARD = 1
_MOUSE_MOVE = 0x0001
_MOUSE_FLAGS = {
    "left": (0x0002, 0x0004),
    "right": (0x0008, 0x0010),
    "middle": (0x0020, 0x0040),
}

# DirectInput scan codes adapted from DougDougGithub/TwitchPlays (MIT).
_KEY_CODES: dict[str, tuple[int, bool]] = {
    "esc": (0x01, False),
    "1": (0x02, False), "2": (0x03, False), "3": (0x04, False), "4": (0x05, False),
    "5": (0x06, False), "6": (0x07, False), "7": (0x08, False), "8": (0x09, False),
    "9": (0x0A, False), "0": (0x0B, False),
    "backspace": (0x0E, False), "tab": (0x0F, False),
    "q": (0x10, False), "w": (0x11, False), "e": (0x12, False), "r": (0x13, False),
    "t": (0x14, False), "y": (0x15, False), "u": (0x16, False), "i": (0x17, False),
    "o": (0x18, False), "p": (0x19, False),
    "enter": (0x1C, False), "ctrl": (0x1D, False),
    "a": (0x1E, False), "s": (0x1F, False), "d": (0x20, False), "f": (0x21, False),
    "g": (0x22, False), "h": (0x23, False), "j": (0x24, False), "k": (0x25, False),
    "l": (0x26, False), "shift": (0x2A, False),
    "z": (0x2C, False), "x": (0x2D, False), "c": (0x2E, False), "v": (0x2F, False),
    "b": (0x30, False), "n": (0x31, False), "m": (0x32, False),
    "alt": (0x38, False), "space": (0x39, False),
    "f1": (0x3B, False), "f2": (0x3C, False), "f3": (0x3D, False), "f4": (0x3E, False),
    "f5": (0x3F, False), "f6": (0x40, False), "f7": (0x41, False), "f8": (0x42, False),
    "f9": (0x43, False), "f10": (0x44, False), "f11": (0x57, False), "f12": (0x58, False),
    "up": (0x48, True), "left": (0x4B, True), "right": (0x4D, True), "down": (0x50, True),
    "delete": (0x53, True),
}
_KEY_ALIASES = {
    "control": "ctrl", "leftctrl": "ctrl", "leftcontrol": "ctrl",
    "leftshift": "shift", "leftalt": "alt", "return": "enter", "escape": "esc",
    "arrowup": "up", "arrowdown": "down", "arrowleft": "left", "arrowright": "right",
}

if sys.platform == "win32":
    ULONG_PTR = wintypes.WPARAM

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG), ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR),
        ]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("data", INPUT_UNION)]


class GameInput:
    """Thread-safe Windows SendInput backend with reference-counted holds."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("ChatPlays input requires Windows.")
        self._send_input = ctypes.windll.user32.SendInput
        self._lock = threading.RLock()
        self._held_keys: dict[str, int] = {}
        self._held_mouse: dict[str, int] = {}

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

    def _send(self, packet: "INPUT") -> None:
        if self._send_input(1, ctypes.byref(packet), ctypes.sizeof(INPUT)) != 1:
            raise ctypes.WinError()

    def _send_key(self, key: str, up: bool) -> None:
        scan, extended = _KEY_CODES[key]
        flags = _SCANCODE | (_EXTENDED if extended else 0) | (_KEYUP if up else 0)
        self._send(INPUT(_INPUT_KEYBOARD, INPUT_UNION(ki=KEYBDINPUT(0, scan, flags, 0, 0))))

    def _send_mouse(self, flags: int, dx: int = 0, dy: int = 0) -> None:
        self._send(INPUT(_INPUT_MOUSE, INPUT_UNION(mi=MOUSEINPUT(dx, dy, 0, flags, 0, 0))))

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
        if button not in _MOUSE_FLAGS:
            raise ValueError(f"unsupported mouse button: {button!r}")
        with self._lock:
            count = self._held_mouse.get(button, 0)
            if not count:
                self._send_mouse(_MOUSE_FLAGS[button][0])
            self._held_mouse[button] = count + 1

    def mouse_up(self, button: str) -> None:
        button = button.lower()
        if button not in _MOUSE_FLAGS:
            raise ValueError(f"unsupported mouse button: {button!r}")
        with self._lock:
            count = self._held_mouse.get(button, 0)
            if count <= 1:
                if count:
                    self._send_mouse(_MOUSE_FLAGS[button][1])
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
            self._send_mouse(_MOUSE_MOVE, int(dx), int(dy))

    def release_all(self) -> None:
        with self._lock:
            for key in tuple(self._held_keys):
                self._send_key(key, True)
            for button in tuple(self._held_mouse):
                self._send_mouse(_MOUSE_FLAGS[button][1])
            self._held_keys.clear()
            self._held_mouse.clear()
