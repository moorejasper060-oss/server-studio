# Server Studio

Create and manage local Minecraft servers with a modern desktop UI.

## Status
Desktop app with full loader coverage. The modern PySide6 UI can create, start, stop, and
stream servers for **Vanilla, Paper, Purpur, Fabric, Forge, NeoForge, and Spigot**,
auto-downloading the correct Temurin Java runtime. The **mod/plugin browser** (Modrinth,
version+loader filtered, plus manual `.jar` import; CurseForge optional via a
`CURSEFORGE_API_KEY`) is built in. Internet sharing (tunnel) and world backups arrive in
later plans.

## Development
```
python -m pip install -e ".[dev]"
python -m pytest
```

## Running the app
```
python -m pip install -e ".[dev]"
python -m server_studio.ui.main
```
The window opens with the dashboard. Create a server with **+ New Server**, then Start it to stream its console live. Switch accent themes under the ⚙ Settings page.
