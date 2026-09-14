# ChatPlays v4.1.1

This maintenance release keeps the v4.1.0 behavior while tightening lifecycle, target safety, configuration persistence and regression coverage.

- Runtime cleanup now runs even when startup is cancelled during countdown or target preparation fails.
- Pending executor work is cancelled before held inputs are released during shutdown.
- Multi-key combos roll back internal/posted key state when a later key fails to send.
- Window targeting now rejects explicit executable/process mismatches before considering title similarity.
- Cached target windows are revalidated against their original PID to reduce HWND-reuse mistakes.
- `config.json` saves are atomic, reducing the chance of corruption if a save is interrupted.
- Runtime validation is centralized while preserving the existing editable/incomplete config loading behavior.
- Added regression tests for lifecycle cleanup, strict target matching, combo rollback, config persistence and Twitch/YouTube parsing.
- Ruff now includes bugbear (`B`) checks in addition to the existing lint rules.

No intentional UI, command syntax, Twitch/YouTube behavior, emulator/ROM workflow or isolated-input workflow changes are included.
