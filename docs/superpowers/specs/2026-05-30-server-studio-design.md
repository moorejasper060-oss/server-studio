# Server Studio — Design Spec

**Date:** 2026-05-30
**Status:** Approved (design), pending implementation plan
**Working name:** Server Studio

## 1. Summary

Server Studio is a polished, shareable Windows desktop app that lets anyone create and
manage local Minecraft servers with zero command-line work. The user picks a Minecraft
version and a server type (loader), and the app provisions everything — the server jar,
the correct Java runtime, and a sensible config. From there the user manages the server
through a modern UI: a live console, a version-aware mod/plugin browser, world backups,
and one-click "invite friends over the internet" via a built-in tunnel.

The defining experiences:
1. **Version-first flow** — pick the MC version + loader up front; the app knows exactly
   what to install and which Java to fetch.
2. **Version-aware mod/plugin browser** — only ever shows mods/plugins compatible with the
   server's exact version + loader, so installs never break the server.
3. **One-click internet sharing** — friends can join from anywhere without router config.

## 2. Goals & Non-Goals

### Goals
- Create, run, and manage multiple local servers from one app.
- Support loaders: Vanilla, Paper, Purpur, Spigot, Fabric, Forge, NeoForge.
- Auto-download and cache the correct Java runtime per server (no user involvement).
- Browse and install mods (Modrinth, CurseForge) and plugins, filtered to the server's
  version + loader, with dependency resolution; plus manual `.jar` import.
- One-click internet sharing via an embedded tunnel; also surface LAN IP and
  port-forwarding info.
- World backup/restore.
- A modern, animated, professional UI — finished-product quality.
- Ship as a Windows `.exe` via PyInstaller.

### Non-Goals (for this project)
- Remote/headless server hosting on cloud providers.
- Managing servers on machines other than the local one.
- Cross-platform (macOS/Linux) builds — Windows is the target. Code stays
  platform-agnostic where cheap, but only Windows is shipped/tested.
- Mod *development* tooling.

## 3. Audience & Quality Bar

A shareable, polished `.exe` intended for friends and the public — same bar as
Color Grade Studio. Must handle the common failure cases gracefully (no Java, wrong
version, network errors, port in use) rather than crashing or showing raw tracebacks.

## 4. Tech Stack

- **Language/UI:** Python + PySide6 (Qt). Matches existing experience (Color Grade Studio).
- **Packaging:** PyInstaller → single Windows `.exe` / installer.
- **HTTP:** `httpx` (async-capable) for API calls and downloads.
- **Process management:** Python `subprocess` + a supervising thread/QProcess for the
  Java server process and live console streaming.
- **Styling/animation:** Qt Style Sheets (QSS) + `QPropertyAnimation` /
  `QGraphicsDropShadowEffect` for transitions, hover lifts, status pulses.

## 5. Architecture

```
┌─────────────────────────────────────────────┐
│              PySide6 Desktop App              │
│  ┌──────────────┐      ┌──────────────────┐  │
│  │  UI Layer    │◄────►│  Core (Python)   │  │
│  │ (windows,    │      │  - ServerManager │  │
│  │  wizards,    │      │  - VersionManager│  │
│  │  console)    │      │  - JavaManager   │  │
│  │              │      │  - ModBrowser    │  │
│  │              │      │  - TunnelManager │  │
│  │              │      │  - BackupManager │  │
│  └──────────────┘      └────────┬─────────┘  │
└─────────────────────────────────┼────────────┘
                                  │
         ┌────────────────────────┼───────────────────┐
         ▼                        ▼                    ▼
   Java subprocess          Web APIs              Local disk
   (the MC server)   (Modrinth/CurseForge/   (servers/, java/,
                      Adoptium/loader APIs)    cache/, backups/)
```

### Data layout (on disk)
```
<app-data>/
  servers/
    <server-id>/
      server.json          # app metadata (see schema below)
      server.jar           # server/loader jar
      server.properties     # MC config
      eula.txt
      mods/ | plugins/      # depending on loader
      world/ ...
  java/
    temurin-8/ temurin-17/ temurin-21/   # cached, shared across servers
  cache/                   # API responses, downloaded artifacts
  backups/
    <server-id>/<timestamp>.zip
```

### `server.json` schema (app-owned metadata)
```json
{
  "id": "uuid",
  "name": "My SMP",
  "mc_version": "1.20.6",
  "loader": "paper",
  "loader_version": "build-123",
  "java_runtime": "temurin-21",
  "ram_mb": 4096,
  "port": 25565,
  "tunnel": { "enabled": true, "provider": "playit", "address": null },
  "created_at": "2026-05-30T12:00:00Z",
  "installed_content": [
    { "source": "modrinth", "project_id": "...", "version_id": "...",
      "filename": "sodium-...jar", "enabled": true }
  ]
}
```

## 6. Core Components

### ServerManager
- CRUD for servers; owns the `servers/` directory and `server.json`.
- Starts/stops/restarts the Java process with the correct runtime, RAM flags, and jar.
- Streams stdout/stderr to the UI console in real time; sends commands to stdin.
- Handles first-run setup: EULA acceptance prompt, default `server.properties`.
- Detects/handles common errors: port in use, crash on boot, OOM.

### VersionManager
- Fetches available MC versions per loader and the loader/build lists:
  - Vanilla: Mojang version manifest.
  - Paper/Purpur: their respective REST APIs (project/version/build).
  - Fabric: Fabric meta API (loader + installer).
  - Forge/NeoForge: their maven/promotions metadata.
  - Spigot: BuildTools-based (documented caveat: must compile).
- Resolves and downloads the correct server jar for a chosen version + loader.

### JavaManager
- Maps MC version → required Java major version (e.g. ≤1.16→8, 1.17–1.20.4→17,
  1.20.5+→21).
- Downloads matching Temurin runtime from Adoptium if not already cached; reuses across
  servers. Verifies checksums.

### ModBrowser
- Searches Modrinth and CurseForge, **always filtered to the server's `mc_version` +
  `loader`** so results only show compatible content.
- One-click install with transitive dependency resolution.
- Manual `.jar` drag-and-drop import.
- Enable/disable (toggle file extension), update (detect newer compatible version),
  remove. Tracks everything in `installed_content`.
- CurseForge requires an API key (handled as a build-time/config secret; documented).

### TunnelManager
- One-click "invite friends over internet": starts an embedded tunnel (playit.gg-style)
  bound to the server's port and surfaces the shareable address.
- Also surfaces LAN IP + port and a short port-forwarding guide for advanced users.
- Cleanly tears down the tunnel on server stop / app exit.

### BackupManager
- Snapshot a server's `world/` (and configs) to a timestamped zip; restore from a
  snapshot; list/delete backups.

## 7. UI / UX

### Screens
- **Dashboard:** cards per server (name, version+loader badge, animated status dot,
  RAM/player counts), `+ New Server` action.
- **New Server wizard:** version → loader → name/RAM → create. Java fetched automatically
  with an animated progress step.
- **Server detail:** tabbed — Console · Mods/Plugins · Settings · Players · Backups ·
  Sharing.

### Visual direction
Dark, modern, with depth (not flat). Custom-themed Qt:
- Left icon sidebar navigation.
- Rounded server cards with subtle hover-lift + drop shadow.
- Smooth page/tab cross-fade transitions (`QPropertyAnimation`).
- Animated status pulses (green = running), motion in download progress.
- Console with a real terminal feel (monospace, colored log levels, autoscroll).
- Creative biome-green accent palette, but clean and professional —
  Linear/Vercel-grade polish, not blocky.
- In-app mockups reviewed with the user during build to steer the look.

## 8. Error Handling

- No raw tracebacks shown to users; surface friendly messages with a "details" expander.
- Network failures: retry + cached fallbacks where possible; clear offline messaging.
- Port conflicts: detect and offer an alternate port.
- Server crash on boot: capture the log tail and show a readable summary.
- Java download failure: clear retry path; never leave a half-installed runtime.

## 9. Testing

- Unit tests for pure logic: version→Java mapping, mod compatibility filtering,
  dependency resolution, `server.json` read/write/migration.
- Integration tests (mocked HTTP) for VersionManager, JavaManager, ModBrowser against
  recorded API fixtures.
- Process-management tests using a fake long-running process to validate
  start/stop/console-stream/command-send.
- Manual QA checklist for the UI and full create→run→mod→share→backup happy path.

## 10. Build Order (internal milestones)

Scope is the full app; this is just a sane, testable build sequence:

1. **Core skeleton:** app data layout, `server.json`, ServerManager create/start/stop +
   live console (Vanilla only, manual Java).
2. **VersionManager + JavaManager:** version/loader selection, auto server jar +
   auto Java for all loaders.
3. **ModBrowser:** Modrinth (version/loader-filtered) + manual import + enable/disable/
   update/remove; then CurseForge.
4. **TunnelManager:** one-click internet sharing + LAN/port-forward info.
5. **BackupManager.**
6. **UI polish pass:** theming, animations, transitions, final visual direction.
7. **Packaging:** PyInstaller `.exe`, first-run experience, distribution.

## 11. Open Questions / Risks

- **CurseForge API key:** distribution terms and how the key is embedded/handled in a
  public `.exe`. May ship Modrinth-first and gate CurseForge behind a user-supplied key.
- **Tunnel provider:** which embeddable service (playit.gg vs alternatives) — licensing,
  reliability, and whether a binary must be bundled.
- **Spigot:** requires compiling via BuildTools (slow, needs Java) — confirm we want it in
  v1 vs Paper/Purpur as the recommended Spigot-API alternative.
- **Forge/NeoForge installers:** headless install quirks per version range.
- **GitHub repo:** public repo like Color Grade Studio? (To confirm before first commit.)
