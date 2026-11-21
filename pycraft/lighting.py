"""Minecraft-style dual-channel BFS voxel light propagation (daylight sky light + block light)."""

from collections import deque

from pycraft.blocks import BLOCKS
from pycraft.constants import (
    AIR, BIRCH_LEAVES, CHUNK_SIZE, DOOR_OPEN, FLOWER_RED, FLOWER_YELLOW,
    FURNACE, GLASS, GLOWSTONE, ICE, LADDER, LAVA, LEAVES, MAX_Y,
    PINE_LEAVES, PORTAL, TORCH, WATER,
)

# Precomputed O(1) LUTs indexed by block ID (0..63)
_EMIT_VALS = {
    GLOWSTONE: 15,
    LAVA: 15,
    TORCH: 14,
    PORTAL: 11,
    FURNACE: 5,
}
EMIT_LUT = tuple(_EMIT_VALS.get(i, 0) for i in range(64))

_LEAF_OR_LIQ = frozenset((WATER, ICE, LEAVES, PINE_LEAVES, BIRCH_LEAVES))
_CLEAR_PASS = frozenset((AIR, GLASS, TORCH, FLOWER_RED, FLOWER_YELLOW, LADDER, DOOR_OPEN, PORTAL))


def _compute_sky_down_atten(bid):
    if bid in _CLEAR_PASS:
        return 0
    if bid in _LEAF_OR_LIQ:
        return 2
    if bid in BLOCKS and not BLOCKS[bid]["solid"]:
        return 0
    return 15


def _compute_step_atten(bid):
    if bid in _CLEAR_PASS:
        return 1
    if bid in _LEAF_OR_LIQ:
        return 3
    if bid in BLOCKS and not BLOCKS[bid]["solid"]:
        return 1
    return 15


SKY_DOWN_ATTEN = tuple(_compute_sky_down_atten(i) for i in range(64))
STEP_ATTEN = tuple(_compute_step_atten(i) for i in range(64))

_NEIGHBORS = (
    (1, 0, 0), (-1, 0, 0),
    (0, 1, 0), (0, -1, 0),
    (0, 0, 1), (0, 0, -1),
)


def _get_block_fast(chunks, x, y, z):
    if y < 0 or y >= MAX_Y:
        return AIR
    c = chunks.get((x >> 3, z >> 3))
    if c is None:
        return AIR
    return c.data[(y << 6) | ((z & 7) << 3) | (x & 7)]


def _get_sky_fast(chunks, x, y, z):
    if y < 0:
        return 0
    if y >= MAX_Y:
        return 15
    c = chunks.get((x >> 3, z >> 3))
    if c is None:
        return 0
    return c.light[(y << 6) | ((z & 7) << 3) | (x & 7)] >> 4


def _set_sky_fast(chunks, x, y, z, val, dirty):
    if y < 0 or y >= MAX_Y:
        return
    key = (x >> 3, z >> 3)
    c = chunks.get(key)
    if c is None:
        return
    idx = (y << 6) | ((z & 7) << 3) | (x & 7)
    cur = c.light[idx]
    c.light[idx] = ((val & 0x0F) << 4) | (cur & 0x0F)
    dirty.add(key)


def _get_blk_fast(chunks, x, y, z):
    if y < 0 or y >= MAX_Y:
        return 0
    c = chunks.get((x >> 3, z >> 3))
    if c is None:
        return 0
    return c.light[(y << 6) | ((z & 7) << 3) | (x & 7)] & 0x0F


def _set_blk_fast(chunks, x, y, z, val, dirty):
    if y < 0 or y >= MAX_Y:
        return
    key = (x >> 3, z >> 3)
    c = chunks.get(key)
    if c is None:
        return
    idx = (y << 6) | ((z & 7) << 3) | (x & 7)
    cur = c.light[idx]
    c.light[idx] = (cur & 0xF0) | (val & 0x0F)
    dirty.add(key)


def _flood_sky(chunks, queue, dirty):
    """Run BFS propagation of 4-bit sky light across chunks."""
    get_b = _get_block_fast
    get_s = _get_sky_fast
    set_s = _set_sky_fast
    step_att = STEP_ATTEN
    down_att = SKY_DOWN_ATTEN

    while queue:
        vx, vy, vz = queue.popleft()
        cur = get_s(chunks, vx, vy, vz)
        if cur <= 1:
            continue

        for dx, dy, dz in _NEIGHBORS:
            nx, ny, nz = vx + dx, vy + dy, vz + dz
            if ny < 0 or ny >= MAX_Y:
                continue
            c = chunks.get((nx >> 3, nz >> 3))
            if c is None:
                continue
            nb = c.data[(ny << 6) | ((nz & 7) << 3) | (nx & 7)]
            # Vertical downward propagation at full sky=15 keeps open shafts at 15
            if dy == -1 and cur == 15:
                att = down_att[nb]
                nxt = 15 - att
            else:
                att = step_att[nb]
                nxt = cur - att
            if nxt <= 0:
                continue
            idx = (ny << 6) | ((nz & 7) << 3) | (nx & 7)
            old = c.light[idx] >> 4
            if nxt > old:
                c.light[idx] = (nxt << 4) | (c.light[idx] & 0x0F)
                dirty.add((nx >> 3, nz >> 3))
                if nxt > 1:
                    queue.append((nx, ny, nz))


def _flood_block(chunks, queue, dirty):
    """Run BFS propagation of 4-bit block light (torches, glowstone, lava, portals)."""
    step_att = STEP_ATTEN

    while queue:
        vx, vy, vz = queue.popleft()
        vc = chunks.get((vx >> 3, vz >> 3))
        if vc is None:
            continue
        cur = vc.light[(vy << 6) | ((vz & 7) << 3) | (vx & 7)] & 0x0F
        if cur <= 1:
            continue

        for dx, dy, dz in _NEIGHBORS:
            nx, ny, nz = vx + dx, vy + dy, vz + dz
            if ny < 0 or ny >= MAX_Y:
                continue
            nc = chunks.get((nx >> 3, nz >> 3))
            if nc is None:
                continue
            idx = (ny << 6) | ((nz & 7) << 3) | (nx & 7)
            nb = nc.data[idx]
            att = step_att[nb]
            if att >= 15:
                continue
            nxt = cur - att
            if nxt <= 0:
                continue
            old = nc.light[idx] & 0x0F
            if nxt > old:
                nc.light[idx] = (nc.light[idx] & 0xF0) | nxt
                dirty.add((nx >> 3, nz >> 3))
                if nxt > 1:
                    queue.append((nx, ny, nz))


def propagate_chunk_light(world, cx, cz):
    """Compute initial column skylight + emissive block light and propagate cleanly across neighbors."""
    chunks = world.chunks
    chunk = chunks.get((cx, cz))
    if chunk is None:
        return set()

    data = chunk.data
    light = chunk.light
    # Clear existing light bytes in this chunk
    for i in range(len(light)):
        light[i] = 0

    x0 = cx * CHUNK_SIZE
    z0 = cz * CHUNK_SIZE
    is_overworld = (world.dimension == "overworld")
    sky_q = deque()
    blk_q = deque()
    down_att = SKY_DOWN_ATTEN
    emit_lut = EMIT_LUT
    dirty = {(cx, cz)}

    # 1. Column top-down sky light & local block emitters
    for lz in range(CHUNK_SIZE):
        wz = z0 + lz
        z_off = lz << 3
        for lx in range(CHUNK_SIZE):
            wx = x0 + lx
            col_off = z_off | lx
            sky_lv = 15 if is_overworld else 0

            for wy in range(MAX_Y - 1, -1, -1):
                idx = (wy << 6) | col_off
                bid = data[idx]

                if sky_lv > 0:
                    att = down_att[bid]
                    if att >= 15:
                        sky_lv = 0
                    else:
                        if att > 0:
                            sky_lv = max(0, sky_lv - att)
                        if sky_lv > 0:
                            light[idx] = (sky_lv << 4) | (light[idx] & 0x0F)
                            if sky_lv < 15 or wy == 0 or lx == 0 or lx == 7 or lz == 0 or lz == 7:
                                sky_q.append((wx, wy, wz))
                            elif wy > 0 and down_att[data[((wy - 1) << 6) | col_off]] >= 15:
                                sky_q.append((wx, wy, wz))

                em = emit_lut[bid]
                if em > 0:
                    light[idx] = (light[idx] & 0xF0) | em
                    blk_q.append((wx, wy, wz))

    # 1b. Seed interior vertical walls bordering open sky (where neighbor column blocked sky below terrain height)
    if is_overworld:
        y_chk = min(MAX_Y - 1, chunk.max_y + 1)
        for wy in range(1, y_chk):
            y_off = wy << 6
            for lz in range(1, 7):
                z_off = lz << 3
                wz = z0 + lz
                for lx in range(1, 7):
                    idx = y_off | z_off | lx
                    s_cur = light[idx] >> 4
                    if s_cur <= 1:
                        continue
                    if (
                        (light[idx + 1] >> 4) < s_cur - 1 and STEP_ATTEN[data[idx + 1]] < 15
                    ) or (
                        (light[idx - 1] >> 4) < s_cur - 1 and STEP_ATTEN[data[idx - 1]] < 15
                    ) or (
                        (light[idx + 8] >> 4) < s_cur - 1 and STEP_ATTEN[data[idx + 8]] < 15
                    ) or (
                        (light[idx - 8] >> 4) < s_cur - 1 and STEP_ATTEN[data[idx - 8]] < 15
                    ):
                        sky_q.append((x0 + lx, wy, wz))

    # 2. Pull neighbor chunk boundary light bleeding INTO this chunk
    for ncx, ncz, lx_n, lx_self, lz_n, lz_self, along_x in (
        (cx - 1, cz, 7, 0, None, None, False),
        (cx + 1, cz, 0, 7, None, None, False),
        (cx, cz - 1, None, None, 7, 0, True),
        (cx, cz + 1, None, None, 0, 7, True),
    ):
        nc = chunks.get((ncx, ncz))
        if nc is None:
            continue
        nx0 = ncx * CHUNK_SIZE
        nz0 = ncz * CHUNK_SIZE
        nlight = nc.light
        for wy in range(MAX_Y):
            y_off = wy << 6
            for t in range(CHUNK_SIZE):
                if along_x:
                    nx, nz = nx0 + t, nz0 + lz_n
                    sx, sz = x0 + t, z0 + lz_self
                    n_idx = y_off | (lz_n << 3) | t
                    s_idx = y_off | (lz_self << 3) | t
                else:
                    nx, nz = nx0 + lx_n, nz0 + t
                    sx, sz = x0 + lx_self, z0 + t
                    n_idx = y_off | (t << 3) | lx_n
                    s_idx = y_off | (t << 3) | lx_self
                nlv = nlight[n_idx]
                nsky = nlv >> 4
                nblk = nlv & 0x0F
                sb = data[s_idx]
                step_a = STEP_ATTEN[sb]
                if step_a < 15:
                    if nsky - step_a > (light[s_idx] >> 4):
                        sky_q.append((nx, wy, nz))
                    if nblk - step_a > (light[s_idx] & 0x0F):
                        blk_q.append((nx, wy, nz))
                # Also if our edge has higher sky/blk than neighbor, push into neighbor
                slv = light[s_idx]
                if (slv >> 4) > 1:
                    sky_q.append((sx, wy, sz))
                if (slv & 0x0F) > 1:
                    blk_q.append((sx, wy, sz))

    if sky_q:
        _flood_sky(chunks, sky_q, dirty)
    if blk_q:
        _flood_block(chunks, blk_q, dirty)
    return dirty


def _has_open_sky_above(chunks, x, y, z):
    for wy in range(y + 1, MAX_Y):
        bid = _get_block_fast(chunks, x, wy, z)
        if SKY_DOWN_ATTEN[bid] >= 15:
            return False
    return True


def update_light_at_block(world, x, y, z, old_bid, new_bid):
    """Incrementally propagate sky + block light when a block changes at (x, y, z). Returns dirty chunk keys."""
    if y < 0 or y >= MAX_Y:
        return set()
    chunks = world.chunks
    chunk = chunks.get((x >> 3, z >> 3))
    if chunk is None:
        return set()

    dirty = {(x >> 3, z >> 3)}
    old_em = EMIT_LUT[old_bid]
    new_em = EMIT_LUT[new_bid]
    old_step = STEP_ATTEN[old_bid]
    new_step = STEP_ATTEN[new_bid]
    is_overworld = (world.dimension == "overworld")

    # --- 1. Block Light Update (Torches, Glowstone, Lava, Portals, Walls) ---
    blk_add = deque()
    blk_rem = deque()
    cur_blk = _get_blk_fast(chunks, x, y, z)

    if old_em > 0 and new_em < old_em:
        _set_blk_fast(chunks, x, y, z, new_em, dirty)
        blk_rem.append((x, y, z, old_em))
    elif new_step > old_step and cur_blk > 0 and new_em == 0:
        _set_blk_fast(chunks, x, y, z, 0, dirty)
        blk_rem.append((x, y, z, cur_blk))

    if blk_rem:
        while blk_rem:
            vx, vy, vz, old_v = blk_rem.popleft()
            for dx, dy, dz in _NEIGHBORS:
                nx, ny, nz = vx + dx, vy + dy, vz + dz
                if ny < 0 or ny >= MAX_Y:
                    continue
                nc = chunks.get((nx >> 3, nz >> 3))
                if nc is None:
                    continue
                idx = (ny << 6) | ((nz & 7) << 3) | (nx & 7)
                nb = nc.data[idx]
                n_em = EMIT_LUT[nb]
                n_lv = nc.light[idx] & 0x0F
                if n_lv != 0:
                    if n_lv < old_v and n_em == 0:
                        nc.light[idx] = nc.light[idx] & 0xF0
                        dirty.add((nx >> 3, nz >> 3))
                        blk_rem.append((nx, ny, nz, n_lv))
                    elif n_lv >= old_v or n_em > 0:
                        blk_add.append((nx, ny, nz))

    if new_em > 0:
        _set_blk_fast(chunks, x, y, z, new_em, dirty)
        blk_add.append((x, y, z))
    elif new_step < old_step:
        # Opened space -> pull light from brighter adjacent voxels
        for dx, dy, dz in _NEIGHBORS:
            nx, ny, nz = x + dx, y + dy, z + dz
            if 0 <= ny < MAX_Y and _get_blk_fast(chunks, nx, ny, nz) > 1:
                blk_add.append((nx, ny, nz))

    if blk_add:
        _flood_block(chunks, blk_add, dirty)

    # --- 2. Sky Light Update (Daylight shafts, roofs, caves) ---
    if is_overworld:
        sky_add = deque()
        sky_rem = deque()
        cur_sky = _get_sky_fast(chunks, x, y, z)
        new_down = SKY_DOWN_ATTEN[new_bid]
        old_down = SKY_DOWN_ATTEN[old_bid]

        if new_down > old_down:
            # Placed opaque or semi-opaque block -> remove affected sky light & trace direct shaft below
            if cur_sky > 0:
                _set_sky_fast(chunks, x, y, z, 0, dirty)
                sky_rem.append((x, y, z, cur_sky))
            if cur_sky == 15 or _has_open_sky_above(chunks, x, y, z):
                for wy in range(y - 1, -1, -1):
                    wbid = _get_block_fast(chunks, x, wy, z)
                    if SKY_DOWN_ATTEN[wbid] >= 15:
                        break
                    wsky = _get_sky_fast(chunks, x, wy, z)
                    if wsky > 0:
                        _set_sky_fast(chunks, x, wy, z, 0, dirty)
                        sky_rem.append((x, wy, z, wsky))
        elif new_down < old_down:
            # Broke/opened block -> cascade direct sky shaft downward or pull from neighbors
            sky_above = 15 if y == MAX_Y - 1 else _get_sky_fast(chunks, x, y + 1, z)
            open_above = (sky_above == 15 and _has_open_sky_above(chunks, x, y, z))
            if open_above:
                lv_shaft = 15
                for wy in range(y, -1, -1):
                    wbid = _get_block_fast(chunks, x, wy, z)
                    att = SKY_DOWN_ATTEN[wbid]
                    if att >= 15:
                        break
                    lv_shaft = max(0, lv_shaft - att)
                    if lv_shaft <= 0:
                        break
                    if lv_shaft > _get_sky_fast(chunks, x, wy, z):
                        _set_sky_fast(chunks, x, wy, z, lv_shaft, dirty)
                        sky_add.append((x, wy, z))
            else:
                for dx, dy, dz in _NEIGHBORS:
                    nx, ny, nz = x + dx, y + dy, z + dz
                    if 0 <= ny < MAX_Y and _get_sky_fast(chunks, nx, ny, nz) > 1:
                        sky_add.append((nx, ny, nz))

        if sky_rem:
            while sky_rem:
                vx, vy, vz, old_v = sky_rem.popleft()
                for dx, dy, dz in _NEIGHBORS:
                    nx, ny, nz = vx + dx, vy + dy, vz + dz
                    if ny < 0 or ny >= MAX_Y:
                        continue
                    nc = chunks.get((nx >> 3, nz >> 3))
                    if nc is None:
                        continue
                    idx = (ny << 6) | ((nz & 7) << 3) | (nx & 7)
                    n_sky = nc.light[idx] >> 4
                    if n_sky != 0:
                        # Downward step under same open sky can still be 15 in neighboring column;
                        # only clear neighbors strictly darker than old_v!
                        if n_sky < old_v:
                            nc.light[idx] = nc.light[idx] & 0x0F
                            dirty.add((nx >> 3, nz >> 3))
                            sky_rem.append((nx, ny, nz, n_sky))
                        elif n_sky >= old_v:
                            sky_add.append((nx, ny, nz))

        if sky_add:
            _flood_sky(chunks, sky_add, dirty)

    return dirty
