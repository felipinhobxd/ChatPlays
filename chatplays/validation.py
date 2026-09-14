from __future__ import annotations

from typing import Any

from .commands import CommandRegistry
from .target import TargetResolver


def validate_runtime_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate settings shared by the UI and headless runtime.

    The function returns the same mapping so callers can validate inline without
    creating a second configuration representation.
    """
    stream = config.get("stream")
    if not isinstance(stream, dict):
        raise ValueError("stream must be an object")
    if not any(
        str(stream.get(key, "")).strip()
        for key in ("twitch_channel", "youtube_channel_id", "youtube_stream_url")
    ):
        raise ValueError("Informe um canal da Twitch ou um canal/URL de live do YouTube.")

    queue = config.get("queue")
    if not isinstance(queue, dict):
        raise ValueError("queue must be an object")
    input_config = config.get("input")
    if not isinstance(input_config, dict):
        raise ValueError("input must be an object")

    countdown = int(config.get("countdown_seconds", 0))
    message_rate = float(queue.get("message_rate", 0))
    max_length = int(queue.get("max_length", 0))
    workers = int(queue.get("workers", 0))
    default_press = float(input_config.get("default_press_seconds", 0))

    if countdown < 0:
        raise ValueError("A contagem antes de iniciar não pode ser negativa.")
    if message_rate < 0:
        raise ValueError("A velocidade da fila não pode ser negativa.")
    if max_length < 1:
        raise ValueError("O máximo da fila precisa ser pelo menos 1.")
    if workers < 1:
        raise ValueError("Workers precisa ser pelo menos 1.")
    if default_press <= 0:
        raise ValueError("A duração padrão da tecla precisa ser maior que zero.")

    commands = config.get("commands")
    if not isinstance(commands, dict) or not commands:
        raise ValueError("commands must be a non-empty object")
    CommandRegistry(commands, default_press)

    target = config.get("target")
    if not isinstance(target, dict):
        raise ValueError("target must be an object")
    TargetResolver(target).validate()
    return config
