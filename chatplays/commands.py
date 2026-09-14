import re
import unicodedata
from dataclasses import dataclass
from typing import Any


_DURATION_RE = re.compile(r"^(\d+(?:[.,]\d+)?)(ms|s)?$", re.IGNORECASE)
_RELEASE = {"release", "release all", "soltar", "soltar tudo"}
_HOLD_PREFIXES = ("hold ", "segurar ")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.split())


def parse_duration(value: str, minimum: float = 0.001, maximum: float = 10.0) -> float:
    match = _DURATION_RE.fullmatch(normalize(value))
    if not match:
        raise ValueError(f"invalid duration: {value!r}")

    seconds = float(match.group(1).replace(",", "."))
    if (match.group(2) or "s").lower() == "ms":
        seconds /= 1000
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
        self.default_press_seconds = float(default_press_seconds)
        self._aliases: dict[str, tuple[str, dict[str, Any]]] = {}

        for name, spec in commands.items():
            for alias in (*spec.get("aliases", []), name):
                key = normalize(str(alias))
                if not key:
                    continue
                previous = self._aliases.get(key)
                if previous and previous[0] != name:
                    raise ValueError(f"duplicate command alias {alias!r}: {previous[0]!r} and {name!r}")
                self._aliases[key] = (name, spec)

    def resolve(self, message: str) -> ParsedAction | None:
        text = normalize(message)
        if not text:
            return None
        if text in _RELEASE:
            return ParsedAction("release", {}, release_all=True)

        for prefix in _HOLD_PREFIXES:
            if text.startswith(prefix):
                return self._resolve_hold(text.removeprefix(prefix))

        found = self._aliases.get(text)
        if not found:
            return None
        name, spec = found
        duration = spec.get("duration")
        return ParsedAction(name, spec, duration=float(duration) if duration is not None else None)

    def _resolve_hold(self, body: str) -> ParsedAction | None:
        body = normalize(body)
        if not body:
            return None

        alias, duration = body, None
        if " " in body:
            candidate, maybe_duration = body.rsplit(" ", 1)
            try:
                duration = parse_duration(maybe_duration)
                alias = candidate
            except ValueError:
                pass

        found = self._aliases.get(alias)
        if not found:
            return None
        name, spec = found
        if not ({"key", "mouse_button"} & spec.keys()):
            return None
        return ParsedAction(name, spec, hold=True, duration=duration)
