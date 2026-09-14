from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .config import DEFAULT_CONFIG

_PROFILE_KEYS = ("target", "countdown_seconds", "queue", "input", "commands")


def _profile(target_mode: str, command_names: tuple[str, ...]) -> dict[str, Any]:
    commands = {
        name: copy.deepcopy(DEFAULT_CONFIG["commands"][name])
        for name in command_names
    }
    return {
        "target": {
            "mode": target_mode,
            "pid": 0,
            "title": "",
            "process": "",
            "exe": "",
            "emulator_exe": "",
            "rom": "",
        },
        "countdown_seconds": DEFAULT_CONFIG["countdown_seconds"],
        "queue": copy.deepcopy(DEFAULT_CONFIG["queue"]),
        "input": copy.deepcopy(DEFAULT_CONFIG["input"]),
        "commands": commands,
    }


BUILTIN_PROFILES: dict[str, dict[str, Any]] = {
    "Minecraft": _profile(
        "program",
        (
            "forward",
            "backward",
            "strafe_left",
            "strafe_right",
            "jump",
            "click",
            "right_click",
            "look_up",
            "look_down",
            "look_left",
            "look_right",
        ),
    ),
    "Pokémon / Emulador": _profile(
        "emulator",
        ("up", "down", "left", "right", "a", "b", "start", "select"),
    ),
}


class ProfileError(ValueError):
    pass


def profile_path(config_path: str | Path) -> Path:
    return Path(config_path).with_name("profiles.json")


def profile_from_config(config: dict[str, Any]) -> dict[str, Any]:
    """Copy only game-specific settings. Stream connection data is intentionally excluded."""
    return {
        key: copy.deepcopy(config[key])
        for key in _PROFILE_KEYS
        if key in config
    }


def apply_profile(config: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Return config with game settings replaced while preserving stream connection data."""
    merged = copy.deepcopy(config)
    for key in _PROFILE_KEYS:
        if key in profile:
            merged[key] = copy.deepcopy(profile[key])
    return merged


def load_profiles(path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(path)
    user_profiles: dict[str, dict[str, Any]] = {}
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProfileError(f"JSON inválido em {path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise ProfileError("profiles.json precisa conter um objeto JSON.")
        source = raw.get("profiles", raw)
        if not isinstance(source, dict):
            raise ProfileError("profiles precisa ser um objeto.")
        for name, profile in source.items():
            if isinstance(name, str) and name.strip() and isinstance(profile, dict):
                user_profiles[name.strip()] = copy.deepcopy(profile)

    profiles = copy.deepcopy(BUILTIN_PROFILES)
    profiles.update(user_profiles)
    return profiles


def save_profiles(path: str | Path, profiles: dict[str, dict[str, Any]]) -> Path:
    """Persist only user/customized profiles atomically."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    payload = json.dumps({"version": 1, "profiles": profiles}, ensure_ascii=False, indent=2) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def load_user_profiles(path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProfileError(f"JSON inválido em {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ProfileError("profiles.json precisa conter um objeto JSON.")
    source = raw.get("profiles", raw)
    if not isinstance(source, dict):
        raise ProfileError("profiles precisa ser um objeto.")
    return {
        str(name).strip(): copy.deepcopy(profile)
        for name, profile in source.items()
        if str(name).strip() and isinstance(profile, dict)
    }
