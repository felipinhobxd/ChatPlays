import argparse
import sys
from pathlib import Path

from chatplays import __version__
from chatplays.app import ChatPlaysApp
from chatplays.config import ConfigError, create_default_config, load_runtime_config
from chatplays.desktop_ui import ChatPlaysUI


def default_config_path() -> Path:
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
    return base / "config.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Let Twitch/YouTube chat control a game.")
    parser.add_argument("--config", help="Path to config JSON")
    parser.add_argument("--headless", action="store_true", help="Run without the graphical UI")
    parser.add_argument("--check", action="store_true", help="Validate config and exit")
    parser.add_argument("--version", action="version", version=f"ChatPlays {__version__}")
    return parser.parse_args()


def _run_headless(config_path: Path, check_only: bool) -> int:
    if not config_path.exists():
        create_default_config(config_path)
        print(f"Created {config_path}")
        return 0
    try:
        config = load_runtime_config(config_path)
    except (ConfigError, OSError, TypeError, ValueError) as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    if check_only:
        print("Config OK")
        return 0
    try:
        ChatPlaysApp(config).run()
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Startup error: {exc}", file=sys.stderr)
        return 1
    return 0


def _run_ui(config_path: Path, ui_factory=ChatPlaysUI) -> None:
    """Run the desktop UI and never let the process exit before runtime cleanup."""
    ui = ui_factory(config_path)
    try:
        ui.run()
    finally:
        if ui.stop_event:
            ui.stop_event.set()
        if ui.worker and ui.worker.is_alive():
            ui.worker.join()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config) if args.config else default_config_path()
    if args.headless or args.check:
        return _run_headless(config_path, args.check)
    _run_ui(config_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
