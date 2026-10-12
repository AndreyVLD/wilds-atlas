"""Read Anvil region files into per-column arrays: surface height, sea floor, top block, floor block, biome."""
import gzip
import struct
import zlib
from pathlib import Path

import numpy as np

MISSING = -32768
FIELDS = ('surf', 'floor', 'top', 'flo', 'bio')
_ARR = {7: ('i1', 1), 11: ('>i4', 4), 12: ('>i8', 8)}
_NUM = {1: 1, 2: 2, 3: 4, 4: 8}
_SIZE = {**_NUM, 5: 4, 6: 8}
_DECOMP = {1: gzip.decompress, 2: zlib.decompress, 3: bytes}
_ZZ, _XX = np.divmod(np.arange(256), 16)
_CHUNK = {b'Status': None, b'Heightmaps': {b'WORLD_SURFACE': None, b'OCEAN_FLOOR': None},
          b'sections': {b'Y': None, b'block_states': {b'palette': {b'Name': None}, b'data': None}, b'biomes': None},
          b'structures': {b'starts': {b'*': {b'id': None, b'Children': {b'BB': None}}}}}


def nbt(b: bytes, schema=None):
    """Minimal NBT reader: compounds -> dict, lists -> list, arrays -> numpy views.
    `schema` maps (bytes) keys to sub-schemas (None = keep everything, b'*' = any key); other keys are skipped."""
    def skip(t, p):
        if t == 10:
            while (t := b[p]) != 0:
                p = skip(t, p + 3 + int.from_bytes(b[p + 1:p + 3], 'big'))
            return p + 1
        if t == 9:
            et, n, p = b[p], int.from_bytes(b[p + 1:p + 5], 'big', signed=True), p + 5
            if et in _SIZE:
                return p + max(n, 0) * _SIZE[et]
            for _ in range(n):
                p = skip(et, p)
            return p
        if t == 8:
            return p + 2 + int.from_bytes(b[p:p + 2], 'big')
        if t in _ARR:
            return p + 4 + int.from_bytes(b[p:p + 4], 'big', signed=True) * _ARR[t][1]
        return p + _SIZE[t]

    def val(t, p, sch):
        if t == 10:
            d = {}
            while (t := b[p]) != 0:
                n = int.from_bytes(b[p + 1:p + 3], 'big')
                k, p = b[p + 3:p + 3 + n], p + 3 + n
                if sch is None or k in sch or b'*' in sch:
                    d[k.decode('utf-8', 'replace')], p = val(t, p, None if sch is None else sch.get(k, sch.get(b'*')))
                else:
                    p = skip(t, p)
            return d, p + 1
        if t == 8:
            n = int.from_bytes(b[p:p + 2], 'big')
            return b[p + 2:p + 2 + n].decode('utf-8', 'replace'), p + 2 + n
        if t == 9:
            et, n, p = b[p], int.from_bytes(b[p + 1:p + 5], 'big', signed=True), p + 5
            out = []
            for _ in range(n):
                v, p = val(et, p, sch)
                out.append(v)
            return out, p
        if t in _ARR:
            dt, size = _ARR[t]
            n = int.from_bytes(b[p:p + 4], 'big', signed=True)
            return np.frombuffer(b, dt, n, p + 4), p + 4 + n * size
        if t in _NUM:
            return int.from_bytes(b[p:p + _NUM[t]], 'big', signed=True), p + _NUM[t]
        return struct.unpack_from('>f' if t == 5 else '>d', b, p)[0], p + _SIZE[t]
    return val(b[0], 3 + int.from_bytes(b[1:3], 'big'), schema)[0]


def chunks(path: Path):
    data = path.read_bytes()
    if len(data) < 8192:
        return
    rx, rz = map(int, path.name.split('.')[1:3])
    loc = np.frombuffer(data, '>u4', 1024)
    for i in np.flatnonzero(loc):
        start = int(loc[i] >> 8) * 4096
        if start + 5 > len(data):
            continue
        n, ct = int.from_bytes(data[start:start + 4], 'big'), data[start + 4]
        raw = data[start + 5:start + 4 + n]
        try:
            if ct & 128:  # oversized chunk kept in its own file
                raw = (path.parent / f'c.{rx * 32 + i % 32}.{rz * 32 + i // 32}.mcc').read_bytes()
            yield int(i), nbt(_DECOMP[ct & 127](raw), _CHUNK)
        except Exception:  # half-written or unsupported (lz4) chunk
            continue


def packed(longs, bits, idx):
    per = 64 // bits
    words = np.asarray(longs).view('>u8')[idx // per]
    return ((words >> ((idx % per) * bits).astype(np.uint64)) & np.uint64((1 << bits) - 1)).astype(np.int64)


def pick(secs, ys, key, pal):
    """Palette index (into `pal`) of the block/biome at height ys for each of a chunk's 256 columns."""
    out = np.zeros(256, np.int64)
    sy = ys >> 4
    for y in np.unique(sy):
        st = secs.get(int(y), {}).get(key)
        if not st or not st.get('palette'):
            continue
        names = st['palette']
        lut = np.array([pal.setdefault(p['Name'] if isinstance(p, dict) else p, len(pal)) for p in names])
        m = sy == y
        if len(names) == 1 or st.get('data') is None:
            out[m] = lut[0]
            continue
        ly, z, x = ys[m] & 15, _ZZ[m], _XX[m]
        if key == 'block_states':
            out[m] = lut[packed(st['data'], max(4, (len(names) - 1).bit_length()), (ly * 16 + z) * 16 + x)]
        else:
            out[m] = lut[packed(st['data'], (len(names) - 1).bit_length(), ((ly >> 2) * 4 + (z >> 2)) * 4 + (x >> 2))]
    return out


def scan_region(path, min_y=-64, height=384):
    """-> (arrays with region-local palette indices, block names, biome names, structures [id, x0, y0, z0, x1, y1, z1, pieces], chunks)"""
    path = Path(path)
    bits = max(1, height.bit_length())
    a = {'surf': np.full((512, 512), MISSING, np.int16), 'floor': np.full((512, 512), MISSING, np.int16),
         **{k: np.zeros((512, 512), np.uint16) for k in ('top', 'flo', 'bio')}}
    blocks, biomes, starts, n = {'minecraft:air': 0}, {'minecraft:void': 0}, [], 0
    idx = np.arange(256)
    for i, c in chunks(path):
        for k, s in (c.get('structures', {}).get('starts') or {}).items():
            bb = np.array([ch['BB'] for ch in s.get('Children', []) if len(ch.get('BB', ())) == 6], np.int64).reshape(-1, 6)
            if s.get('id', k) != 'INVALID' and len(bb):
                starts.append([s.get('id', k), *bb[:, :3].min(0).tolist(), *bb[:, 3:].max(0).tolist(), len(bb)])
        hm = c.get('Heightmaps', {})
        if c.get('Status') != 'minecraft:full' or 'WORLD_SURFACE' not in hm or 'OCEAN_FLOOR' not in hm:
            continue
        ws = packed(hm['WORLD_SURFACE'], bits, idx) + min_y - 1
        of = packed(hm['OCEAN_FLOOR'], bits, idx) + min_y - 1
        secs = {int(s['Y']): s for s in c.get('sections', [])}
        sl = np.s_[(i // 32) * 16:(i // 32) * 16 + 16, (i % 32) * 16:(i % 32) * 16 + 16]
        for k, v in (('surf', ws), ('floor', of), ('top', pick(secs, ws, 'block_states', blocks)),
                     ('flo', pick(secs, of, 'block_states', blocks)), ('bio', pick(secs, ws, 'biomes', biomes))):
            a[k][sl] = v.reshape(16, 16)
        n += 1
    return a, list(blocks), list(biomes), starts, n
