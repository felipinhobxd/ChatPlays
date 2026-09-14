from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    from ctypes import wintypes

    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    _user32.IsWindowVisible.argtypes = [wintypes.HWND]
    _user32.IsWindowVisible.restype = wintypes.BOOL
    _user32.IsWindow.argtypes = [wintypes.HWND]
    _user32.IsWindow.restype = wintypes.BOOL
    _user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    _user32.GetWindowTextLengthW.restype = ctypes.c_int
    _user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _user32.GetWindowTextW.restype = ctypes.c_int
    _user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    _user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    _kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    _kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL


@dataclass(frozen=True, slots=True)
class WindowInfo:
    hwnd: int
    pid: int
    title: str
    process: str
    exe: str

    @property
    def label(self) -> str:
        return f"{self.title} — {self.process or 'processo'} — PID {self.pid}"


def normalize_path(value: str | os.PathLike[str] | None) -> str:
    text = str(value or "").strip().strip('"').strip("'")
    if not text:
        return ""
    try:
        return str(Path(text).expanduser().resolve(strict=False))
    except (OSError, RuntimeError):
        return text


def process_name(path: str) -> str:
    return Path(path).name if path else ""


def _query_process_path(pid: int) -> str:
    if sys.platform != "win32" or pid <= 0:
        return ""
    handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not _kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return ""
        return buffer.value
    finally:
        _kernel32.CloseHandle(handle)


def list_open_windows() -> list[WindowInfo]:
    """Return visible top-level windows with PID and executable path."""
    if sys.platform != "win32":
        return []

    results: list[WindowInfo] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def collect(hwnd: int, _lparam: int) -> bool:
        if not _user32.IsWindowVisible(hwnd):
            return True
        length = _user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        _user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title:
            return True

        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value or pid.value == os.getpid():
            return True
        exe = _query_process_path(int(pid.value))
        results.append(
            WindowInfo(
                hwnd=int(hwnd),
                pid=int(pid.value),
                title=title,
                process=process_name(exe),
                exe=exe,
            )
        )
        return True

    callback = callback_type(collect)
    _user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    _user32.EnumWindows.restype = wintypes.BOOL
    _user32.EnumWindows(callback, 0)
    results.sort(key=lambda item: (item.process.lower(), item.title.lower(), item.pid))
    return results


def _same_path(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return os.path.normcase(normalize_path(left)) == os.path.normcase(normalize_path(right))


def target_score(window: WindowInfo, target: dict[str, Any], preferred_pid: int = 0) -> int:
    score = 0
    pid = int(target.get("pid") or 0)
    exe = normalize_path(target.get("exe"))
    title = str(target.get("title") or "").strip().lower()
    process = str(target.get("process") or "").strip().lower()

    path_matches = bool(exe and _same_path(window.exe, exe))
    process_matches = bool(process and window.process.lower() == process)
    identity_compatible = not exe or not window.exe or path_matches
    identity_compatible = identity_compatible and (not process or process_matches)

    if preferred_pid and window.pid == preferred_pid and identity_compatible:
        score += 100
    if pid and window.pid == pid and identity_compatible:
        score += 80
    if path_matches:
        score += 50
    if process_matches:
        score += 20
    if title:
        actual = window.title.lower()
        if actual == title:
            score += 30
        elif title in actual or actual in title:
            score += 15
    return score


def best_window(
    windows: list[WindowInfo], target: dict[str, Any], preferred_pid: int = 0
) -> WindowInfo | None:
    ranked = [(target_score(window, target, preferred_pid), window) for window in windows]
    ranked = [(score, window) for score, window in ranked if score > 0]
    if not ranked:
        return None
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return ranked[0][1]


class TargetResolver:
    """Resolve one explicit game window; never fall back to foreground input."""

    def __init__(self, config: dict[str, Any], logger: Callable[[str], None] = print) -> None:
        self.config = dict(config or {})
        self.log = logger
        self.mode = str(self.config.get("mode") or "program").strip().lower()
        self._preferred_pid = int(self.config.get("pid") or 0)
        self._cached: WindowInfo | None = None
        self._launched: subprocess.Popen[bytes] | None = None

    def validate(self) -> None:
        if self.mode not in {"program", "emulator"}:
            raise ValueError("Modo de alvo inválido. Escolha Programa aberto ou Emulador + ROM.")
        if self.mode == "program":
            if not any(
                (
                    int(self.config.get("pid") or 0),
                    normalize_path(self.config.get("exe")),
                    str(self.config.get("title") or "").strip(),
                )
            ):
                raise ValueError("Selecione um programa/jogo aberto antes de iniciar.")
            return

        exe = Path(normalize_path(self.config.get("emulator_exe")))
        rom = Path(normalize_path(self.config.get("rom")))
        if not exe.is_file():
            raise ValueError(f"Emulador não encontrado: {exe}")
        if not rom.is_file():
            raise ValueError(f"ROM não encontrada: {rom}")

    def prepare(self, timeout: float = 12.0) -> WindowInfo:
        self.validate()
        if self.mode == "emulator":
            emulator = normalize_path(self.config.get("emulator_exe"))
            rom = normalize_path(self.config.get("rom"))
            self.log(f"[Alvo] Abrindo {Path(emulator).name} com {Path(rom).name}")
            self._launched = subprocess.Popen([emulator, rom], cwd=str(Path(emulator).parent))
            self._preferred_pid = int(self._launched.pid)
            self.config["exe"] = emulator
            self.config["process"] = Path(emulator).name

        deadline = time.monotonic() + max(0.1, timeout)
        while time.monotonic() < deadline:
            found = self.resolve()
            if found:
                self.log(f"[Alvo] {found.title} ({found.process}, PID {found.pid})")
                return found
            time.sleep(0.15)
        raise RuntimeError("A janela selecionada não foi encontrada/aberta.")

    def resolve(self) -> WindowInfo | None:
        if self._cached and self._is_window(self._cached.hwnd):
            return self._cached
        windows = list_open_windows()
        target = dict(self.config)
        if self.mode == "emulator":
            target["exe"] = normalize_path(self.config.get("emulator_exe"))
            target["process"] = Path(target["exe"]).name if target["exe"] else ""
        self._cached = best_window(windows, target, self._preferred_pid)
        return self._cached

    def hwnd(self) -> int:
        found = self.resolve()
        if not found:
            raise RuntimeError("A janela alvo não está aberta. Nenhuma tecla foi enviada ao PC.")
        return found.hwnd

    @staticmethod
    def _is_window(hwnd: int) -> bool:
        return bool(sys.platform == "win32" and hwnd and _user32.IsWindow(hwnd))
