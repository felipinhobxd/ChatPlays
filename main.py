from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

from chatplays.app import ChatPlaysApp
from chatplays.commands import CommandRegistry
from chatplays.config import ConfigError, load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Let Twitch/YouTube chat control a game.")
    parser.add_argument("--config", default="config.json", help="Path to config JSON")
    parser.add_argument("--check", action="store_true", help="Validate config and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.exists() and config_path.name == "config.json":
        example = Path("config.example.json")
        if example.exists():
            shutil.copyfile(example, config_path)
            print("Created config.json from config.example.json.")
            print("Edit config.json, set your Twitch channel and/or YouTube stream, then run again.")
            return 0

    try:
        config = load_config(config_path)
        CommandRegistry(config["commands"], config["input"]["default_press_seconds"])
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Command config error: {exc}", file=sys.stderr)
        return 2

    if args.check:
        print("Config OK")
        return 0

    try:
        ChatPlaysApp(config).run()
    except RuntimeError as exc:
        print(f"Startup error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
