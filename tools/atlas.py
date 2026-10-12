#!/usr/bin/env python3
"""Wilds Atlas: turn a Paper server's worlds into the tiled web map under web/public/maps.

  python tools/atlas.py build [world ...] [--full]   render into web/public/maps (cached, incremental)
  python tools/atlas.py publish [--full]             build, then push the data and redeploy the site
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

if sys.version_info < (3, 11):
    sys.exit('Wilds Atlas needs Python 3.11 or newer.')
import tomllib  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import render  # noqa: E402
import scan  # noqa: E402
import world  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'web' / 'public' / 'maps'
CACHE = ROOT / 'cache'
B = render.B


def log(msg, end='\n'):
    print(msg, end=end, flush=True)


def load_config(path):
    cfg = tomllib.loads(Path(path).read_text('utf-8'))
    server = (Path(path).resolve().parent / cfg.get('server', '..')).resolve()
    worlds = []
    for w in cfg.get('worlds', []):
        w = {'name': w['id'].title(), 'dimension': f"minecraft:{w['id']}", 'bukkit': w['id'],
             'min_y': -64, 'height': 384, 'sea': 63, **w}
        ns, dim = w['dimension'].split(':', 1)
        w['dir'] = server / cfg.get('level', 'world') / 'dimensions' / ns / dim / 'region'
        worlds.append(w)
    return cfg, server, worlds


# ---------- workers ----------

_W = {}


def _init(cache, out, pal):
    _W.update(cache=cache, out=out, pal=pal)


@lru_cache(maxsize=24)
def _region(key):
    f = _W['cache'] / f'{key}.npz'
    return dict(np.load(f)) if f.exists() else None


def _render(key):
    rx, rz = map(int, key.split('_'))
    S = 512 + 2 * B
    win = {f: np.full((S, S), scan.MISSING if f in ('surf', 'floor') else 0, np.int16 if f in ('surf', 'floor') else np.uint16)
           for f in scan.FIELDS}
    span = {-1: (slice(512 - B, 512), slice(0, B)), 0: (slice(0, 512), slice(B, B + 512)), 1: (slice(0, B), slice(B + 512, S))}
    for dz in (-1, 0, 1):
        for dx in (-1, 0, 1):
            a = _region(f'{rx + dx}_{rz + dz}')
            if a is not None:
                for f in scan.FIELDS:
                    win[f][span[dz][1], span[dx][1]] = a[f][span[dz][0], span[dx][0]]
    out, P = _W['out'], _W['pal']
    X, Z = rx * 512 - B + np.arange(S), rz * 512 - B + np.arange(S)
    for style, rgba in render.render(win, P, X, Z).items():
        for j in (0, 1):
            for i in (0, 1):
                render.save(rgba[j * 256:j * 256 + 256, i * 256:i * 256 + 256],
                            out / 'tiles' / style / '0' / f'{2 * rx + i}_{2 * rz + j}.webp')
        render.save(render.shrink(rgba), out / 'tiles' / style / '-1' / f'{rx}_{rz}.webp')
    core = {f: win[f][B:-B, B:-B] for f in scan.FIELDS}
    path = out / 'data' / f'{rx}_{rz}.webp'
    if (core['surf'] != scan.MISSING).any():
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(render.hover(core, P), 'RGB').save(path, 'WEBP', lossless=True, quality=60, method=4)
    else:
        path.unlink(missing_ok=True)
    return key


def _pyramid(out, style, z, tiles):
    for px, py in tiles:
        canvas = np.zeros((512, 512, 4), np.uint8)
        for j in (0, 1):
            for i in (0, 1):
                t = render.load(out / 'tiles' / style / str(z + 1) / f'{2 * px + i}_{2 * py + j}.webp')
                if t is not None:
                    canvas[j * 256:j * 256 + 256, i * 256:i * 256 + 256] = t
        render.save(render.shrink(canvas), out / 'tiles' / style / str(z) / f'{px}_{py}.webp')


# ---------- build ----------

def build_world(w, server, cfg, jobs, full):
    t0, cache, out = time.time(), CACHE / w['id'], OUT / w['id']
    if not w['dir'].is_dir():
        log(f"  {w['id']}: no region files at {w['dir']}, skipped")
        return None
    cache.mkdir(parents=True, exist_ok=True)
    sf = cache / 'state.json'
    st = json.loads(sf.read_text('utf-8')) if sf.exists() and not full else {}
    shape = {'version': render.VERSION, 'min_y': w['min_y'], 'height': w['height'], 'sea': w['sea']}
    if any(st.get(k) != v for k, v in shape.items()):
        st = {}
    st = {**shape, 'blocks': st.get('blocks', ['minecraft:air']), 'biomes': st.get('biomes', ['minecraft:void']),
          'regions': st.get('regions', {}), 'min_zoom': st.get('min_zoom'), **({'v': st['v']} if 'v' in st else {})}
    files = {'_'.join(f.name.split('.')[1:3]): f for f in w['dir'].glob('r.*.*.mca') if f.stat().st_size > 8192}
    stamp = {k: [f.stat().st_mtime_ns, f.stat().st_size] for k, f in files.items()}
    todo = sorted(k for k in files if st['regions'].get(k, {}).get('stamp') != stamp[k])
    gone = [k for k in st['regions'] if k not in files]
    bidx = {b: i for i, b in enumerate(st['blocks'])}
    iidx = {b: i for i, b in enumerate(st['biomes'])}

    with ProcessPoolExecutor(jobs) as ex:
        futs = {ex.submit(scan.scan_region, files[k], w['min_y'], w['height']): k for k in todo}
        for n, fut in enumerate(as_completed(futs), 1):
            k = futs[fut]
            a, blocks, biomes, starts, chunks = fut.result()
            lb = np.array([bidx.setdefault(b, len(bidx)) for b in blocks], np.uint16)
            li = np.array([iidx.setdefault(b, len(iidx)) for b in biomes], np.uint16)
            a['top'], a['flo'], a['bio'] = lb[a['top']], lb[a['flo']], li[a['bio']]
            np.savez_compressed(cache / f'{k}.npz', **a)
            st['regions'][k] = {'stamp': stamp[k], 'chunks': chunks, 'structures': starts}
            log(f"\r  {w['id']}: read {n}/{len(todo)} regions", end='')
    for k in gone:
        st['regions'].pop(k)
        (cache / f'{k}.npz').unlink(missing_ok=True)
    st['blocks'], st['biomes'] = list(bidx), list(iidx)
    if todo:
        log('')

    keys = sorted(st['regions'], key=lambda k: tuple(map(int, k.split('_'))))
    rc = np.array([list(map(int, k.split('_'))) for k in keys]).reshape(-1, 2)
    if not len(rc):
        log(f"  {w['id']}: nothing generated yet")
        return None
    ext = int((rc.max(0) - rc.min(0) + 1).max()) * 512
    min_zoom = -max(1, math.ceil(math.log2(ext / 256)))
    styles_missing = any(not (out / 'tiles' / s).is_dir() for s in render.STYLES)
    if full or styles_missing or st['min_zoom'] != min_zoom:
        dirty = set(keys)
    else:
        near = {f'{x + dx}_{z + dz}' for k in todo + gone for x, z in [map(int, k.split('_'))]
                for dx in (-1, 0, 1) for dz in (-1, 0, 1)}
        dirty = near & set(keys)
    for k in gone:
        x, z = map(int, k.split('_'))
        for s in render.STYLES:
            for p in [f'0/{2 * x + i}_{2 * z + j}' for i in (0, 1) for j in (0, 1)] + [f'-1/{x}_{z}']:
                (out / 'tiles' / s / f'{p}.webp').unlink(missing_ok=True)
        (out / 'data' / f'{k}.webp').unlink(missing_ok=True)

    src = world.BiomeSource(server, cfg.get('level', 'world'))
    pal = render.palette(st['blocks'], st['biomes'], src, w['sea'], w['min_y'], w['height'])
    with ProcessPoolExecutor(jobs, initializer=_init, initargs=(cache, out, pal)) as ex:
        order = sorted(dirty, key=lambda k: tuple(map(int, k.split('_')))[::-1])
        for n, _ in enumerate(ex.map(_render, order, chunksize=2), 1):
            log(f"\r  {w['id']}: drew {n}/{len(dirty)} regions", end='')
        if dirty:
            log('')
        level = {tuple(map(int, k.split('_'))) for k in dirty | set(gone)}
        for z in range(-2, min_zoom - 1, -1):
            level = sorted({(x >> 1, y >> 1) for x, y in level})
            parts = [level[i::jobs] for i in range(jobs)]
            list(ex.map(_pyramid, *zip(*[(out, s, z, p) for s in render.STYLES for p in parts if p])))
    st['min_zoom'] = min_zoom
    st['v'] = int(time.time()) if dirty or gone or 'v' not in st else st['v']  # cache-buster, moves only on change
    sf.write_text(json.dumps(st, separators=(',', ':')), 'utf-8')

    # markers, zones and labels: one pass over the cached regions for biome samples and ground heights
    first = rc.min(0)
    grid = np.full(((rc[:, 1].max() - first[1] + 1) * 32, (rc[:, 0].max() - first[0] + 1) * 32), -1, np.int32)
    starts = [s for k in keys for s in st['regions'][k]['structures']]
    need, ground = {}, [None] * len(starts)
    for i, s in enumerate(starts):
        x, z = (s[1] + s[4]) // 2, (s[3] + s[6]) // 2
        need.setdefault(f'{x >> 9}_{z >> 9}', []).append((i, x & 511, z & 511))
    for k in keys:
        x, z = map(int, k.split('_'))
        with np.load(cache / f'{k}.npz') as a:
            s, b = a['surf'], a['bio']
        gz, gx = (z - first[1]) * 32, (x - first[0]) * 32
        grid[gz:gz + 32, gx:gx + 32] = np.where(s[8::16, 8::16] != scan.MISSING, b[8::16, 8::16].astype(np.int32), -1)
        for i, lx, lz in need.get(k, ()):
            ground[i] = None if s[lz, lx] == scan.MISSING else int(s[lz, lx])
    marks = world.structures(starts, ground, w['sea'])
    extra, zones = world.server_markers(server, w, cfg.get('names', {}))
    labels = world.labels(grid, int(first[0]) * 512, int(first[1]) * 512, 16, st['biomes'])
    tiles = sorted(p.stem for p in (out / 'tiles' / 'terrain' / '0').glob('*.webp'))
    tx = np.array([list(map(int, t.split('_'))) for t in tiles]).reshape(-1, 2)
    spawn = next(([m['x'], m['y'], m['z']] for m in extra if m['k'] == 'spawn'), None)
    meta = {'id': w['id'], 'name': w['name'], 'minY': w['min_y'], 'sea': w['sea'], 'minZoom': min_zoom,
            'v': st['v'], 'spawn': spawn,
            'bounds': [int(tx[:, 0].min()) * 256, int(tx[:, 1].min()) * 256,
                       int(tx[:, 0].max() + 1) * 256, int(tx[:, 1].max() + 1) * 256] if len(tx) else None,
            'tiles': tiles, 'data': sorted(p.stem for p in (out / 'data').glob('*.webp')),
            'styles': list(render.STYLES),
            'biomes': [{'n': world.biome_name(b), 'c': '#%02x%02x%02x' % tuple(int(v) for v in pal['brgb'][i])}
                       for i, b in enumerate(st['biomes'])],
            'blocks': [b.split(':', 1)[-1] for b in st['blocks']],
            'markers': extra + marks, 'zones': zones, 'labels': labels,
            'chunks': sum(r['chunks'] for r in st['regions'].values())}
    (out / 'world.json').write_text(json.dumps(meta, separators=(',', ':')), 'utf-8')
    log(f"  {w['id']}: {meta['chunks']:,} chunks, {len(tiles)} tiles, {len(marks)} structures, "
        f"{len(labels)} labels ({time.time() - t0:.0f}s)")
    return {'id': w['id'], 'name': w['name'], 'v': st['v']}


def build(cfg, server, worlds, only, jobs, full):
    log(f'Server: {server}')
    done = [r for w in worlds if not only or w['id'] in only if (r := build_world(w, server, cfg, jobs, full))]
    OUT.mkdir(parents=True, exist_ok=True)
    old = json.loads((OUT / 'index.json').read_text('utf-8')) if (OUT / 'index.json').exists() else {}
    if only:  # keep the other worlds listed
        order = [w['id'] for w in worlds]
        done = [x for x in old.get('worlds', []) if x['id'] not in only and (OUT / x['id']).is_dir()] + done
        done.sort(key=lambda x: order.index(x['id']) if x['id'] in order else 99)
    else:  # drop maps of worlds no longer in the config
        for d in OUT.iterdir():
            if d.is_dir() and d.name not in {x['id'] for x in done}:
                shutil.rmtree(d)
    newest = max((x.get('v', 0) for x in done), default=0)
    index = {'title': cfg.get('title', 'Wilds Atlas'), 'subtitle': cfg.get('subtitle', ''),
             'updated': datetime.fromtimestamp(newest, timezone.utc).isoformat(timespec='seconds'), 'worlds': done}
    (OUT / 'index.json').write_text(json.dumps(index, indent=1), 'utf-8')
    return index


# ---------- publish ----------

def git(*args, env=None, cwd=ROOT, check=True, quiet=True):
    r = subprocess.run(['git', *args], cwd=cwd, env=env, text=True, capture_output=quiet)
    if check and r.returncode:
        sys.exit(f"git {' '.join(args)} failed:\n{(r.stderr or '').strip()}")
    return (r.stdout or '').strip()


def publish(index):
    if not index['worlds']:
        sys.exit('Nothing to publish: no world was rendered.')
    remote = git('remote', 'get-url', 'origin')
    who = [] if git('config', 'user.email', check=False) else ['-c', 'user.name=Wilds Atlas', '-c', 'user.email=atlas@localhost']
    repo = CACHE / 'map-data.git'
    if not repo.exists():
        git('init', '-q', '--bare', str(repo))
    env = {**os.environ, 'GIT_DIR': str(repo), 'GIT_WORK_TREE': str(OUT)}
    git('fetch', '-q', remote, '+refs/heads/map-data:refs/heads/map-data', env=env, check=False)
    git('add', '-A', '.', env=env, cwd=OUT)
    tree = git('write-tree', env=env, cwd=OUT)
    if git('rev-parse', '-q', '--verify', 'refs/heads/map-data^{tree}', env=env, check=False) != tree:
        commit = git(*who, 'commit-tree', tree, '-m', f"Map data {index['updated']}", env=env)
        log('Uploading map data...')
        git('push', '-f', remote, f'{commit}:refs/heads/map-data', env=env, quiet=False)
        git('update-ref', 'refs/heads/map-data', commit, env=env)
    commit = git('rev-parse', 'refs/heads/map-data', env=env)
    lock = ROOT / 'data.lock'
    if not lock.exists() or lock.read_text().strip() != commit:
        git('pull', '-q', '--rebase', '--autostash', check=False)
        lock.write_text(commit + '\n')
        git('add', 'data.lock')
        git(*who, 'commit', '-q', '-m', f"Update map ({', '.join(w['name'] for w in index['worlds'])})", '--', 'data.lock')
        git('push', '-q', quiet=False)
        log('Published. GitHub rebuilds the site in a minute or two.')
    else:
        log('The map data is already up to date.')


def main():
    ap = argparse.ArgumentParser(prog='atlas', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=('build', 'publish'))
    ap.add_argument('worlds', nargs='*', help='only these world ids (build only)')
    ap.add_argument('-c', '--config', default=ROOT / 'config.toml')
    ap.add_argument('-j', '--jobs', type=int, default=max(1, (os.cpu_count() or 2) // 2), help='worker processes')
    ap.add_argument('--full', action='store_true', help='ignore the cache and redo everything')
    args = ap.parse_args()
    cfg, server, worlds = load_config(args.config)
    index = build(cfg, server, worlds, set(args.worlds) if args.command == 'build' else set(), args.jobs, args.full)
    if args.command == 'publish':
        publish(index)


if __name__ == '__main__':
    main()
