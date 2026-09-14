# ChatPlays v4.1.2

This release focuses on safer shutdown, deterministic input handling and a cleaner game-switching workflow without changing the isolated-input safety model.

- Closing the desktop UI now waits for runtime cleanup before the process exits.
- Timed key presses/clicks react to stop requests instead of sleeping blindly.
- Twitch IRC decoding preserves split UTF-8 sequences such as accents and emoji.
- Window selection is fail-closed when multiple equivalent processes (for example several `javaw.exe` windows) are open.
- The packaged Windows executable is now launched during CI; CI fails if it exits immediately during startup.
- Keyboard/mouse actions now use one serialized input dispatcher instead of concurrent workers.
- `release` / `soltar` has priority: it can interrupt a timed action, clear older pending inputs and release held controls before newer commands continue.
- The obsolete input-worker setting was removed from new configs/UI while older configs remain compatible.
- Numeric runtime validation rejects non-finite values such as `NaN` and `inf`.
- Added portable game profiles stored in `profiles.json` beside `config.json`.
- Profiles contain target, commands and gameplay/input settings while deliberately preserving the active Twitch/YouTube connection settings.
- Added built-in Minecraft and Pokémon / Emulador templates; executable/ROM paths are intentionally left for the user to select.
- Added regression coverage for shutdown, UTF-8 streaming, target ambiguity, input ordering/preemption and profile persistence/isolation.

The core safety rule remains unchanged: ChatPlays sends input only to the explicitly resolved game window and never silently falls back to global Windows input.
