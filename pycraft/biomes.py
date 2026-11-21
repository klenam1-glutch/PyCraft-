"""Procedural multi-noise biome engine (Snowy Mountains, Forest, Taiga, Desert, Badlands, Plains, River)."""

from pycraft.constants import (
    DIRT, GRASS, GRAVEL, MAX_Y, RED_SANDSTONE, SAND, SANDSTONE,
    SNOW, SNOW_BLOCK, STONE, TERRACOTTA, WATER_LEVEL,
)
from pycraft.noise import fbm_2d, ridged_2d


def sample_climate(x, z, seed):
    """Evaluate 4 orthogonal noise fields: temperature, moisture, continentalness, and ridge."""
    temp = fbm_2d(x + 120, z - 85, seed + 505, freq=0.0085, octaves=2)
    moist = fbm_2d(x - 240, z + 170, seed + 808, freq=0.0095, octaves=2)
    cont = fbm_2d(x + 45, z + 60, seed + 121, freq=0.0078, octaves=3)
    ridge = ridged_2d(x - 60, z - 40, seed + 303, freq=0.022, octaves=2)
    detail = fbm_2d(x, z, seed, freq=0.048, octaves=2)
    return temp, moist, cont, ridge, detail


def classify_biome(temp, moist, cont, ridge):
    """Map continuous climate noise parameters to distinct Minecraft biomes."""
    if cont < 0.34:
        return "river"
    if (cont > 0.56 and temp < 0.48) or (cont > 0.63 and ridge > 0.55):
        return "snowy_mountains"
    if temp < 0.37:
        return "taiga"
    if temp > 0.62 and cont > 0.52:
        return "badlands"
    if temp > 0.60 and moist < 0.50:
        return "desert"
    if moist > 0.53:
        return "forest"
    return "plains"


def _column_from_climate(temp, moist, cont, ridge, detail):
    biome = classify_biome(temp, moist, cont, ridge)
    base_h = 5.0 + cont * 9.5 + (detail - 0.5) * 4.5

    if biome == "river":
        river_dip = max(0.0, (0.35 - cont) * 14.0)
        h = int(WATER_LEVEL + 1 - river_dip + (detail - 0.5) * 2.0)
        top_bid = GRAVEL if h < WATER_LEVEL else GRASS
        sub_bid = GRAVEL
        deep_bid = STONE
    elif biome == "snowy_mountains":
        uplift = max(0.0, (cont - 0.54) * 26.0) + max(0.0, ridge - 0.35) * 14.0
        h = int(base_h + uplift)
        top_bid = SNOW if h >= 13 else (STONE if h >= 10 else GRASS)
        sub_bid = SNOW_BLOCK if h >= 16 else STONE
        deep_bid = STONE
    elif biome == "taiga":
        h = int(base_h + max(0.0, ridge - 0.55) * 6.0)
        top_bid = SNOW if (temp < 0.30 or h >= 14) else GRASS
        sub_bid = DIRT
        deep_bid = STONE
    elif biome == "badlands":
        plateau = min(1.0, max(0.0, (cont - 0.50) * 5.0))
        step_h = int((ridge * 8.0) // 2) * 2
        h = int(base_h + plateau * (4.0 + step_h))
        top_bid = TERRACOTTA
        sub_bid = RED_SANDSTONE
        deep_bid = RED_SANDSTONE
    elif biome == "desert":
        dune = ridge * 3.8 + (detail - 0.5) * 2.5
        h = int(6.5 + cont * 4.5 + dune)
        top_bid = SAND
        sub_bid = SANDSTONE
        deep_bid = STONE
    elif biome == "forest":
        h = int(base_h + max(0.0, ridge - 0.62) * 5.5)
        top_bid = GRASS
        sub_bid = DIRT
        deep_bid = STONE
    else:  # plains
        h = int(6.5 + cont * 5.5 + (detail - 0.5) * 3.2)
        top_bid = GRASS
        sub_bid = DIRT
        deep_bid = STONE

    h = max(2, min(MAX_Y - 6, h))
    return biome, h, top_bid, sub_bid, deep_bid


def sample_biome_column(x, z, seed):
    """
    Compute (biome, surface_height, top_block, sub_block, deep_block)
    with continuous noise-blended elevation across distinct biome regions.
    """
    temp, moist, cont, ridge, detail = sample_climate(x, z, seed)
    return _column_from_climate(temp, moist, cont, ridge, detail)


def sample_chunk_columns(x0, z0, seed):
    """
    Fast 8x8 chunk column sampler: bilinearly interpolates low-frequency macro
    climate fields (temp, moist, cont) across chunk corners while sampling fine
    ridge and terrain detail per column.
    """
    c00 = sample_climate(x0, z0, seed)
    c10 = sample_climate(x0 + 8, z0, seed)
    c01 = sample_climate(x0, z0 + 8, seed)
    c11 = sample_climate(x0 + 8, z0 + 8, seed)

    t00, m00, k00 = c00[0], c00[1], c00[2]
    t10, m10, k10 = c10[0], c10[1], c10[2]
    t01, m01, k01 = c01[0], c01[1], c01[2]
    t11, m11, k11 = c11[0], c11[1], c11[2]

    out = [None] * 64
    s_ridge = seed + 303
    for lx in range(8):
        u = lx * 0.125
        wx = x0 + lx
        tx0 = t00 + (t10 - t00) * u
        tx1 = t01 + (t11 - t01) * u
        mx0 = m00 + (m10 - m00) * u
        mx1 = m01 + (m11 - m01) * u
        kx0 = k00 + (k10 - k00) * u
        kx1 = k01 + (k11 - k01) * u
        for lz in range(8):
            v = lz * 0.125
            wz = z0 + lz
            temp = tx0 + (tx1 - tx0) * v
            moist = mx0 + (mx1 - mx0) * v
            cont = kx0 + (kx1 - kx0) * v
            ridge = ridged_2d(wx - 60, wz - 40, s_ridge, freq=0.022, octaves=2)
            detail = fbm_2d(wx, wz, seed, freq=0.048, octaves=2)
            out[(lz << 3) | lx] = _column_from_climate(temp, moist, cont, ridge, detail)
    return out
