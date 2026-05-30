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
