"""Colour rules, the four map styles and tile output."""
import colorsys

import numpy as np
from PIL import Image

from scan import MISSING

VERSION = 1   # bump to force a full re-render
B = 8         # border borrowed from neighbouring regions (shading, coasts, contours, stamps)
STYLES = ('terrain', 'parchment', 'biomes', 'height')

DYE = {'white': (233, 236, 236), 'light_gray': (142, 142, 134), 'gray': (62, 68, 71), 'black': (21, 21, 26),
       'brown': (114, 71, 40), 'red': (160, 39, 34), 'orange': (240, 118, 19), 'yellow': (248, 197, 39),
       'lime': (112, 185, 25), 'green': (84, 109, 27), 'cyan': (21, 137, 145), 'light_blue': (58, 175, 217),
       'blue': (53, 57, 157), 'purple': (121, 42, 172), 'magenta': (189, 68, 179), 'pink': (237, 141, 172)}
TERRACOTTA = {'white': (209, 178, 161), 'light_gray': (135, 106, 97), 'gray': (57, 42, 35), 'black': (37, 22, 16),
              'brown': (77, 51, 35), 'red': (143, 61, 46), 'orange': (161, 83, 37), 'yellow': (186, 133, 35),
              'lime': (103, 117, 52), 'green': (76, 83, 42), 'cyan': (86, 91, 91), 'light_blue': (113, 108, 137),
              'blue': (74, 59, 91), 'purple': (118, 70, 86), 'magenta': (149, 88, 108), 'pink': (161, 78, 78)}
WOOD = {'oak': (162, 130, 78), 'spruce': (114, 84, 48), 'birch': (192, 175, 121), 'jungle': (160, 115, 80),
        'acacia': (168, 90, 50), 'dark_oak': (66, 43, 20), 'mangrove': (117, 54, 48), 'cherry': (226, 178, 172),
        'pale_oak': (228, 218, 216), 'bamboo': (193, 173, 80), 'crimson': (101, 48, 70), 'warped': (43, 104, 99)}
FIXED = {
    'lava': (207, 94, 16), 'snow': (243, 248, 249), 'snow_block': (243, 248, 249), 'powder_snow': (246, 250, 252),
    'ice': (145, 183, 253), 'packed_ice': (141, 180, 250), 'blue_ice': (116, 167, 253), 'frosted_ice': (140, 181, 252),
    'stone': (125, 125, 125), 'smooth_stone': (158, 158, 158), 'cobblestone': (127, 127, 127),
    'mossy_cobblestone': (110, 118, 94), 'stone_bricks': (122, 121, 122), 'mossy_stone_bricks': (115, 121, 105),
    'cracked_stone_bricks': (118, 117, 118), 'granite': (149, 103, 85), 'diorite': (188, 188, 188),
    'andesite': (136, 136, 136), 'calcite': (223, 224, 220), 'tuff': (108, 109, 102), 'deepslate': (80, 80, 82),
    'cobbled_deepslate': (77, 77, 80), 'dripstone_block': (134, 107, 92), 'pointed_dripstone': (129, 102, 89),
    'gravel': (131, 127, 126), 'sand': (219, 207, 163), 'red_sand': (190, 102, 33), 'sandstone': (216, 203, 155),
    'red_sandstone': (186, 99, 29), 'clay': (160, 166, 179), 'mud': (60, 57, 60), 'packed_mud': (142, 106, 79),
    'mud_bricks': (137, 103, 79), 'dirt': (134, 96, 67), 'coarse_dirt': (119, 85, 59), 'rooted_dirt': (144, 103, 76),
    'dirt_path': (148, 121, 65), 'farmland': (110, 74, 45), 'podzol': (106, 76, 39), 'mycelium': (111, 98, 101),
    'moss_block': (89, 110, 45), 'moss_carpet': (89, 110, 45), 'pale_moss_block': (107, 115, 104),
    'pale_moss_carpet': (107, 115, 104), 'leaf_litter': (148, 112, 63), 'terracotta': (152, 94, 67),
    'netherrack': (111, 54, 53), 'magma_block': (142, 63, 31), 'obsidian': (15, 11, 25), 'basalt': (73, 72, 77),
    'blackstone': (42, 36, 41), 'bedrock': (85, 85, 85), 'glow_lichen': (112, 138, 121), 'cobweb': (220, 224, 226),
    'brown_mushroom_block': (149, 111, 81), 'red_mushroom_block': (200, 46, 45), 'mushroom_stem': (203, 196, 185),
    'brown_mushroom': (154, 117, 86), 'red_mushroom': (214, 54, 58), 'hay_block': (166, 138, 12),
    'pumpkin': (198, 118, 24), 'melon': (111, 145, 30), 'cactus': (85, 127, 43), 'sugar_cane': (148, 192, 101),
    'bamboo': (93, 144, 19), 'wheat': (169, 160, 75), 'carrots': (110, 160, 40), 'potatoes': (110, 160, 40),
    'beetroots': (110, 150, 40), 'sweet_berry_bush': (68, 99, 43), 'dead_bush': (140, 104, 60),
    'iron_bars': (136, 139, 135), 'campfire': (96, 77, 53), 'cherry_leaves': (231, 167, 199),
    'pale_oak_leaves': (138, 147, 138), 'azalea_leaves': (93, 125, 46), 'flowering_azalea_leaves': (115, 125, 75),
    'quartz_block': (235, 229, 222), 'smooth_quartz': (235, 229, 222), 'bricks': (150, 97, 83),
    'nether_bricks': (44, 21, 26), 'prismarine': (99, 156, 151), 'sea_lantern': (172, 199, 190),
    'glass': (192, 216, 222), 'bookshelf': (117, 94, 59), 'seagrass': (40, 110, 60), 'kelp': (60, 120, 40),
    'lily_pad': (32, 128, 48), 'spruce_leaves': (70, 110, 72), 'birch_leaves': (104, 136, 70)}
FLOWERS = {'dandelion': (240, 210, 60), 'poppy': (200, 40, 30), 'blue_orchid': (40, 160, 220), 'allium': (180, 120, 220),
           'azure_bluet': (225, 230, 235), 'red_tulip': (210, 50, 30), 'orange_tulip': (235, 120, 40),
           'white_tulip': (230, 235, 230), 'pink_tulip': (235, 170, 200), 'oxeye_daisy': (235, 235, 210),
           'cornflower': (70, 100, 220), 'lily_of_the_valley': (240, 240, 240), 'wither_rose': (40, 40, 30),
           'sunflower': (245, 200, 40), 'lilac': (200, 150, 210), 'rose_bush': (190, 40, 40), 'peony': (230, 170, 215),
           'wildflowers': (235, 215, 80), 'pink_petals': (240, 160, 200), 'torchflower': (235, 130, 40),
           'pitcher_plant': (110, 150, 200), 'open_eyeblossom': (240, 140, 40), 'closed_eyeblossom': (120, 110, 110),
           'cactus_flower': (240, 120, 160)}
COLORS = sorted(DYE, key=len, reverse=True)
SUFFIXES = ('_stairs', '_slab', '_wall', '_fence_gate', '_fence', '_trapdoor', '_door', '_button', '_pressure_plate',
            '_wall_sign', '_sign', '_carpet', '_wool', '_concrete_powder', '_concrete')

KINDS = ('ground', 'water', 'tree', 'built', 'path', 'farm', 'snow', 'sand', 'lava', 'rock', 'ice')
K = {k: i for i, k in enumerate(KINDS)}
BUILT = ('planks', 'brick', 'cobblestone', 'glass', 'wool', 'concrete', 'polished_', 'chiseled_', 'cut_', 'smooth_',
         'glazed', 'quartz', 'purpur', 'prismarine', 'tiles', 'fence', 'door', 'lantern', 'torch', '_bed', 'barrel',
         'chest', 'table', 'furnace', 'smoker', 'bookshelf', 'hay_block', 'rail', 'campfire', 'bell', 'anvil', 'banner',
         'carpet', 'iron_bars', 'chain', 'ladder', 'scaffolding', 'slab', 'stairs', '_wall', 'sign', 'pot', 'cauldron',
         'lectern', 'loom', 'stonecutter', 'grindstone', 'composter', 'beehive', 'copper', 'iron_block', 'gold_block',
         'stripped_')
ROCK = ('stone', 'granite', 'diorite', 'andesite', 'tuff', 'calcite', 'deepslate', 'gravel', 'basalt', 'blackstone',
        'dripstone', 'terracotta', '_ore', 'obsidian', 'bedrock', 'netherrack', 'clay', 'mud')


def kind(n):
    if n in FLOWERS or n in ('moss_carpet', 'pale_moss_carpet', 'grass_block'):
        return K['ground']
    if n in ('water', 'bubble_column', 'seagrass', 'tall_seagrass', 'kelp', 'kelp_plant'):
        return K['water']
    if n in ('lava', 'magma_block'):
        return K['lava']
    if n in ('ice', 'packed_ice', 'blue_ice', 'frosted_ice'):
        return K['ice']
    if n in ('snow', 'snow_block', 'powder_snow'):
        return K['snow']
    if n in ('sand', 'red_sand', 'suspicious_sand', 'sandstone', 'red_sandstone'):
        return K['sand']
    if n == 'dirt_path':
        return K['path']
    if n == 'mossy_cobblestone':
        return K['rock']
    if n == 'farmland' or n.endswith(('_crop', '_stem')) or n in ('wheat', 'carrots', 'potatoes', 'beetroots'):
        return K['farm']
    if n.endswith(('leaves', '_log', '_wood', 'mushroom_block')) and not n.startswith('stripped_') \
            or n in ('mushroom_stem', 'mangrove_roots', 'azalea', 'flowering_azalea', 'bamboo', 'cocoa', 'vine'):
        return K['tree']
    if any(k in n for k in BUILT):
        return K['built']
    if any(k in n for k in ROCK):
        return K['rock']
    return K['ground']


def block_rule(name):
    """-> ('fixed', rgb) | ('grass', k) | ('foliage', k) | ('flower', rgb) | ('water',)"""
    n = name.split(':', 1)[-1]
    if n in ('water', 'bubble_column'):
        return ('water',)
    if n == 'grass_block':
        return ('grass', 0.92)
    if n in ('short_grass', 'tall_grass', 'fern', 'large_fern', 'bush', 'short_dry_grass', 'tall_dry_grass'):
        return ('grass', 0.85)
    if n in ('oak_leaves', 'jungle_leaves', 'acacia_leaves', 'dark_oak_leaves', 'mangrove_leaves', 'vine'):
        return ('foliage', 0.74)
    if n in FLOWERS:
        return ('flower', FLOWERS[n])
    base = n
    for suf in SUFFIXES:
        if base.endswith(suf):
            base = base[:-len(suf)]
            break
    base = base.removeprefix('waxed_')
    for key in (n, base):
        if key in FIXED:
            return ('fixed', FIXED[key])
    if 'terracotta' in n:
        return ('fixed', next((TERRACOTTA[c] for c in COLORS if n.startswith(c + '_')), FIXED['terracotta']))
    if 'copper' in n:
        return ('fixed', next((rgb for k, rgb in (('oxidized', (82, 162, 132)), ('weathered', (108, 153, 110)),
                                                  ('exposed', (161, 125, 103))) if k in n), (191, 107, 80)))
    for c in COLORS:
        if n.startswith(c + '_'):
            return ('fixed', DYE[c])
    for w in sorted(WOOD, key=len, reverse=True):
        if n.startswith((w + '_', 'stripped_' + w + '_')):
            dark = n.endswith(('_log', '_wood', '_stem'))
            return ('fixed', tuple(int(v * (0.85 if dark else 1)) for v in WOOD[w]))
    for key, rgb in (('deepslate', (80, 80, 84)), ('blackstone', (42, 36, 41)), ('sandstone', (216, 203, 155)),
                     ('quartz', (235, 229, 222)), ('brick', (140, 90, 74)), ('prismarine', (99, 156, 151)),
                     ('cobblestone', (127, 127, 127)), ('stone', (125, 125, 125)), ('ore', (125, 125, 125)),
                     ('glass', (192, 216, 222)), ('leaves', (80, 120, 50)), ('log', (110, 85, 55)),
                     ('planks', (150, 120, 75)), ('mushroom', (150, 110, 85)), ('coral', (200, 90, 140)),
                     ('sculk', (13, 30, 36)), ('amethyst', (133, 97, 191))):
        if key in n:
            return ('fixed', rgb)
    return ('fixed', (136, 136, 136))


BIOME_COLORS = (('lavender', (178, 140, 220)), ('sakura', (242, 167, 195)), ('cherry', (242, 167, 195)),
                ('blooming', (166, 205, 102)), ('frozen_ocean', (150, 170, 220)), ('frozen', (226, 236, 246)),
                ('snowy', (226, 236, 246)), ('ice', (190, 220, 245)), ('peaks', (205, 210, 220)),
                ('rocky', (150, 140, 128)), ('haze', (150, 156, 170)), ('volcanic', (90, 70, 70)),
                ('cliff', (160, 150, 140)), ('pale_garden', (166, 172, 164)), ('dark_forest', (46, 84, 36)),
                ('cloud_forest', (88, 140, 118)), ('lush', (92, 186, 74)), ('old_growth_spruce', (52, 92, 70)),
                ('old_growth_pine', (70, 104, 74)), ('taiga', (84, 120, 88)), ('windswept', (94, 124, 98)),
                ('forested', (60, 120, 56)), ('birch', (120, 170, 80)), ('forest', (78, 138, 60)),
                ('jungle', (44, 140, 30)), ('swamp', (88, 98, 60)), ('mangrove', (70, 100, 50)),
                ('savanna', (170, 160, 80)), ('badlands', (196, 106, 54)), ('desert', (222, 202, 140)),
                ('beach', (228, 214, 160)), ('shore', (228, 214, 160)), ('river', (62, 123, 214)),
                ('deep', (32, 62, 150)), ('ocean', (44, 88, 190)), ('mushroom', (150, 110, 160)),
                ('meadow', (150, 200, 110)), ('temperate', (110, 158, 82)), ('highlands', (128, 162, 96)),
                ('plains', (140, 190, 100)), ('valley', (120, 180, 92)), ('cave', (110, 100, 120)),
                ('mountain', (150, 146, 136)), ('hills', (120, 160, 90)), ('grove', (170, 200, 190)),
                ('slopes', (210, 220, 228)))
GRASS = np.array(((191, 183, 85), (128, 180, 151), (71, 205, 51)), np.float32)
FOLIAGE = np.array(((174, 164, 42), (96, 161, 123), (26, 191, 0)), np.float32)


def hexrgb(v):
    if v is None:
        return None
    v = int(v.lstrip('#'), 16) if isinstance(v, str) else int(v)
    return np.array(((v >> 16) & 255, (v >> 8) & 255, v & 255), np.float32)


def climate(tri, temp, down):
    """Approximation of the vanilla grass/foliage colour-map triangle."""
    t = min(max(temp, 0.0), 1.0)
    return np.clip(tri[0] + (tri[1] - tri[0]) * (1 - t) + (tri[2] - tri[0]) * min(max(down, 0.0), 1.0) * t, 0, 255)


def biome_color(bid):
    p = bid.split(':', 1)[-1]
    for k, c in BIOME_COLORS:
        if k in p:
            return c
    h = sum(map(ord, bid)) * 2654435761 % 360 / 360
    return tuple(int(v * 255) for v in colorsys.hls_to_rgb(h, 0.55, 0.45))


def palette(blocks, biomes, biome_json, sea, min_y, height):
    """Lookup tables shared by every region of a world."""
    info = []
    for b in biomes:
        j = biome_json(b)
        eff, temp, down = j.get('effects', {}), float(j.get('temperature', 0.8)), float(j.get('downfall', 0.4))
        grass = hexrgb(eff.get('grass_color'))
        if grass is None:
            grass = climate(GRASS, temp, down)
            if eff.get('grass_color_modifier') == 'swamp':
                grass = np.array((106, 112, 57), np.float32)
            elif eff.get('grass_color_modifier') == 'dark_forest':
                grass = (grass + np.array((40, 52, 10), np.float32)) / 2
        foliage = hexrgb(eff.get('foliage_color'))
        info.append((grass, climate(FOLIAGE, temp, down) if foliage is None else foliage,
                     hexrgb(eff.get('water_color')) if eff.get('water_color') else np.array((63, 118, 228), np.float32)))
    rules = [block_rule(b) for b in blocks]
    grass, foliage, water = (np.array(x, np.float32) for x in zip(*info))
    lut = np.zeros((len(blocks), len(biomes), 3), np.float32)
    for i, (t, *v) in enumerate(rules):
        lut[i] = (v[0] if t == 'fixed' else grass * v[0] if t == 'grass' else foliage * v[0] if t == 'foliage'
                  else grass * 0.42 + np.array(v[0]) * 0.5 if t == 'flower' else water)
    brgb = np.array([biome_color(b) for b in biomes], np.float32)
    bwater = np.array([any(k in b for k in ('ocean', 'river')) for b in biomes])
    return {'lut': lut, 'kind': np.array([kind(b.split(':', 1)[-1]) for b in blocks], np.uint8),
            'water': np.array([r[0] == 'water' for r in rules]), 'brgb': brgb, 'bwater': bwater,
            'sea': sea, 'min_y': min_y, 'top_y': min_y + height}


# ---------- helpers ----------

def mix(a, b, t):
    t = np.asarray(t, np.float32)
    return a + (np.asarray(b, np.float32) - a) * (t[..., None] if t.ndim else t)


def shifts(a, fill):
    p = np.pad(a, 1, constant_values=fill)
    return p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]


def hillshade(h):
    p = np.pad(h, 1, mode='edge')
    gx, gz = (p[1:-1, 2:] - p[1:-1, :-2]) / 2, (p[2:, 1:-1] - p[:-2, 1:-1]) / 2
    lx, ly, lz = np.array((-1, 1.4, -1)) / np.linalg.norm((-1, 1.4, -1))
    lam = (-gx * lx + ly - gz * lz) / np.sqrt(gx * gx + 1 + gz * gz)
    return np.clip(0.42 + 0.78 * lam / ly, 0.45, 1.25).astype(np.float32)


def hsh(x, z, seed=0):
    h = (x.astype(np.int64) * 374761393 + z.astype(np.int64) * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return h ^ (h >> 16)


def vnoise(X, Z, cell, seed):
    """Smooth value noise in [-1, 1] on world coordinates (X: columns, Z: rows)."""
    gx, fx = np.divmod(X, cell)
    gz, fz = np.divmod(Z, cell)
    gx, gz, fx, fz = gx[None, :], gz[:, None], (fx / cell)[None, :], (fz / cell)[:, None]
    fx, fz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
    c = [(hsh(gx + i, gz + j, seed) & 1023) / 511.5 - 1 for j in (0, 1) for i in (0, 1)]
    return ((c[0] * (1 - fx) + c[1] * fx) * (1 - fz) + (c[2] * (1 - fx) + c[3] * fx) * fz).astype(np.float32)


def stamp(col, mask, X, Z, spacing, glyph, seed):
    """Scatter a small glyph over `mask` on a jittered world-aligned grid (seamless across tiles)."""
    S = col.shape[0]
    gx = np.arange(X[0] // spacing - 1, X[-1] // spacing + 2)
    gz = np.arange(Z[0] // spacing - 1, Z[-1] // spacing + 2)
    GX, GZ = np.meshgrid(gx, gz)
    cx = (GX * spacing + hsh(GX, GZ, seed) % (spacing - 2) - X[0]).ravel()
    cz = (GZ * spacing + hsh(GX, GZ, seed + 1) % (spacing - 2) - Z[0]).ravel()
    ok = (cx >= 0) & (cx < S) & (cz >= 0) & (cz < S)
    cx, cz = cx[ok], cz[ok]
    keep = mask[cz, cx]
    cx, cz = cx[keep], cz[keep]
    for dz, dx, rgb, a in glyph:
        x, z = cx + dx, cz + dz
        ok = (x >= 0) & (x < S) & (z >= 0) & (z < S)
        col[z[ok], x[ok]] = mix(col[z[ok], x[ok]], rgb, a)


def _glyph(rows, colors):
    h = len(rows) // 2
    return [(j - h, i - len(r) // 2, *colors[ch]) for j, r in enumerate(rows) for i, ch in enumerate(r) if ch in colors]


TREE = _glyph((' ooo ', 'oOOOo', 'oOOOo', ' ooo ', '  t  '),
              {'o': ((58, 74, 42), 0.85), 'O': ((132, 146, 92), 0.75), 't': ((92, 66, 42), 0.9)})
DOT = [(0, 0, (150, 120, 70), 0.6)]


# ---------- styles ----------

def prepare(w, P):
    valid = w['surf'] != MISSING
    h = np.where(valid, w['surf'], np.nan).astype(np.float32)
    for _ in range(B):
        m = np.isnan(h)
        if not m.any():
            break
        n = shifts(h, np.nan)
        h = np.where(m, np.fmax(np.fmax(n[0], n[1]), np.fmax(n[2], n[3])), h)
    h = np.where(np.isnan(h), P['sea'], h)
    water = P['water'][w['top']] & valid
    depth = np.where(water, np.clip(w['surf'].astype(np.int32) - w['floor'], 0, 255), 0)
    return {**w, 'valid': valid, 'h': h, 'water': water, 'depth': depth, 'shade': hillshade(h)}


def terrain(c, P):
    base = P['lut'][c['top'], c['bio']]
    rgb = base * c['shade'][..., None]
    floor = P['lut'][c['flo'], c['bio']] * np.clip(c['shade'], 0.8, 1.1)[..., None]
    a = 0.45 + 0.5 * (1 - np.exp(-c['depth'] / 7.0))
    rgb = np.where(c['water'][..., None], mix(floor, base, a), rgb)
    return rgb * (0.94 + 0.12 * np.clip((c['h'] - P['sea']) / 300, 0, 1))[..., None]


PAPER, INK, UMBER = (233, 219, 183), (62, 44, 30), (186, 152, 104)
TINT = {K['tree']: ((150, 156, 104), 0.32), K['built']: ((132, 72, 48), 0.88), K['path']: ((170, 134, 90), 0.6),
        K['snow']: ((248, 245, 236), 0.75), K['sand']: ((228, 206, 150), 0.5), K['lava']: ((196, 82, 36), 0.9),
        K['rock']: ((170, 160, 140), 0.3), K['ice']: ((198, 216, 216), 0.6), K['farm']: ((214, 196, 128), 0.5)}


def parchment(c, P, X, Z):
    k, land, water = P['kind'][c['top']], c['valid'] & ~c['water'], c['water']
    hn = np.clip((c['h'] - P['sea']) / max(P['top_y'] - P['sea'], 64) * 2.2, 0, 1)
    col = np.broadcast_to(np.array(PAPER, np.float32), c['h'].shape + (3,)) * (1 + (c['shade'] - 1) * 0.65)[..., None]
    col = mix(col, UMBER, hn * 0.45)
    for kk, (rgb, a) in TINT.items():
        col = np.where((k == kk)[..., None], mix(col, rgb, a), col)
    farm = (k == K['farm']) & (Z[:, None] % 3 == 0)
    col = np.where(farm[..., None], mix(col, (176, 150, 90), 0.5), col)
    # sea: wash by depth, coastline in ink, "water lining" parallel to the shore
    dist, front, seen = np.zeros(land.shape, np.uint8), land.copy(), land.copy()
    for i in range(1, 13):
        n = shifts(front, False)
        front = (n[0] | n[1] | n[2] | n[3]) & ~seen & water
        dist[front], seen = i, seen | front
    col = np.where(water[..., None], mix(np.array((178, 198, 190), np.float32), (126, 156, 164),
                                         np.clip(c['depth'] / 24, 0, 1)), col)
    col = np.where((water & np.isin(dist, (4, 8)))[..., None], mix(col, (92, 120, 128), 0.45), col)
    n = shifts(water, False)
    coast = land & (n[0] | n[1] | n[2] | n[3])
    col = np.where(coast[..., None], mix(col, INK, 0.85), col)
    col = np.where((water & (dist == 1))[..., None], mix(col, INK, 0.3), col)
    # contour lines every 16 blocks, bolder every 64
    lv = np.floor(c['h'] / 16).astype(np.int32)
    n = shifts(lv, 0)
    edge = land & ((lv != n[1]) | (lv != n[3])) & c['valid']
    major = edge & ((np.maximum(lv, np.maximum(n[1], n[3])) % 4) == 0)
    col = np.where(edge[..., None], mix(col, (112, 80, 52), np.where(major, 0.55, 0.25)), col)
    stamp(col, (k == K['tree']) & land, X, Z, 6, TREE, 11)
    stamp(col, (k == K['sand']) & land, X, Z, 4, DOT, 23)
    grain = (hsh(X[None, :], Z[:, None], 5) & 255) / 255.0 - 0.5
    return col * (1 + 0.05 * grain + 0.06 * vnoise(X, Z, 96, 7) + 0.03 * vnoise(X, Z, 24, 9))[..., None]


def biomes(c, P):
    col = P['brgb'][c['bio']] * np.clip(c['shade'], 0.72, 1.12)[..., None]
    col = np.where((c['water'] & ~P['bwater'][c['bio']])[..., None], mix(col, (70, 110, 190), 0.55), col)
    n = shifts(c['bio'], 0)
    edge = c['valid'] & ((c['bio'] != n[1]) | (c['bio'] != n[3]))
    return np.where(edge[..., None], col * 0.78, col)


LAND = ((0, (98, 140, 84)), (25, (138, 168, 96)), (70, (196, 186, 120)), (130, (178, 138, 92)),
        (210, (150, 116, 96)), (300, (178, 172, 168)), (420, (246, 246, 248)))
SEA = ((0, (132, 180, 214)), (8, (92, 146, 200)), (24, (54, 98, 168)), (48, (32, 62, 130)))


def ramp(v, stops):
    xs = np.array([s[0] for s in stops], np.float32)
    return np.stack([np.interp(v, xs, [s[1][i] for s in stops]) for i in range(3)], -1).astype(np.float32)


def height(c, P):
    col = ramp(c['h'] - P['sea'], LAND) * np.clip(c['shade'], 0.6, 1.2)[..., None]
    col = np.where(c['water'][..., None], ramp(c['depth'], SEA), col)
    lv = np.floor(c['h'] / 32).astype(np.int32)
    n = shifts(lv, 0)
    edge = ~c['water'] & ((lv != n[1]) | (lv != n[3]))
    return np.where(edge[..., None], col * 0.82, col)


def render(w, P, X, Z):
    """Window arrays (512 + 2B square) -> {style: 512x512 RGBA}."""
    c = prepare(w, P)
    alpha = np.where(c['valid'], 255, 0).astype(np.uint8)[B:-B, B:-B]
    out = {'terrain': terrain(c, P), 'parchment': parchment(c, P, X, Z), 'biomes': biomes(c, P), 'height': height(c, P)}
    return {s: np.dstack([np.clip(v[B:-B, B:-B], 0, 255).astype(np.uint8), alpha]) for s, v in out.items()}


def hover(w, P):
    """Per-block lookup image: top half = height | biome << 11, bottom half = block << 8 | water depth."""
    valid = w['surf'] != MISSING
    water = P['water'][w['top']] & valid
    v1 = np.where(valid, (w['surf'].astype(np.int64) - P['min_y']) | (w['bio'].astype(np.int64) << 11), 0)
    v2 = np.where(valid, (w['top'].astype(np.int64) << 8) |
                  np.where(water, np.clip(w['surf'].astype(np.int64) - w['floor'], 0, 255), 0), 0)
    v = np.concatenate([v1, v2])
    return np.dstack([(v >> 16) & 255, (v >> 8) & 255, v & 255]).astype(np.uint8)


def save(rgba, path, quality=80):
    """Write a WebP tile, or remove it when the area is empty. Returns whether a tile exists."""
    a = rgba[..., 3]
    if not a.any():
        path.unlink(missing_ok=True)
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray(rgba[..., :3] if a.all() else rgba, 'RGB' if a.all() else 'RGBA')
    img.save(path, 'WEBP', quality=quality, method=4)
    return True


def shrink(rgba):
    """2x box downsample with premultiplied alpha."""
    img = Image.fromarray(rgba, 'RGBA').convert('RGBa')
    return np.asarray(img.resize((img.width // 2, img.height // 2), Image.Resampling.BOX).convert('RGBA'))


def load(path):
    if not path.exists():
        return None
    return np.asarray(Image.open(path).convert('RGBA'))
