# Server Studio

Create and manage local Minecraft servers with a modern desktop UI.

## Status
Core foundation + loaders & Java. The Python core can create, start, stop, and stream
servers for Vanilla, Paper, Purpur, and Fabric, auto-downloading the correct Temurin Java
runtime. Forge/NeoForge/Spigot, the mod browser, tunnel, backups, and the UI arrive in
later plans.

## Development
```
python -m pip install -e ".[dev]"
python -m pytest
```
