"""Deterministic hashing, 2D value noise, FBM, and ridged mountain noise."""

import math


_FLOOR = math.floor


def hash2(ix, iz, seed):
    n = (ix * 374761393 + iz * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) * (1.0 / 65535.0)


def hash3(ix, iy, iz, seed):
    n = (ix * 374761393 + iy * 1274126177 + iz * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 2246822519) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) * (1.0 / 65535.0)


def smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def value_noise_2d(x, z, seed):
    ix = _FLOOR(x)
    iz = _FLOOR(z)
    tx = x - ix
    tz = z - iz
    fx = tx * tx * (3.0 - 2.0 * tx)
    fz = tz * tz * (3.0 - 2.0 * tz)

    s_part = seed * 1442695041
    x0 = ix * 374761393 + s_part
    x1 = x0 + 374761393
    z0 = iz * 668265263
    z1 = z0 + 668265263
    inv = 1.0 / 65535.0

    n00 = (x0 + z0) & 0xFFFFFFFF
    n00 = ((n00 ^ (n00 >> 13)) * 1274126177) & 0xFFFFFFFF
    v00 = ((n00 ^ (n00 >> 16)) & 0xFFFF) * inv

    n10 = (x1 + z0) & 0xFFFFFFFF
    n10 = ((n10 ^ (n10 >> 13)) * 1274126177) & 0xFFFFFFFF
    v10 = ((n10 ^ (n10 >> 16)) & 0xFFFF) * inv

    n01 = (x0 + z1) & 0xFFFFFFFF
    n01 = ((n01 ^ (n01 >> 13)) * 1274126177) & 0xFFFFFFFF
    v01 = ((n01 ^ (n01 >> 16)) & 0xFFFF) * inv

    n11 = (x1 + z1) & 0xFFFFFFFF
    n11 = ((n11 ^ (n11 >> 13)) * 1274126177) & 0xFFFFFFFF
    v11 = ((n11 ^ (n11 >> 16)) & 0xFFFF) * inv

    vx0 = v00 + (v10 - v00) * fx
    vx1 = v01 + (v11 - v01) * fx
    return vx0 + (vx1 - vx0) * fz


def fbm_2d(x, z, seed, freq=0.045, octaves=3):
    val = 0.0
    amp = 0.55
    norm = 0.0
    f = freq
    vn = value_noise_2d
    for i in range(octaves):
        val += amp * vn(x * f, z * f, seed + i * 101)
        norm += amp
        f *= 2.05
        amp *= 0.48
    return val / norm if norm else 0.5


def ridged_2d(x, z, seed, freq=0.024, octaves=2):
    val = 0.0
    amp = 0.65
    norm = 0.0
    f = freq
    vn = value_noise_2d
    for i in range(octaves):
        n = 1.0 - abs(vn(x * f, z * f, seed + i * 211) * 2.0 - 1.0)
        val += amp * (n * n)
        norm += amp
        f *= 2.1
        amp *= 0.45
    return val / norm if norm else 0.5
