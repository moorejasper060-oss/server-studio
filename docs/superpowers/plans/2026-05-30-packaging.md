# Server Studio — Plan 7: Packaging (.exe) Implementation Plan

> Implemented directly (config-heavy, low logic). Recorded here for the roadmap.

**Goal:** Package the app as a standalone Windows application folder via PyInstaller, so users can run `ServerStudio.exe` without a Python install.

**Architecture:** A plain entry script `packaging/entry.py` calls `server_studio.ui.main:main`. A PyInstaller spec (`server-studio.spec`, 6.x format, one-folder, windowed/no-console) bundles it with `pathex=["src"]` so the src-layout package is found; PyInstaller's built-in PySide6 hooks pull in the Qt runtime. An optional vendored `bore` binary (`vendor/bore.exe`) is bundled if present (for the internet tunnel). `scripts/build.ps1` runs the build.

**Tech Stack:** PyInstaller 6.x (added as a `build` optional-dependency).

## What was built
- `packaging/entry.py` — entry script (`from server_studio.ui.main import main; sys.exit(main())`).
- `server-studio.spec` — one-folder, `console=False`, `pathex=["src"]`, conditional bore bundling, excludes tkinter.
- `scripts/build.ps1` — installs `.[dev,build]` and runs `python -m PyInstaller --noconfirm server-studio.spec`.
- `pyproject.toml` — `[project.optional-dependencies] build = ["pyinstaller>=6.6"]`.
- `tests/test_packaging.py` — verifies the entry script imports and exposes a callable `main`, and that the spec + build script exist.

## Verification
- Unit: entry import + artifacts present (in the suite).
- Build: `python -m PyInstaller --noconfirm server-studio.spec` produces `dist/ServerStudio/ServerStudio.exe`. Launch it → the dashboard opens (no console window). (Run as part of release QA; the build is too slow/large for CI here.)

## Notes / future
- Java is auto-downloaded at runtime (Temurin), so no JDK is bundled.
- `bore` (internet tunnel) is optional: drop `vendor/bore.exe` before building to bundle it.
- A future refinement: an app icon, a one-file build, and a signed installer.
