# ChatPlays v4.0.0

A major cleanup focused on the original Twitch Plays idea: chat messages in, real game input out.

- Rewritten from Node.js to a compact Python core.
- Standalone Windows `ChatPlays.exe` — Python is not required for the release build.
- Twitch and YouTube can run together with non-blocking reconnects.
- Direct Windows `SendInput` keyboard and relative mouse input.
- PT-BR + English aliases, timed/indefinite HOLD, and safe global release.
- One `config.json`; the executable creates it automatically on first launch.
- Removed the old web wizard, dashboard, installer framework, profiles, bundled drivers, gamepad stack and other high-complexity layers.
- CI now lints, compiles, tests, and builds the Windows executable before release.

This rewrite is inspired in part by DougDoug's MIT-licensed TwitchPlays project. Attribution is preserved in `THIRD_PARTY_NOTICES.md`.
