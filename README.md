# Wilds Atlas

A map of the Wilds, our medieval RPG Minecraft world, styled like an old chart. It is rendered from the server's region files and hosted on GitHub Pages, so friends only need a link.

**https://andreyvld.github.io/wilds-atlas/**

![The Wilds Atlas in the parchment style](docs/preview.webp)

- Four map styles: parchment, terrain, biomes and elevation, from a whole-world view down to single blocks
- Heraldic markers for villages, taverns, keeps, temples, towers, illager camps, dungeons and ruins, read from the chunks themselves (vanilla, Terralith, Dungeons and Taverns, Structory, ATi, Grim Kingdoms and more), plus spawn, warps, waystones and WorldGuard safe zones
- Biome names, search, a distance ruler with travel times, and a readout of x, y, z, biome and block under the cursor
- Shareable links (`#wilds/x/z/zoom/style`), a candlelight dark mode, and phone support

The renderer reads only region files and plugin configs. Player positions, inventories, homes and the seed never leave the server.

## How it works

1. `tools/` (Python) reads `world/dimensions/.../region/*.mca` straight from the server folder and caches what it read. It draws 256 px WebP tiles for every zoom level, plus small lookup images for the cursor readout.
2. `publish` force-pushes that output as a single commit on the `map-data` branch, so the repo never grows with old maps. It then writes the commit id to `data.lock` on `main`.
3. The push to `main` runs the Pages workflow, which builds `web/` (TypeScript, Vite, Leaflet) with that map data and deploys it.

## Setup on the server PC

1. Install [Git](https://git-scm.com/download/win) and [Python 3.11+](https://www.python.org/downloads/) (tick "Add python.exe to PATH").
2. Clone the repo next to the server folder, so `config.toml` finds `../OG Server/minecraft-server`:
   ```
   cd D:\minecraft-servers
   git clone https://github.com/AndreyVLD/wilds-atlas
   cd wilds-atlas
   pip install -r tools/requirements.txt
   ```
3. On GitHub, open **Settings → Pages** and set **Source** to **GitHub Actions**.

## Updating the map

Double-click `atlas.bat`, or run:

```
python tools/atlas.py publish
```

Only regions whose files changed since the last run are read and redrawn: new chunks from Chunky or from exploring, and builds. The site updates a minute or two after the push. Running it while the server is up is fine. Paper writes chunks to disk every few minutes, and `save-all` first catches the rest. Add `--full` to redraw everything.

To update every night at 05:00, run this once in a terminal:

```
schtasks /Create /TN "Wilds Atlas" /SC DAILY /ST 05:00 /TR "cmd /c cd /d D:\minecraft-servers\wilds-atlas && python tools\atlas.py publish > cache\last-publish.log 2>&1"
```

## Settings

`config.toml` holds the title, the server path, the worlds to map and display names for safe zones and warps. The main world and Vanilla are already listed but commented out; uncomment them to give the atlas a world switcher.

## Working on the site

```
python tools/atlas.py build        # render into web/public/maps without publishing
cd web
npm install
npm run dev                        # http://localhost:5173
```

| Path | What it holds |
| --- | --- |
| `tools/atlas.py` | Command line, incremental build, publish |
| `tools/scan.py` | Region and NBT reader, about 2 ms per chunk |
| `tools/render.py` | Block and biome colours, the four styles, tile output |
| `tools/world.py` | Structures, spawn, warps, zones, waystones, biome labels |
| `web/src/` | The site: map, markers, readout, search and ruler |
