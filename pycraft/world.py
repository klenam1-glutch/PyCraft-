"""Memory-efficient multi-dimension voxel world (Overworld + Nether), structures, lava/ice, arrows, TNT."""

import math
import random

from pycraft.biomes import classify_biome, sample_chunk_columns, sample_climate
from pycraft.blocks import BLOCKS
from pycraft.constants import (
    AIR, BEDROCK, BIRCH_LEAVES, BIRCH_WOOD, BOOKSHELF, BRICK, CACTUS,
    CHEST, CHUNK_SIZE, CLAY, COAL_ORE, COBBLE, DIAMOND_ORE, DIRT,
    EMERALD_ORE, FLOWER_RED, FLOWER_YELLOW, GLOWSTONE, GOLD_BLOCK,
    GOLD_ORE, GRASS, GRAVEL, ICE, IRON_ORE, LAVA, LEAVES, MAX_Y,
    MOSSY_COBBLE, NETHERRACK, OBSIDIAN, PINE_LEAVES, PINE_WOOD, PLANKS,
    PORTAL, SAND, SANDSTONE, SNOW, STONE, TNT, TORCH, WATER, WATER_LEVEL, WOOD,
)
from pycraft.lighting import propagate_chunk_light, update_light_at_block
from pycraft.mobs import Arrow, MOB_STATS, Mob
from pycraft.noise import fbm_2d, hash2, hash3

_MAX_PARTICLES = 60
_MAX_SPLASHES = 28

# Flat O(1) lookup tables for ultra-fast face culling (avoids dict lookup in hot loops)
_BLK_TRANS = tuple((True if (i not in BLOCKS or BLOCKS[i]["transparent"]) else False) for i in range(64))
_BLK_SOLID = tuple((True if (i in BLOCKS and BLOCKS[i]["solid"]) else False) for i in range(64))
_BLK_EMISSIVE = tuple((True if (i in BLOCKS and BLOCKS[i]["emissive"]) else False) for i in range(64))


class Chunk:
    """Compact fixed-size voxel chunk backed by flat bytearrays (2KB blocks + 2KB dual-channel light)."""

    __slots__ = ("cx", "cz", "data", "light", "faces", "max_y")

    def __init__(self, cx, cz):
        self.cx = cx
        self.cz = cz
        self.data = bytearray(CHUNK_SIZE * MAX_Y * CHUNK_SIZE)
        self.light = bytearray(CHUNK_SIZE * MAX_Y * CHUNK_SIZE)
        self.faces = []
        self.max_y = 0


class World:
    __slots__ = (
        "seed", "dimension", "chunks", "modified_dims", "glows",
        "tnt_fuses", "particles", "mobs", "arrows", "chest_storage",
        "weather", "weather_timer", "weather_intensity",
        "lightning_flash", "lightning_cd", "lightning_pos", "rain_splashes",
        "_last_pcx", "_last_pcz",
    )

    def __init__(self, seed=None, dimension="overworld"):
        self.seed = seed if seed is not None else random.randint(1, 999999)
        self.dimension = dimension
        self.chunks = {}
        self.modified_dims = {"overworld": {}, "nether": {}}
        self.glows = set()
        self.tnt_fuses = []
        self.particles = []
        self.mobs = []
        self.arrows = []
        self.chest_storage = {}
        self.weather = "clear"
        self.weather_timer = 90.0
        self.weather_intensity = 0.0
        self.lightning_flash = 0.0
        self.lightning_cd = 6.0
        self.lightning_pos = (0.15, 0.65)
        self.rain_splashes = []
        self._last_pcx = None
        self._last_pcz = None

    def cycle_weather(self):
        order = ("clear", "rain", "thunder")
        idx = (order.index(self.weather) + 1) % len(order) if self.weather in order else 0
        self.weather = order[idx]
        self.weather_timer = 85.0
        if self.weather == "thunder":
            self.lightning_cd = 1.8
        return self.weather

    def has_roof_above(self, x, y, z):
        ix = math.floor(x)
        iz = math.floor(z)
        chunk = self.chunks.get((ix >> 3, iz >> 3))
        if chunk is None:
            return False
        data = chunk.data
        col_off = ((iz & 7) << 3) | (ix & 7)
        start_y = max(0, math.floor(y) + 1)
        end_y = min(MAX_Y, chunk.max_y + 1)
        for wy in range(start_y, end_y):
            bid = data[(wy << 6) | col_off]
            if bid != AIR and _BLK_SOLID[bid]:
                return True
        return False

    @property
    def modified(self):
        return self.modified_dims[self.dimension]

    def switch_dimension(self):
        self.dimension = "nether" if self.dimension == "overworld" else "overworld"
        self.chunks.clear()
        self.glows.clear()
        self.tnt_fuses.clear()
        self.particles.clear()
        self.mobs.clear()
        self.arrows.clear()
        self._last_pcx = None
        self._last_pcz = None
        return self.dimension

    def get_block(self, x, y, z):
        if y < 0 or y >= MAX_Y:
            return AIR
        chunk = self.chunks.get((x >> 3, z >> 3))
        if chunk is None:
            return AIR
        return chunk.data[(y << 6) | ((z & 7) << 3) | (x & 7)]

    def get_light_byte(self, x, y, z):
        """Return packed light byte (upper 4 bits=sky 0..15, lower 4 bits=block 0..15)."""
        if y >= MAX_Y:
            return 0xF0 if self.dimension == "overworld" else 0
        if y < 0:
            return 0
        chunk = self.chunks.get((x >> 3, z >> 3))
        if chunk is None:
            return 0xF0 if self.dimension == "overworld" else 0
        return chunk.light[(y << 6) | ((z & 7) << 3) | (x & 7)]

    def get_light_levels(self, x, y, z):
        """Return (sky_light_0_15, block_light_0_15) at world block coordinates."""
        lv = self.get_light_byte(x, y, z)
        return (lv >> 4), (lv & 0x0F)

    def is_solid(self, x, y, z):
        bid = self.get_block(x, y, z)
        return bid != AIR and BLOCKS[bid]["solid"]

    def get_biome(self, x, z):
        if self.dimension == "nether":
            return "nether"
        temp, moist, cont, ridge, _ = sample_climate(x, z, self.seed)
        return classify_biome(temp, moist, cont, ridge)

    def _is_occluding(self, x, y, z, self_bid, self_trans):
        nb = self.get_block(x, y, z)
        if nb == AIR:
            return False
        if nb == self_bid and self_trans:
            return True
        return not BLOCKS[nb]["transparent"]

    def _place_raw(self, x, y, z, bid):
        if y < 0 or y >= MAX_Y:
            return
        chunk = self.chunks.get((x >> 3, z >> 3))
        if chunk is None:
            return
        chunk.data[(y << 6) | ((z & 7) << 3) | (x & 7)] = bid
        if bid != AIR:
            if y > chunk.max_y:
                chunk.max_y = y
            if _BLK_EMISSIVE[bid]:
                self.glows.add((x, y, z))
            else:
                self.glows.discard((x, y, z))
        else:
            self.glows.discard((x, y, z))

    def _generate_nether_chunk(self, chunk, cx, cz):
        data = chunk.data
        x0 = cx * CHUNK_SIZE
        z0 = cz * CHUNK_SIZE
        for lx in range(CHUNK_SIZE):
            wx = x0 + lx
            for lz in range(CHUNK_SIZE):
                wz = z0 + lz
                col_off = (lz << 3) | lx
                n = fbm_2d(wx, wz, self.seed + 777)
                floor_h = max(2, min(13, int(3 + n * 10.0)))
                ceil_h = max(22, min(MAX_Y - 2, int(23 + fbm_2d(wx + 99, wz - 99, self.seed + 888) * 6.0)))

                data[col_off] = BEDROCK
                data[((MAX_Y - 1) << 6) | col_off] = BEDROCK

                for wy in range(1, floor_h + 1):
                    oh = hash3(wx, wy, wz, self.seed + 911)
                    if oh > 0.945:
                        bid = GOLD_ORE
                    elif oh > 0.88:
                        bid = GLOWSTONE if wy == floor_h else OBSIDIAN
                    else:
                        bid = NETHERRACK if hash2(wx, wz, self.seed + 19) > 0.16 else BRICK
                    data[(wy << 6) | col_off] = bid

                if floor_h < WATER_LEVEL:
                    for wy in range(floor_h + 1, WATER_LEVEL + 1):
                        self._place_raw(wx, wy, wz, LAVA)

                for wy in range(ceil_h, MAX_Y - 1):
                    bid = GLOWSTONE if (wy == ceil_h and hash2(wx, wz, self.seed + 422) > 0.90) else NETHERRACK
                    self._place_raw(wx, wy, wz, bid)

        if cx == 0 and cz == 0:
            # Safe Nether return portal shrine
            for px in range(0, 5):
                for pz in range(1, 5):
                    self._place_raw(px, 7, pz, OBSIDIAN)
                    for py in range(8, 13):
                        self._place_raw(px, py, pz, AIR)
            self._place_raw(1, 8, 3, OBSIDIAN)
            self._place_raw(4, 8, 3, OBSIDIAN)
            for py in range(8, 11):
                self._place_raw(1, py, 3, OBSIDIAN)
                self._place_raw(4, py, 3, OBSIDIAN)
            for px in (2, 3):
                self._place_raw(px, 11, 3, OBSIDIAN)
                for py in (8, 9, 10):
                    self._place_raw(px, py, 3, PORTAL)

    def generate_chunk(self, cx, cz):
        if (cx, cz) in self.chunks:
            return
        chunk = Chunk(cx, cz)
        self.chunks[(cx, cz)] = chunk

        if self.dimension == "nether":
            chunk.max_y = MAX_Y - 1
            self._generate_nether_chunk(chunk, cx, cz)
        else:
            data = chunk.data
            x0 = cx * CHUNK_SIZE
            z0 = cz * CHUNK_SIZE
            tree_spots = []
            cactus_spots = []
            flower_spots = []
            flat_h_center = None
            col_samples = sample_chunk_columns(x0, z0, self.seed)
            chunk_max_h = 0

            for lx in range(CHUNK_SIZE):
                wx = x0 + lx
                for lz in range(CHUNK_SIZE):
                    wz = z0 + lz
                    biome, h, top_bid, sub_bid, deep_bid = col_samples[(lz << 3) | lx]
                    if h > chunk_max_h:
                        chunk_max_h = h
                    if lx == 3 and lz == 3:
                        flat_h_center = (h, biome)

                    col_off = (lz << 3) | lx
                    data[col_off] = BEDROCK
                    for wy in range(1, h + 1):
                        if 2 <= wy <= h - 3 and h > WATER_LEVEL + 2:
                            if hash3(wx // 2, wy // 2, wz // 2, self.seed + 404) > 0.968:
                                if wy == 2:
                                    self._place_raw(wx, wy, wz, LAVA)
                                continue

                        if wy == h:
                            if biome == "river" and h < WATER_LEVEL and hash2(wx, wz, self.seed + 612) > 0.68:
                                bid = CLAY
                            elif h <= WATER_LEVEL and biome not in ("badlands", "snowy_mountains"):
                                bid = GRAVEL if (biome == "taiga" or hash2(wx, wz, self.seed + 221) > 0.72) else SAND
                            else:
                                bid = top_bid
                        elif wy >= h - 2:
                            if biome == "river" and h < WATER_LEVEL:
                                bid = GRAVEL
                            elif h <= WATER_LEVEL and biome not in ("badlands",):
                                bid = SAND
                            else:
                                bid = sub_bid
                        elif deep_bid != STONE and wy >= h - 5:
                            bid = deep_bid
                        else:
                            ore_h = hash3(wx, wy, wz, self.seed + 333)
                            if wy <= 6 and ore_h > 0.972:
                                bid = DIAMOND_ORE
                            elif biome in ("snowy_mountains", "taiga") and wy <= 14 and ore_h > 0.960:
                                bid = EMERALD_ORE
                            elif wy <= 9 and ore_h > 0.952:
                                bid = GOLD_ORE
                            elif ore_h > 0.918:
                                bid = IRON_ORE
                            elif ore_h > 0.848:
                                bid = COAL_ORE
                            else:
                                bid = STONE
                        data[(wy << 6) | col_off] = bid

                    if h < WATER_LEVEL:
                        chunk_max_h = max(chunk_max_h, WATER_LEVEL)
                        cold_water = biome in ("snowy_mountains", "taiga")
                        for wy in range(h + 1, WATER_LEVEL + 1):
                            if wy == WATER_LEVEL and cold_water:
                                data[(wy << 6) | col_off] = ICE
                            else:
                                data[(wy << 6) | col_off] = WATER

                    if h > WATER_LEVEL and h < MAX_Y - 6:
                        th = hash2(wx, wz, self.seed + 999)
                        in_pad = (1 <= lx <= CHUNK_SIZE - 2 and 1 <= lz <= CHUNK_SIZE - 2)
                        if in_pad and biome in ("desert", "badlands") and th > 0.976:
                            cactus_spots.append((wx, h + 1, wz))
                        elif in_pad and biome == "taiga" and th > 0.928:
                            tree_spots.append(("pine", wx, h + 1, wz))
                        elif in_pad and biome == "snowy_mountains" and h <= 14 and th > 0.958:
                            tree_spots.append(("pine", wx, h + 1, wz))
                        elif in_pad and biome == "forest" and h <= 16 and th > 0.925:
                            kind_t = "birch" if hash2(wx + 7, wz - 13, self.seed + 701) > 0.62 else "oak"
                            tree_spots.append((kind_t, wx, h + 1, wz))
                        elif in_pad and biome == "plains" and h <= 14 and th > 0.980:
                            kind_t = "birch" if hash2(wx + 3, wz + 9, self.seed + 702) > 0.65 else "oak"
                            tree_spots.append((kind_t, wx, h + 1, wz))
                        elif biome in ("plains", "forest") and top_bid == GRASS and 0.895 < th < 0.920:
                            fl_bid = FLOWER_RED if hash2(wx - 5, wz + 11, self.seed + 703) > 0.5 else FLOWER_YELLOW
                            flower_spots.append((wx, h + 1, wz, fl_bid))

            for kind_t, tx, ty, tz in tree_spots:
                if kind_t == "pine":
                    trunk_h = 4 + int(hash2(tx, tz, self.seed + 123) * 2)
                    for dy in range(trunk_h):
                        self._place_raw(tx, ty + dy, tz, PINE_WOOD)
                    # Conical spruce canopy
                    for dy, rad in ((2, 2), (3, 1), (4, 1), (trunk_h, 0)):
                        cy_l = ty + dy
                        if cy_l >= MAX_Y - 1:
                            continue
                        for dx in range(-rad, rad + 1):
                            for dz in range(-rad, rad + 1):
                                if abs(dx) == 2 and abs(dz) == 2:
                                    continue
                                if self.get_block(tx + dx, cy_l, tz + dz) == AIR:
                                    self._place_raw(tx + dx, cy_l, tz + dz, PINE_LEAVES)
                else:
                    log_bid = BIRCH_WOOD if kind_t == "birch" else WOOD
                    leaf_bid = BIRCH_LEAVES if kind_t == "birch" else LEAVES
                    trunk_h = 3 + int(hash2(tx, tz, self.seed + 123) * 2)
                    for dy in range(trunk_h):
                        self._place_raw(tx, ty + dy, tz, log_bid)
                    top_y = ty + trunk_h
                    for dy in (-1, 0, 1):
                        if top_y + dy >= MAX_Y - 1:
                            continue
                        rad = 2 if dy <= 0 else 1
                        for dx in range(-rad, rad + 1):
                            for dz in range(-rad, rad + 1):
                                if dx == 0 and dz == 0 and dy < 1:
                                    continue
                                if abs(dx) == 2 and abs(dz) == 2:
                                    continue
                                if self.get_block(tx + dx, top_y + dy, tz + dz) == AIR:
                                    self._place_raw(tx + dx, top_y + dy, tz + dz, leaf_bid)

            for fx_p, fy_p, fz_p, fl_bid in flower_spots:
                if self.get_block(fx_p, fy_p, fz_p) == AIR:
                    self._place_raw(fx_p, fy_p, fz_p, fl_bid)

            for cx_p, cy_p, cz_p in cactus_spots:
                ch = 2 + int(hash2(cx_p, cz_p, self.seed + 654) * 2)
                for dy in range(ch):
                    self._place_raw(cx_p, cy_p + dy, cz_p, CACTUS)

            # Deterministic Ruin / Portal Shrine / Desert Monument
            if flat_h_center is not None and not (cx == 0 and cz == 0):
                sh_h, sh_biome = flat_h_center
                sh_roll = hash2(cx, cz, self.seed + 5150)
                if WATER_LEVEL + 1 < sh_h < MAX_Y - 7:
                    if sh_roll > 0.965:
                        # Ruined Nether Portal
                        for px in range(x0 + 2, x0 + 6):
                            self._place_raw(px, sh_h, z0 + 3, STONE)
                        for py in range(sh_h + 1, sh_h + 4):
                            self._place_raw(x0 + 2, py, z0 + 3, OBSIDIAN)
                            self._place_raw(x0 + 5, py, z0 + 3, OBSIDIAN)
                        self._place_raw(x0 + 3, sh_h + 4, z0 + 3, OBSIDIAN)
                        self._place_raw(x0 + 4, sh_h + 4, z0 + 3, OBSIDIAN)
                        self._place_raw(x0 + 3, sh_h + 1, z0 + 3, PORTAL)
                        self._place_raw(x0 + 4, sh_h + 1, z0 + 3, PORTAL)
                        self._place_raw(x0 + 3, sh_h + 2, z0 + 3, PORTAL)
                        self._place_raw(x0 + 4, sh_h + 2, z0 + 3, PORTAL)
                        self._place_raw(x0 + 2, sh_h + 1, z0 + 4, GOLD_BLOCK)
                    elif sh_roll > 0.935:
                        # Mossy Dungeon or Sandstone Shrine
                        mat = SANDSTONE if sh_biome in ("desert", "badlands") else MOSSY_COBBLE
                        for dx in range(2, 6):
                            for dz in range(2, 6):
                                self._place_raw(x0 + dx, sh_h, z0 + dz, mat)
                        for py in (sh_h + 1, sh_h + 2):
                            self._place_raw(x0 + 2, py, z0 + 2, mat)
                            self._place_raw(x0 + 5, py, z0 + 2, mat)
                            self._place_raw(x0 + 2, py, z0 + 5, mat)
                            self._place_raw(x0 + 5, py, z0 + 5, mat)
                        self._place_raw(x0 + 3, sh_h + 1, z0 + 3, CHEST)
                        self._place_raw(x0 + 4, sh_h + 1, z0 + 3, BOOKSHELF)
                        self._place_raw(x0 + 3, sh_h + 2, z0 + 2, TORCH)

        chunk.max_y = max(chunk.max_y, min(MAX_Y - 1, chunk_max_h + 7)) if self.dimension == "overworld" else MAX_Y - 1
        mod_map = self.modified
        for (mx, my, mz), mbid in mod_map.items():
            if (mx >> 3) == cx and (mz >> 3) == cz:
                self._place_raw(mx, my, mz, mbid)

        propagate_chunk_light(self, cx, cz)
        self.rebuild_chunk_faces(cx, cz)
        for ncx, ncz in ((cx - 1, cz), (cx + 1, cz), (cx, cz - 1), (cx, cz + 1)):
            if (ncx, ncz) in self.chunks:
                self.rebuild_chunk_faces(ncx, ncz)

    def rebuild_chunk_faces(self, cx, cz):
        chunks = self.chunks
        chunk = chunks.get((cx, cz))
        if chunk is None:
            return
        data = chunk.data
        xm_c = chunks.get((cx - 1, cz))
        xp_c = chunks.get((cx + 1, cz))
        zm_c = chunks.get((cx, cz - 1))
        zp_c = chunks.get((cx, cz + 1))
        xm_d = xm_c.data if xm_c is not None else None
        xp_d = xp_c.data if xp_c is not None else None
        zm_d = zm_c.data if zm_c is not None else None
        zp_d = zp_c.data if zp_c is not None else None

        blk_trans = _BLK_TRANS
        faces = []
        append = faces.append
        y_top = min(MAX_Y, max(chunk.max_y + 1, 1))
        max_non_air = 0

        for wy in range(y_top):
            y_off = wy << 6
            wy_pack = wy << 6
            has_up = (wy < MAX_Y - 1)
            has_dn = (wy > 0)
            y_up = y_off + 64
            y_dn = y_off - 64

            for lz in range(8):
                z_off = lz << 3
                yz_off = y_off | z_off
                lzw_pack = wy_pack | z_off
                z_lt = (lz < 7)
                z_gt = (lz > 0)
                yz_zp = y_off | (z_off + 8)
                yz_zm = y_off | (z_off - 8)

                for lx in range(8):
                    bid = data[yz_off | lx]
                    if bid == 0:
                        continue
                    max_non_air = wy
                    self_trans = blk_trans[bid]
                    bp = lx | lzw_pack | (bid << 14)

                    # 0: +Y Top
                    if has_up:
                        nb = data[y_up | z_off | lx]
                        if nb == 0 or (blk_trans[nb] and not (self_trans and nb == bid)):
                            append(bp)
                    else:
                        append(bp)

                    # 1: -Y Bottom
                    if has_dn:
                        nb = data[y_dn | z_off | lx]
                        if nb == 0 or (blk_trans[nb] and not (self_trans and nb == bid)):
                            append(bp | 2048)

                    # 2: +X East (fidx=2 -> 2<<11 = 4096)
                    if lx < 7:
                        nb = data[yz_off | (lx + 1)]
                    elif xp_d is not None:
                        nb = xp_d[yz_off]
                    else:
                        nb = 0
                    if nb == 0 or (blk_trans[nb] and not (self_trans and nb == bid)):
                        append(bp | 4096)

                    # 3: -X West (fidx=3 -> 3<<11 = 6144)
                    if lx > 0:
                        nb = data[yz_off | (lx - 1)]
                    elif xm_d is not None:
                        nb = xm_d[yz_off | 7]
                    else:
                        nb = 0
                    if nb == 0 or (blk_trans[nb] and not (self_trans and nb == bid)):
                        append(bp | 6144)

                    # 4: +Z North (fidx=4 -> 4<<11 = 8192)
                    if z_lt:
                        nb = data[yz_zp | lx]
                    elif zp_d is not None:
                        nb = zp_d[y_off | lx]
                    else:
                        nb = 0
                    if nb == 0 or (blk_trans[nb] and not (self_trans and nb == bid)):
                        append(bp | 8192)

                    # 5: -Z South (fidx=5 -> 5<<11 = 10240)
                    if z_gt:
                        nb = data[yz_zm | lx]
                    elif zm_d is not None:
                        nb = zm_d[y_off | 56 | lx]
                    else:
                        nb = 0
                    if nb == 0 or (blk_trans[nb] and not (self_trans and nb == bid)):
                        append(bp | 10240)

        chunk.max_y = max_non_air
        chunk.faces = faces

    def set_block(self, x, y, z, bid, record_mod=True):
        if y < 0 or y >= MAX_Y:
            return False
        old_bid = self.get_block(x, y, z)
        if bid == AIR and old_bid == BEDROCK:
            return False
        self._place_raw(x, y, z, bid)
        if old_bid != bid:
            update_light_at_block(self, x, y, z, old_bid, bid)
        if record_mod:
            self.modified[(x, y, z)] = bid
        cx = x >> 3
        cz = z >> 3
        if (cx, cz) in self.chunks:
            self.rebuild_chunk_faces(cx, cz)
        lx = x & 7
        lz = z & 7
        if lx == 0 and (cx - 1, cz) in self.chunks:
            self.rebuild_chunk_faces(cx - 1, cz)
        elif lx == CHUNK_SIZE - 1 and (cx + 1, cz) in self.chunks:
            self.rebuild_chunk_faces(cx + 1, cz)
        if lz == 0 and (cx, cz - 1) in self.chunks:
            self.rebuild_chunk_faces(cx, cz - 1)
        elif lz == CHUNK_SIZE - 1 and (cx, cz + 1) in self.chunks:
            self.rebuild_chunk_faces(cx, cz + 1)
        return True

    def spawn_break_particles(self, bx, by, bz, bid, count=8):
        binfo = BLOCKS.get(bid)
        if not binfo:
            return
        rgb = binfo["side"]
        for _ in range(count):
            if len(self.particles) >= _MAX_PARTICLES:
                self.particles.pop(0)
            px = bx + 0.2 + random.random() * 0.6
            py = by + 0.2 + random.random() * 0.6
            pz = bz + 0.2 + random.random() * 0.6
            vx = (random.random() - 0.5) * 3.2
            vy = 1.2 + random.random() * 2.8
            vz = (random.random() - 0.5) * 3.2
            self.particles.append([px, py, pz, vx, vy, vz, rgb, 0.45 + random.random() * 0.2])

    def shoot_arrow(self, x, y, z, dx, dy, dz):
        if len(self.arrows) >= 12:
            self.arrows.pop(0)
        spd = 22.0
        self.arrows.append(Arrow(x + dx * 0.6, y + dy * 0.6, z + dz * 0.6, dx * spd, dy * spd + 1.5, dz * spd))

    def trigger_tnt(self, bx, by, bz):
        for f in self.tnt_fuses:
            if f[0] == bx and f[1] == by and f[2] == bz:
                return
        self.tnt_fuses.append([bx, by, bz, 1.35])

    def explode(self, cx, cy, cz, radius=2.7):
        r_int = int(math.ceil(radius))
        affected_chunks = set()
        for dx in range(-r_int, r_int + 1):
            for dy in range(-r_int, r_int + 1):
                for dz in range(-r_int, r_int + 1):
                    if dx * dx + dy * dy + dz * dz <= radius * radius:
                        wx, wy, wz = cx + dx, cy + dy, cz + dz
                        if wy <= 0 or wy >= MAX_Y:
                            continue
                        bid = self.get_block(wx, wy, wz)
                        if bid != AIR and bid != BEDROCK:
                            if bid == TNT and (wx != cx or wy != cy or wz != cz):
                                self.trigger_tnt(wx, wy, wz)
                            else:
                                self._place_raw(wx, wy, wz, AIR)
                                self.modified[(wx, wy, wz)] = AIR
                                affected_chunks.add((wx >> 3, wz >> 3))
        for _ in range(20):
            if len(self.particles) >= _MAX_PARTICLES:
                self.particles.pop(0)
            ang = random.random() * math.tau
            spd = 2.0 + random.random() * 5.2
            c = random.choice([(255, 165, 45), (245, 88, 30), (215, 215, 215)])
            self.particles.append([
                cx + 0.5, cy + 0.5, cz + 0.5,
                math.cos(ang) * spd, 2.0 + random.random() * 4.5, math.sin(ang) * spd,
                c, 0.65,
            ])
        for ccx, ccz in affected_chunks:
            propagate_chunk_light(self, ccx, ccz)
        for ccx, ccz in affected_chunks:
            for dcx in (-1, 0, 1):
                for dcz in (-1, 0, 1):
                    nc = (ccx + dcx, ccz + dcz)
                    if nc in self.chunks:
                        self.rebuild_chunk_faces(nc[0], nc[1])

    def update(self, dt, player, is_day, sound_bank):
        self.weather_timer -= dt
        if self.weather_timer <= 0:
            if self.weather == "clear":
                self.weather_timer = 55.0 + random.random() * 55.0
                self.weather = "thunder" if random.random() < 0.30 else "rain"
                if self.weather == "thunder":
                    self.lightning_cd = 2.0 + random.random() * 4.0
            elif self.weather == "rain":
                self.weather_timer = 50.0 + random.random() * 55.0
                self.weather = "thunder" if random.random() < 0.35 else "clear"
                if self.weather == "thunder":
                    self.lightning_cd = 1.8 + random.random() * 4.0
            else:
                self.weather_timer = 75.0 + random.random() * 65.0
                self.weather = "clear"

        target_int = 1.0 if self.weather in ("rain", "thunder") else 0.0
        if self.weather_intensity < target_int:
            self.weather_intensity = min(target_int, self.weather_intensity + dt * 0.45)
        elif self.weather_intensity > target_int:
            self.weather_intensity = max(target_int, self.weather_intensity - dt * 0.45)

        if self.lightning_flash > 0.0:
            self.lightning_flash = max(0.0, self.lightning_flash - dt * 2.6)

        if self.dimension == "overworld" and self.weather == "thunder" and self.weather_intensity > 0.45:
            self.lightning_cd -= dt
            if self.lightning_cd <= 0.0:
                self.lightning_cd = 5.5 + random.random() * 8.5
                self.lightning_flash = 1.0
                self.lightning_pos = (random.uniform(-0.68, 0.68), random.uniform(0.32, 0.85))
                sound_bank.play("thunder", 0.78)
        if self.weather_intensity > 0.15 and self.dimension == "overworld":
            # Spawn subtle exposed ground rain splashes near the player
            p_biome = self.get_biome(int(player.x), int(player.z))
            if p_biome not in ("desert", "badlands", "snowy_mountains", "taiga"):
                spawn_prob = dt * 28.0 * self.weather_intensity
                n_sp = int(spawn_prob) + (1 if random.random() < (spawn_prob - int(spawn_prob)) else 0)
                for _ in range(min(3, n_sp)):
                    rx = player.x + (random.random() - 0.5) * 14.0
                    rz = player.z + (random.random() - 0.5) * 14.0
                    ix, iz = math.floor(rx), math.floor(rz)
                    if (ix >> 3, iz >> 3) in self.chunks:
                        sy = self.get_surface_y(ix, iz)
                        if len(self.rain_splashes) >= _MAX_SPLASHES:
                            self.rain_splashes.pop(0)
                        self.rain_splashes.append([rx, sy + 0.04, rz, 0.28])

        if self.rain_splashes:
            alive_sp = []
            for sp in self.rain_splashes:
                sp[3] -= dt
                if sp[3] > 0.0:
                    alive_sp.append(sp)
            self.rain_splashes = alive_sp

        if self.particles:
            alive = []
            for p in self.particles:
                p[7] -= dt
                if p[7] > 0:
                    p[4] -= 12.0 * dt
                    p[0] += p[3] * dt
                    p[1] += p[4] * dt
                    p[2] += p[5] * dt
                    alive.append(p)
            self.particles = alive

        if self.arrows:
            alive_arrows = []
            for a in self.arrows:
                a.ttl -= dt
                if a.ttl <= 0:
                    continue
                a.vy -= 14.0 * dt
                a.x += a.vx * dt
                a.y += a.vy * dt
                a.z += a.vz * dt
                hit_mob = None
                for m in self.mobs:
                    st = MOB_STATS[m.kind]
                    if abs(a.x - m.x) <= st["w"] * 0.7 and abs(a.z - m.z) <= st["w"] * 0.7 and m.y <= a.y <= m.y + st["h"] + 0.1:
                        hit_mob = m
                        break
                if hit_mob is not None:
                    hit_mob.hp -= 7
                    hit_mob.hurt_timer = 0.25
                    sound_bank.play("hit")
                    continue
                bx, by, bz = int(math.floor(a.x)), int(math.floor(a.y)), int(math.floor(a.z))
                bid = self.get_block(bx, by, bz)
                if bid == TNT:
                    self.trigger_tnt(bx, by, bz)
                    sound_bank.play("ignite")
                    continue
                if bid != AIR and BLOCKS[bid]["solid"]:
                    self.spawn_break_particles(bx, by, bz, bid, count=4)
                    sound_bank.play("step", 0.5)
                    continue
                alive_arrows.append(a)
            self.arrows = alive_arrows

        if self.tnt_fuses:
            next_fuses = []
            for f in self.tnt_fuses:
                f[3] -= dt
                if f[3] <= 0:
                    if self.get_block(f[0], f[1], f[2]) == TNT:
                        self.set_block(f[0], f[1], f[2], AIR)
                        self.explode(f[0], f[1], f[2], 2.8)
                        sound_bank.play("boom")
                else:
                    next_fuses.append(f)
            self.tnt_fuses = next_fuses

        next_mobs = []
        for m in self.mobs:
            if math.hypot(m.x - player.x, m.z - player.z) > 28.0:
                continue
            m.update(self, player, dt, is_day, sound_bank)
            if m.hp > 0:
                next_mobs.append(m)
            else:
                player.add_item(MOB_STATS[m.kind]["drop"], 1)
                player.xp += 5
        self.mobs = next_mobs

        if len(self.mobs) < 10 and random.random() < dt * 0.72:
            ang = random.random() * math.tau
            dist = 9.0 + random.random() * 10.0
            mx = int(math.floor(player.x + math.cos(ang) * dist))
            mz = int(math.floor(player.z + math.sin(ang) * dist))
            if (mx >> 3, mz >> 3) in self.chunks:
                my = self.get_surface_y(mx, mz)
                if WATER_LEVEL < my < MAX_Y - 3:
                    if self.dimension == "nether":
                        kind = random.choice(["skeleton", "spider", "zombie"])
                    elif is_day:
                        kind = random.choice(["pig", "cow", "sheep"])
                    else:
                        kind = random.choice(["zombie", "creeper", "skeleton", "spider", "pig"])
                    self.mobs.append(Mob(kind, mx + 0.5, my + 0.1, mz + 0.5))

    def ensure_chunks_around(self, px, pz, radius_blocks, max_gen_per_frame=2):
        pcx = math.floor(px) >> 3
        pcz = math.floor(pz) >> 3
        rc = int(math.ceil(radius_blocks / CHUNK_SIZE)) + 1

        if pcx != self._last_pcx or pcz != self._last_pcz:
            self._last_pcx = pcx
            self._last_pcz = pcz
            unload_r_sq = (rc + 2) ** 2
            to_unload = [
                key for key in self.chunks
                if (key[0] - pcx) ** 2 + (key[1] - pcz) ** 2 > unload_r_sq
            ]
            if to_unload:
                unload_set = set(to_unload)
                for key in to_unload:
                    del self.chunks[key]
                if self.glows:
                    self.glows = {
                        g for g in self.glows
                        if (g[0] >> 3, g[2] >> 3) not in unload_set
                    }

        needed = [
            (dcx * dcx + dcz * dcz, (pcx + dcx, pcz + dcz))
            for dcx in range(-rc, rc + 1)
            for dcz in range(-rc, rc + 1)
            if (pcx + dcx, pcz + dcz) not in self.chunks
        ]
        needed.sort()
        for idx, (_, (ccx, ccz)) in enumerate(needed):
            if idx >= max_gen_per_frame:
                break
            self.generate_chunk(ccx, ccz)

    def get_surface_y(self, x, z):
        top_limit = (MAX_Y - 5) if self.dimension == "nether" else (MAX_Y - 1)
        for y in range(top_limit, -1, -1):
            bid = self.get_block(x, y, z)
            if bid != AIR and BLOCKS[bid]["solid"]:
                return y + 1
        return 10
