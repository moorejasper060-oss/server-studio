# Server Studio UI — Design Spec

**Date:** 2026-05-30
**Status:** Approved (design), pending implementation plan
**Scope:** The PySide6 desktop UI (roadmap "Plan 6"), built on the existing headless core.
**Mockups:** `.superpowers/mockups/01-app-shell.html` … `06-colorways.html` (not committed; gitignored).

## 1. Summary

The UI is a PySide6 desktop front-end on top of the existing Server Studio core
(`app.build_server_manager()`). It gives the version-first flow, multi-server management,
and a live console a modern, animated, dark interface. The user navigates from an icon
rail; the main area is a dashboard of server cards. Creating a server is a 3-step modal
wizard; opening a server shows a tabbed detail view centered on a live console. The whole
app is themeable: a dark base with **six selectable accent themes** chosen in Settings and
remembered between launches.

This spec covers the app shell, Dashboard, New Server wizard, Server detail (Console + a
functional Settings tab), the theming system, and the threading/wiring to the core. Tabs
whose backing features arrive later (Mods → Plan 3, Sharing → Plan 4, Backups → Plan 5)
appear as labeled placeholders here and are filled in by those plans.

## 2. Goals & Non-Goals

### Goals
- Icon-rail shell with Dashboard, New Server, and Settings.
- Dashboard of server cards with live status (running / stopped / starting), version·loader
  badge, players/RAM/uptime, quick Start·Stop·Open, hover-lift, and a first-run empty state.
- 3-step New Server wizard (Version → Loader → Configure) where the loader step shows
  **only loaders valid for the chosen version**, and Configure auto-downloads Java with a
  visible progress step.
- Server detail view with a real-terminal Console (color-coded, autoscroll, command input)
  and a live stats rail, plus a working Settings tab (RAM, port, rename, delete).
- Six selectable accent themes on a shared dark base, chosen in Settings → Appearance,
  applied live, persisted.
- Smooth, professional animations (hover-lift, tab cross-fade, status pulse, progress).
- No changes to the core's public behavior; the UI consumes it through `ServerManager`.

### Non-Goals (this plan)
- Mods/Plugins browser UI (Plan 3), Sharing/tunnel UI (Plan 4), Backups UI (Plan 5),
  Players management beyond a basic list — these tabs are placeholders here.
- Forge/NeoForge/Spigot loaders (Plan 2b) — the wizard lists the loaders the core
  currently supports; others appear when their installers land.
- Packaging/installer (Plan 7).

## 3. Tech Stack

- PySide6 (Qt Widgets), styled via QSS. Animations via `QPropertyAnimation` and
  `QGraphicsDropShadowEffect`.
- Sits on the existing core: `AppPaths`, `app.build_server_manager()`, `ServerManager`,
  `ServerProcess` (its `on_output` callback is the console feed).
- Packaged later with PyInstaller (Plan 7).

## 4. Architecture

A new `src/server_studio/ui/` package. The UI never talks to installers/process directly —
only through `ServerManager`. The existing core is unchanged.

```
src/server_studio/ui/
  __init__.py
  main.py            # entrypoint: QApplication, AppSettings, theme, MainWindow
  theme.py           # THEMES registry + qss(accent) -> stylesheet string
  settings_store.py  # AppSettings: load/save selected theme (JSON in app-data root)
  main_window.py     # icon rail + stacked pages (Dashboard / Settings / detail)
  widgets/
    server_card.py   # one dashboard card (status, badge, stats, actions, hover-lift)
    dashboard.py     # the card grid + "new server" tile + empty state
    new_server_wizard.py  # 3-step modal dialog
    server_detail.py # header + tabs container
    console_view.py  # terminal widget: log area + command input
    settings_page.py # Appearance (theme picker) + app-level settings
  workers.py         # QThread/worker bridging ServerProcess output to Qt signals
```

### Threading & data flow
- `ServerManager` runs servers via `ServerProcess`, which streams stdout on a **reader
  thread** and calls `on_output(line)` off the UI thread. The UI passes an `on_output`
  that emits a Qt **signal** (queued connection), so console lines land safely on the UI
  thread. This is exactly the contract the core was built for.
- Long operations (create server → install jar + download Java) run on a worker thread
  (`workers.py`) so the UI stays responsive; progress/status surfaces via signals.
- Dashboard status (running/stopped, players, uptime) is refreshed on a `QTimer` poll of
  `ServerManager` plus event-driven updates from console/lifecycle signals.

### Version-aware loader list
- The wizard asks the core which loaders are valid for the chosen version. For this plan it
  uses `SUPPORTED_LOADERS` from the installer registry (Vanilla/Paper/Purpur/Fabric) and,
  where cheap, filters by the selected version; richer per-version availability can refine
  later without changing the UI contract.

## 5. Theming System

- `theme.py` defines `THEMES`: an ordered registry of accent themes, each a small dict of
  color tokens (accent, accent-dim, accent-border, accent-text, glow) over a shared dark
  base. The six: **grass-green** (default), **diamond-blue**, **emerald-teal**,
  **nether-amber**, **amethyst**, **redstone**.
- `qss(theme)` returns the full Qt stylesheet string for a theme (base + accent tokens
  substituted). Switching theme re-applies the app stylesheet live.
- `settings_store.AppSettings` persists the selected theme key to a JSON file in the
  app-data root (separate from per-server `server.json`). Default = `grass-green`.
- Settings → Appearance shows the six as swatches; selecting one applies + saves immediately.

## 6. Screens

### Dashboard
Card grid (`server_card.py`). Each card: status dot (pulse when running), name,
version·loader badge, stats (players / RAM / uptime), and contextual actions
(Stop+Open when running; Start+Open when stopped; Cancel+Open when starting). Hover lifts
the card with a shadow. A dashed "Create a new server" tile and a friendly empty state for
first run. Top bar has the title, a summary ("3 servers · 1 running"), and **+ New Server**.

### New Server wizard
Modal dialog, three steps with a stepper:
1. **Version** — choose a Minecraft version.
2. **Loader** — cards for the loaders valid for that version, tagged mods/plugins; one selectable.
3. **Configure** — name + RAM slider (+ optional port). "Create" runs install on a worker:
   server jar + auto Java download, shown as an animated progress step; on success the
   dialog closes and the new card appears.

### Server detail
Header: back, name, status dot, version·loader badge, Share (placeholder→Plan 4), Stop/Start.
Tabs: **Console** · Mods (placeholder) · Settings · Players (basic list) · Backups
(placeholder) · Sharing (placeholder).
- **Console** (`console_view.py`): monospace log area, color-coded by level
  (info/grey, success/accent, warn/amber, join/blue), autoscroll, and a `>` command input
  that sends to the server via `ServerManager`/`ServerProcess.send`. A right rail shows live
  stats (players, TPS if available, memory meter, uptime).
- **Settings** (`settings_page.py` server-scoped section): RAM, port, rename, delete server.

### App Settings (rail → Settings)
- **Appearance**: the six-theme swatch picker (live apply + persist).
- Room for app-level prefs later (default RAM, data folder) — only Appearance is required now.

## 7. Error Handling

- No raw tracebacks in the UI. Worker failures (install/Java/network) surface as a friendly
  inline message in the wizard with a retry and a "details" expander.
- Server crash on boot: the console shows the captured output; the card returns to Stopped
  with a subtle error marker.
- Port in use / start failure (the core's `RuntimeError` already-running guard, etc.) is
  caught and shown as a non-blocking toast/inline message.

## 8. Testing

- **Logic tests (no Qt event loop):**
  - `theme.qss(theme)` returns a non-empty stylesheet for every theme key, and every theme
    defines the full token set.
  - `AppSettings` load/save round-trips the selected theme; defaults to grass-green when the
    file is missing or invalid.
  - The wizard's "loaders valid for version" helper returns only supported loaders.
- **Widget smoke tests** with `pytest-qt` (`qtbot`): each screen widget constructs and shows
  without error given a fake/in-memory `ServerManager`; the console view appends a line when
  its slot receives one; clicking Start calls the manager.
- The core stays covered by its existing 50 offline tests; the UI is built in small,
  single-responsibility widget modules so each stays reviewable and testable in isolation.

## 9. Open Questions / Risks

- **pytest-qt dependency:** adds a dev dependency for widget tests (headless via
  `QT_QPA_PLATFORM=offscreen`). Acceptable; documented in the plan.
- **TPS metric:** not all loaders expose TPS the same way; the stats rail shows it when
  available and hides it otherwise.
- **Live theme re-apply:** re-setting the app stylesheet must refresh all open widgets;
  verified during the UI polish step.
