# Manual QA — UI

Run `python -m server_studio.ui.main`, then verify:

- [ ] Dashboard shows the empty state on first run.
- [ ] **+ New Server** opens the wizard; version -> loader (only supported loaders) -> name/RAM.
- [ ] Creating a Vanilla 1.20.6 server downloads Java + jar and a card appears.
- [ ] Start the server — status flips to Running; the Console streams log lines live.
- [ ] Type a command (e.g. `help`) in the console; output appears.
- [ ] Stop the server — status flips to Stopped.
- [ ] Settings: clicking each of the 6 themes recolors the app immediately.
- [ ] Restart the app — the last chosen theme is still applied.

## Backups (Plan 5)
- [ ] Open a server's **Backups** tab; click **Backup now** → a timestamped zip appears.
- [ ] Delete the server's `world/`, click **Restore** → the world is back.
- [ ] **Delete** removes a backup from the list.

## Sharing (Plan 4)
- [ ] Open a server's **Sharing** tab: shows the LAN `ip:port` (friends on your WiFi can join).
- [ ] Public IP + port-forward guide is shown.
- [ ] With the `bore` binary on PATH, click **Share over internet** → a `bore.pub:PORT`
      address appears; clicking Stop clears it.

## Mod browser (Plan 3 — needs real network)
- [ ] Open a **Fabric** server's **Mods** tab; search "sodium"; click Install.
- [ ] The jar lands in the server's `mods/` folder; it shows in the Installed list.
- [ ] Disable it (file becomes `*.jar.disabled`), re-enable, then Remove.
- [ ] On a **Vanilla** server the Mods tab shows the placeholder (no browser).

## Loaders (Plan 2b — needs real network + Java)
- [ ] Create a **Forge** 1.20.x server: installer downloads, runs, and the server boots
      (launches via the @args file, not -jar).
- [ ] Create a **NeoForge** 1.21.x server: installer resolves the right version and boots.
- [ ] Create a **Spigot** server: BuildTools compiles (slow — minutes) and the jar boots.
