from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any


_DURATION_RE = re.compile(r"^(\d+(?:[.,]\d+)?)(ms|s)?$", re.IGNORECASE)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.split())


def parse_duration(value: str, *, minimum: float = 0.001, maximum: float = 10.0) -> float:
    match = _DURATION_RE.fullmatch(normalize(value))
    if not match:
        raise ValueError(f"invalid duration: {value!r}")

    number = float(match.group(1).replace(",", "."))
    unit = (match.group(2) or "s").lower()
    seconds = number / 1000.0 if unit == "ms" else number
    if not minimum <= seconds <= maximum:
        raise ValueError(f"duration must be between {minimum}s and {maximum}s")
    return seconds


@dataclass(frozen=True)
class ParsedAction:
    name: str
    spec: dict[str, Any]
    hold: bool = False
    duration: float | None = None
    release_all: bool = False


class CommandRegistry:
    def __init__(self, commands: dict[str, dict[str, Any]], default_press_seconds: float = 0.08):
        self.commands = commands
        self.default_press_seconds = float(default_press_seconds)
        self._aliases: dict[str, tuple[str, dict[str, Any]]] = {}

        for name, spec in commands.items():
            aliases = list(spec.get("aliases", []))
            aliases.append(name)
            for alias in aliases:
                key = normalize(str(alias))
                if not key:
                    continue
                if key in self._aliases and self._aliases[key][0] != name:
                    other = self._aliases[key][0]
                    raise ValueError(f"duplicate command alias {alias!r}: {other!r} and {name!r}")
                self._aliases[key] = (name, spec)

    def resolve(self, message: str) -> ParsedAction | None:
        text = normalize(message)
        if not text:
            return None

        if text in {"release", "release all", "soltar", "soltar tudo"}:
            return ParsedAction(name="release", spec={}, release_all=True)

        for prefix in ("hold ", "segurar "):
            if text.startswith(prefix):
                return self._resolve_hold(text[len(prefix) :])

        found = self._aliases.get(text)
        if not found:
            return None

        name, spec = found
        duration = spec.get("duration")
        if duration is not None:
            duration = float(duration)
        return ParsedAction(name=name, spec=spec, duration=duration)

    def _resolve_hold(self, body: str) -> ParsedAction | None:
        body = normalize(body)
        if not body:
            return None

        duration: float | None = None
        alias_text = body
        parts = body.rsplit(" ", 1)
        if len(parts) == 2:
            try:
                duration = parse_duration(parts[1])
                alias_text = parts[0]
            except ValueError:
                pass

        found = self._aliases.get(alias_text)
        if not found:
            return None

        name, spec = found
        if "key" not in spec and "mouse_button" not in spec:
            return None
        return ParsedAction(name=name, spec=spec, hold=True, duration=duration)

    def describe(self) -> list[str]:
        rows: list[str] = []
        for name, spec in self.commands.items():
            aliases = [str(a) for a in spec.get("aliases", [])]
            target = spec.get("key") or spec.get("mouse_button") or spec.get("mouse_move")
            rows.append(f"{name}: {', '.join(aliases) or name} -> {target}")
        return rows
