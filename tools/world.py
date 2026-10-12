"""Everything besides terrain: biome definitions, structures, warps, safe zones, waystones and map labels."""
import io
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import yaml

PACKS = {'minecraft': 'Vanilla', 'terralith': 'Terralith', 'nova_structures': 'Dungeons and Taverns',
         'dungeons_plus': 'Dungeons+', 'ati_structures': 'ATi Structures', 'grim_kingdoms': 'Grim Kingdoms',
         'structory': 'Structory', 'structory_towers': 'Structory: Towers', 'betterstructures': 'BetterStructures'}
CATS = (('ruin', ('ruin', 'rubble', 'remnant')),
        ('village', ('village', 'town', 'hamlet', 'settlement')),
        ('tavern', ('tavern', 'inn')),
        ('illager', ('pillager', 'illager', 'mansion', 'thatch_outpost', 'camp3')),
        ('castle', ('castillo', 'keep', 'fort', 'chateau', 'castle', 'citadel', 'palace', 'manor',
                    'herobrine_stronghold')),
        ('tower', ('tower', 'lookout', 'watch', 'foraging_outpost')),
        ('temple', ('temple', 'pyramid', 'monument', 'shrine', 'sanctum')),
        ('dungeon', ('dungeon', 'crypt', 'catacomb', 'trial', 'ancient_city', 'stronghold', 'bunker', 'nest',
                     'sculk', 'mineshaft', 'mining', 'refinery', 'chamber', 'deposit')))
QUALIFIERS = ('dark_oak', 'pale_oak', 'oak', 'spruce', 'birch', 'jungle', 'acacia', 'mangrove', 'cherry', 'bamboo',
              'plains', 'desert', 'savanna', 'snowy', 'taiga', 'swamp', 'badlands', 'mountain', 'ocean', 'beach',
              'forest', 'grassy', 'nether', 'surface', 'underground')
SMALL = {'of', 'the', 'and', 'in', 'on', 'a'}


def title(words):
    return ' '.join(w if i and w in SMALL else w[:1].upper() + w[1:] for i, w in enumerate(words))


def structure_name(sid):
    words = [re.sub(r'(?<=[a-z])\d+$', '', w) for w in sid.split(':', 1)[-1].split('/')[-1].split('_') if w]
    for q in sorted(QUALIFIERS, key=len, reverse=True):
        qs = q.split('_')
        if len(words) > len(qs) and words[-len(qs):] == qs:
            words = qs + words[:-len(qs)]
            break
    return title(words)


def category(sid):
    n = sid.split(':', 1)[-1]
    return next((c for c, keys in CATS if any(k in n for k in keys)), 'ruin')


def biome_name(bid):
    return title(bid.split(':', 1)[-1].split('/')[-1].split('_'))


class BiomeSource:
    """Biome JSON from the world's datapacks, falling back to the vanilla server jar Paper keeps in cache/."""

    def __init__(self, server: Path, level='world'):
        self.sources = []
        packs = server / level / 'datapacks'
        for p in sorted(packs.iterdir()) if packs.is_dir() else []:
            if p.suffix == '.zip':
                self.sources.append(zipfile.ZipFile(p))
            elif (p / 'data').is_dir():
                self.sources.append(p)
        jars = sorted((server / 'cache').glob('mojang_*.jar'), key=lambda p: p.stat().st_mtime)
        if jars:
            outer = zipfile.ZipFile(jars[-1])
            inner = [n for n in outer.namelist() if n.startswith('META-INF/versions/') and n.endswith('.jar')]
            self.sources.append(zipfile.ZipFile(io.BytesIO(outer.read(inner[0]))) if inner else outer)

    def __call__(self, bid):
        ns, path = bid.split(':', 1)
        rel = f'data/{ns}/worldgen/biome/{path}.json'
        for s in self.sources:
            try:
                return json.loads(s.read(rel) if isinstance(s, zipfile.ZipFile) else (s / rel).read_bytes())
            except (KeyError, OSError, ValueError):
                continue
        return {}


def read_yaml(path):
    try:
        return yaml.safe_load(Path(path).read_text('utf-8')) or {}
    except (OSError, yaml.YAMLError):
        return {}


def structures(starts, grounds, sea):
    """Structure markers; `grounds` holds the surface height at each structure's centre (None = not generated)."""
    out = []
    for (sid, x0, y0, z0, x1, y1, z1, pieces), ground in zip(starts, grounds):
        x, z = (x0 + x1) // 2, (z0 + z1) // 2
        cat = category(sid)
        if ground is None and (cat in ('ruin', 'dungeon') or y0 < sea - 10):
            continue  # just past the edge of the generated land and probably buried: not worth a hint
        ns = sid.split(':', 1)[0]
        out.append({'k': cat, 'n': structure_name(sid), 'p': PACKS.get(ns, title(ns.split('_'))), 'x': x, 'z': z,
                    'y': [y0, y1], 'b': [x0, z0, x1, z1], 's': pieces,
                    **({'o': 1} if ground is None else {'u': 1} if y1 < ground - 4 else {})})
    return sorted(out, key=lambda m: (m['k'], m['n']))


def server_markers(server: Path, w, names):
    """Spawn, warps, safe zones and waystones for one world, read from the plugins' own files."""
    plugins, markers, zones = server / 'plugins', [], []
    mv = read_yaml(plugins / 'Multiverse-Core' / 'worlds.yml').get(w['dimension'], {})
    spawn = mv.get('spawn-location') if isinstance(mv, dict) else None
    if isinstance(spawn, dict) and 'x' in spawn:
        markers.append({'k': 'spawn', 'n': names.get('spawn', 'Spawn'), 'x': spawn['x'], 'y': spawn['y'], 'z': spawn['z']})
    for f in sorted((plugins / 'Essentials' / 'warps').glob('*.yml')):
        d = read_yaml(f)
        if w['bukkit'] in (d.get('world-name'), d.get('world')) and 'x' in d:
            name = d.get('name', f.stem)
            near = [m for m in markers if m['k'] == 'spawn' and abs(m['x'] - d['x']) + abs(m['z'] - d['z']) < 4]
            if near:
                near[0]['c'] = f'/warp {name}'
            else:
                markers.append({'k': 'warp', 'n': names.get(name, title(name.split('_'))), 'c': f'/warp {name}',
                                'x': d['x'], 'y': d['y'], 'z': d['z']})
    for k, d in (read_yaml(plugins / 'QuickWaystones' / 'waystones.yml').get('Waystones') or {}).items():
        loc = d.get('location') or {}
        if loc.get('world') == w['bukkit'] and 'x' in loc:
            markers.append({'k': 'waystone', 'n': d.get('name') or f'Waystone {k}', 'x': loc['x'], 'y': loc['y'], 'z': loc['z']})
    regions = read_yaml(plugins / 'WorldGuard' / 'worlds' / w['bukkit'] / 'regions.yml').get('regions') or {}
    for rid, r in regions.items():
        f = r.get('flags') or {}
        if r.get('type') == 'cuboid':
            (ax, az), (bx, bz) = (r['min']['x'], r['min']['z']), (r['max']['x'] + 1, r['max']['z'] + 1)
            pts = [[ax, az], [bx, az], [bx, bz], [ax, bz]]
        elif r.get('type') == 'poly2d':
            pts = [[p['x'], p['z']] for p in r.get('points', [])]
        else:
            continue
        rules = [t for t, on in (('No building', f.get('build') == 'deny' or f.get('passthrough') == 'deny'),
                                 ('No PvP', f.get('pvp') == 'deny'),
                                 ('No hostile mobs', bool(f.get('deny-spawn')) or f.get('mob-spawning') == 'deny'),
                                 ('No explosions', 'deny' in (f.get('creeper-explosion'), f.get('other-explosion'),
                                                              f.get('tnt')))) if on]
        zones.append({'id': rid, 'n': names.get(rid, title(rid.split('_'))), 'pts': pts, 'r': rules,
                      'p': r.get('priority', 0)})
    return markers, zones


def labels(grid, x0, z0, cell, biome_ids):
    """Biome names placed at the most interior point of each sizeable area (grid: biome index per cell, -1 = none)."""
    same = np.ones(grid.shape, bool)
    p = np.pad(grid, 1, constant_values=-1)
    for n in (p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]):
        same &= n == grid
    dist, cur, d = np.zeros(grid.shape, np.int32), grid >= 0, 0
    while cur.any() and d < 64:
        d += 1
        dist[cur] = d
        q = np.pad(cur, 1)
        cur = cur & same & q[:-2, 1:-1] & q[2:, 1:-1] & q[1:-1, :-2] & q[1:-1, 2:]
    q = np.pad(dist, 1)
    peak = (dist >= 2) & np.all([dist >= q[1 + dy:q.shape[0] - 1 + dy, 1 + dx:q.shape[1] - 1 + dx]
                                 for dy in (-1, 0, 1) for dx in (-1, 0, 1)], 0)
    out = []
    for r, c in sorted(np.argwhere(peak).tolist(), key=lambda rc: -dist[rc[0], rc[1]]):
        b, rad = int(grid[r, c]), int(dist[r, c])
        bid = biome_ids[b]
        if 'cave' in bid or b == 0 or any((r - o[0]) ** 2 + (c - o[1]) ** 2 < (6 * o[3] if o[2] == b else 2.5) ** 2
                                          for o in out):
            continue
        out.append((r, c, b, rad))
    return [{'t': biome_name(biome_ids[b]), 'x': x0 + c * cell + cell // 2, 'z': z0 + r * cell + cell // 2,
             'r': rad * cell, **({'w': 1} if any(k in biome_ids[b] for k in ('ocean', 'river')) else {})}
            for r, c, b, rad in out]
