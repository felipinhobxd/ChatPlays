from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


def load_config(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError("config root must be an object")

    stream = data.get("stream", {})
    twitch = str(stream.get("twitch_channel", "")).strip()
    youtube_id = str(stream.get("youtube_channel_id", "")).strip()
    youtube_url = str(stream.get("youtube_stream_url", "")).strip()
    if not twitch and not youtube_id and not youtube_url:
        raise ConfigError("set stream.twitch_channel or a YouTube channel/stream URL")

    commands = data.get("commands")
    if not isinstance(commands, dict) or not commands:
        raise ConfigError("commands must be a non-empty object")

    queue = data.setdefault("queue", {})
    queue.setdefault("message_rate", 0.35)
    queue.setdefault("max_length", 20)
    queue.setdefault("workers", 20)

    input_cfg = data.setdefault("input", {})
    input_cfg.setdefault("default_press_seconds", 0.08)

    data.setdefault("countdown_seconds", 5)
    return data
