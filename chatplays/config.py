import copy
import json
from pathlib import Path
from typing import Any

from .validation import validate_runtime_config


class ConfigError(ValueError):
    pass


DEFAULT_CONFIG: dict[str, Any] = {
    "stream": {
        "twitch_channel": "",
        "youtube_channel_id": "",
        "youtube_stream_url": "",
    },
    "target": {
        "mode": "program",
        "pid": 0,
        "title": "",
        "process": "",
        "exe": "",
        "emulator_exe": "",
        "rom": "",
    },
    "countdown_seconds": 5,
    "queue": {"message_rate": 0.35, "max_length": 20, "workers": 20},
    "input": {"default_press_seconds": 0.08},
    "commands": {
        "up": {"key": "up", "aliases": ["up", "cima"]},
        "down": {"key": "down", "aliases": ["down", "baixo"]},
        "left": {"key": "left", "aliases": ["left", "esquerda", "esq"]},
        "right": {"key": "right", "aliases": ["right", "direita", "dir"]},
        "a": {"key": "x", "aliases": ["a"]},
        "b": {"key": "z", "aliases": ["b"]},
        "start": {"key": "enter", "aliases": ["start", "iniciar"]},
        "select": {"key": "backspace", "aliases": ["select"]},
        "forward": {"key": "w", "aliases": ["forward", "frente", "andar frente"]},
        "backward": {"key": "s", "aliases": ["backward", "tras", "andar tras"]},
        "strafe_left": {"key": "a", "aliases": ["andar esquerda", "strafe left"]},
        "strafe_right": {"key": "d", "aliases": ["andar direita", "strafe right"]},
        "jump": {"key": "space", "aliases": ["jump", "pular", "pulo"]},
        "click": {"mouse_button": "left", "aliases": ["click", "clique", "atacar"]},
        "right_click": {
            "mouse_button": "right",
            "aliases": ["right click", "clique direito", "usar"],
        },
        "look_up": {"mouse_move": [0, -80], "aliases": ["look up", "olhar cima", "mouse cima"]},
        "look_down": {"mouse_move": [0, 80], "aliases": ["look down", "olhar baixo", "mouse baixo"]},
        "look_left": {
            "mouse_move": [-80, 0],
            "aliases": ["look left", "olhar esquerda", "mouse esquerda"],
        },
        "look_right": {
            "mouse_move": [80, 0],
            "aliases": ["look right", "olhar direita", "mouse direita"],
        },
    },
}


def create_default_config(path: str | Path) -> Path:
    return save_config(path, copy.deepcopy(DEFAULT_CONFIG))


def save_config(path: str | Path, data: dict[str, Any]) -> Path:
    """Write config atomically so an interrupted save cannot corrupt config.json."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def read_config(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError("config root must be an object")

    for section in ("stream", "target", "queue", "input"):
        _merge_defaults(data, section)
    data.setdefault("countdown_seconds", DEFAULT_CONFIG["countdown_seconds"])
    if not isinstance(data.get("commands"), dict):
        data["commands"] = copy.deepcopy(DEFAULT_CONFIG["commands"])
    return data


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a usable editor config while preserving the pre-v4.1.1 contract."""
    data = read_config(path)
    stream = data["stream"]
    if not any(
        str(stream.get(key, "")).strip()
        for key in ("twitch_channel", "youtube_channel_id", "youtube_stream_url")
    ):
        raise ConfigError("set a Twitch channel or YouTube channel/stream URL")

    commands = data.get("commands")
    if not isinstance(commands, dict) or not commands:
        raise ConfigError("commands must be a non-empty object")
    return data


def load_runtime_config(path: str | Path) -> dict[str, Any]:
    """Load and fully validate settings before starting the runtime."""
    return validate_runtime_config(load_config(path))


def _merge_defaults(data: dict[str, Any], name: str) -> None:
    section = data.setdefault(name, {})
    if not isinstance(section, dict):
        section = {}
        data[name] = section
    for key, value in copy.deepcopy(DEFAULT_CONFIG[name]).items():
        section.setdefault(key, value)
