"""High-FPS 3D Minecraft renderer: full-scale 16x16 & 8x8 greedy UV patches, chunk/frustum culling, 3D mobs, clouds."""

import math
from operator import itemgetter

from pycraft.blocks import BLOCKS
from pycraft.constants import (
    BED, CHUNK_SIZE, DOOR_OPEN, FACES, FLOWER_RED, FLOWER_YELLOW, LADDER, MAX_Y, NEAR_PLANE, TORCH,
)
from pycraft.mobs import MOB_STATS

_ITEM0 = itemgetter(0)

# Precomputed O(1) flat lookup tables indexed by block ID (0..63)
_BLK_TOP = tuple((BLOCKS[i]["top"] if i in BLOCKS else (128, 128, 128)) for i in range(64))
_BLK_BOT = tuple((BLOCKS[i]["bottom"] if i in BLOCKS else (128, 128, 128)) for i in range(64))
_BLK_SIDE = tuple((BLOCKS[i]["side"] if i in BLOCKS else (128, 128, 128)) for i in range(64))
_BLK_EMISSIVE = tuple((BLOCKS[i]["emissive"] if i in BLOCKS else False) for i in range(64))
_BLK_TRANS = tuple((BLOCKS[i]["transparent"] if i in BLOCKS else True) for i in range(64))
_BLK_SPECIAL = tuple((i in (TORCH, FLOWER_RED, FLOWER_YELLOW, BED, LADDER, DOOR_OPEN)) for i in range(64))
_SKY_CURVE = tuple(0.16 + 0.84 * ((i / 15.0) ** 1.15) for i in range(16))
_BLK_CURVE = tuple(0.0 if i == 0 else (0.16 + 0.84 * ((i / 15.0) ** 1.15)) for i in range(16))

# Unit cube corner table & face vertex indices matching constants.FACES corner ordering
_UNIT_CORNERS = (
    (0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0),
    (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1),
)
_CORNER_MAP = {c: idx for idx, c in enumerate(_UNIT_CORNERS)}
_FACE_CORNER_IDX = tuple(tuple(_CORNER_MAP[c] for c in f[4]) for f in FACES)
_FACES_META = tuple((f[0], f[1], f[2], f[3], _FACE_CORNER_IDX[i]) for i, f in enumerate(FACES))


def clip_poly_near(cam_pts):
    if not cam_pts:
        return []
    out = []
    n = len(cam_pts)
    for i in range(n):
        a = cam_pts[i]
        b = cam_pts[(i + 1) % n]
        az, bz = a[2], b[2]
        a_in = az >= NEAR_PLANE
        b_in = bz >= NEAR_PLANE
        if a_in and b_in:
            out.append(b)
        elif a_in and not b_in:
            t = (NEAR_PLANE - az) / (bz - az)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, NEAR_PLANE))
        elif not a_in and b_in:
            t = (NEAR_PLANE - az) / (bz - az)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, NEAR_PLANE))
            out.append(b)
    return out


def compute_sky_and_light(time_of_day, dimension="overworld", bright_boost=True,
                          weather="clear", weather_intensity=0.0, lightning_flash=0.0):
    if dimension == "nether":
        return (84, 24, 22), 0.78, (0.0, -1.0, 0.2), False, 0.2

    ang = time_of_day * math.tau
    sun_y = math.sin(ang)
    sun_x = math.cos(ang)
    day = max(0.0, min(1.0, (sun_y + 0.25) / 0.65))
    sunset = max(0.0, 1.0 - abs(sun_y) * 3.5)

    night_sky = (16, 24, 46)
    day_sky = (124, 194, 250)
    sunset_sky = (232, 128, 82)

    r = night_sky[0] + (day_sky[0] - night_sky[0]) * day
    g = night_sky[1] + (day_sky[1] - night_sky[1]) * day
    b = night_sky[2] + (day_sky[2] - night_sky[2]) * day

    r += (sunset_sky[0] - r) * sunset * 0.58
    g += (sunset_sky[1] - g) * sunset * 0.42
    b += (sunset_sky[2] - b) * sunset * 0.28

    min_amb = 0.42 if bright_boost else 0.24
    ambient = min_amb + (1.0 - min_amb) * day

    if weather_intensity > 0.0:
        is_thunder = (weather == "thunder")
        sr, sg, sb = (44, 54, 72) if is_thunder else (78, 94, 118)
        blend = min(0.82, weather_intensity * (0.76 if is_thunder else 0.56))
        # Keep storm sky scaled gently by daylight
        sc = 0.35 + 0.65 * day
        r += (sr * sc - r) * blend
        g += (sg * sc - g) * blend
        b += (sb * sc - b) * blend
        ambient *= (1.0 - weather_intensity * (0.16 if is_thunder else 0.10))

    if lightning_flash > 0.0:
        lf = lightning_flash
        r += (232.0 - r) * lf * 0.78
        g += (240.0 - g) * lf * 0.78
        b += (255.0 - b) * lf * 0.85
        ambient = min(1.0, ambient + lf * 0.48)

    is_day = sun_y > -0.05
    return (int(r), int(g), int(b)), ambient, (sun_x, sun_y, 0.28), is_day, day


def _project_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                 bx0, by0, bz0, bx1, by1, bz1, base_rgb, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span,
                 emissive=False):
    out = []
    bcx = (bx0 + bx1) * 0.5
    bcy = (by0 + by1) * 0.5
    bcz = (bz0 + bz1) * 0.5
    vx_b = bcx - cx
    vy_b = bcy - cy
    vz_b = bcz - cz
    dist_sq = vx_b * vx_b + vy_b * vy_b + vz_b * vz_b
    if dist_sq > max_dist_sq:
        return out
    if vx_b * fx + vy_b * fy + vz_b * fz < -1.2:
        return out

    sky_r, sky_g, sky_b = sky_rgb
    hx = (bx1 - bx0) * 0.5
    hy = (by1 - by0) * 0.5
    hz = (bz1 - bz0) * 0.5
    light_mul = 1.0 if emissive else ambient
    fog_t = min(1.0, (dist_sq - fog_start_sq) / fog_span) if dist_sq > fog_start_sq else 0.0

    for fidx, (nx, ny, nz, shade, corners) in enumerate(FACES):
        fcx = bcx + nx * hx
        fcy = bcy + ny * hy
        fcz = bcz + nz * hz
        if (fcx - cx) * nx + (fcy - cy) * ny + (fcz - cz) * nz >= 0.0:
            continue
        cam_pts = []
        any_in = False
        for c in corners:
            kx = bx0 if c[0] == 0 else bx1
            ky = by0 if c[1] == 0 else by1
            kz = bz0 if c[2] == 0 else bz1
            dx, dy, dz = kx - cx, ky - cy, kz - cz
            pz = dx * fx + dy * fy + dz * fz
            if pz >= NEAR_PLANE:
                any_in = True
            cam_pts.append((dx * rx + dz * rz, dx * ux + dy * uy + dz * uz, pz))
        if not any_in:
            continue
        clipped = clip_poly_near(cam_pts)
        if len(clipped) < 3:
            continue
        pts2d = [(half_w + (px / pz) * focal, half_h - (py / pz) * focal) for px, py, pz in clipped]
        lit = shade * light_mul
        cr, cg, cb = base_rgb[0] * lit, base_rgb[1] * lit, base_rgb[2] * lit
        if fog_t > 0.0:
            cr += (sky_r - cr) * fog_t
            cg += (sky_g - cg) * fog_t
            cb += (sky_b - cb) * fog_t
        fdist_sq = (fcx - cx) ** 2 + (fcy - cy) ** 2 + (fcz - cz) ** 2
        out.append((fdist_sq, pts2d, (int(cr), int(cg), int(cb)), 0, fidx, False, None))
    return out


def _project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                          mx, my, mz, syaw, cyaw, lx0, ly0, lz0, lx1, ly1, lz1,
                          base_rgb, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span, emissive=False):
    """Project a box rotated around mob's local Y axis by syaw/cyaw (for faces, snouts, arms)."""
    # Transform local center to world
    lcx = (lx0 + lx1) * 0.5
    lcy = (ly0 + ly1) * 0.5
    lcz = (lz0 + lz1) * 0.5
    wcx = mx + lcx * cyaw + lcz * syaw
    wcy = my + lcy
    wcz = mz - lcx * syaw + lcz * cyaw
    vx_b = wcx - cx
    vy_b = wcy - cy
    vz_b = wcz - cz
    dist_sq = vx_b * vx_b + vy_b * vy_b + vz_b * vz_b
    if dist_sq > max_dist_sq or (vx_b * fx + vy_b * fy + vz_b * fz < -1.0):
        return []

    sky_r, sky_g, sky_b = sky_rgb
    light_mul = 1.0 if emissive else ambient
    fog_t = min(1.0, (dist_sq - fog_start_sq) / fog_span) if dist_sq > fog_start_sq else 0.0
    out = []
    for fidx, (nx, ny, nz, shade, corners) in enumerate(FACES):
        wnx = nx * cyaw + nz * syaw
        wnz = -nx * syaw + nz * cyaw
        if vx_b * wnx + vy_b * ny + vz_b * wnz >= 0.0:
            continue
        cam_pts = []
        any_in = False
        for c in corners:
            klx = lx0 if c[0] == 0 else lx1
            kly = ly0 if c[1] == 0 else ly1
            klz = lz0 if c[2] == 0 else lz1
            wx = mx + klx * cyaw + klz * syaw
            wy = my + kly
            wz = mz - klx * syaw + klz * cyaw
            dx, dy, dz = wx - cx, wy - cy, wz - cz
            pz = dx * fx + dy * fy + dz * fz
            if pz >= NEAR_PLANE:
                any_in = True
            cam_pts.append((dx * rx + dz * rz, dx * ux + dy * uy + dz * uz, pz))
        if not any_in:
            continue
        clipped = clip_poly_near(cam_pts)
        if len(clipped) < 3:
            continue
        pts2d = [(half_w + (px / pz) * focal, half_h - (py / pz) * focal) for px, py, pz in clipped]
        lit = shade * light_mul
        cr, cg, cb = base_rgb[0] * lit, base_rgb[1] * lit, base_rgb[2] * lit
        if fog_t > 0.0:
            cr += (sky_r - cr) * fog_t
            cg += (sky_g - cg) * fog_t
            cb += (sky_b - cb) * fog_t
        out.append((dist_sq - 0.02, pts2d, (int(cr), int(cg), int(cb)), 0, fidx, False, None))
    return out


def _project_tex_patches_3d(c0, c1, c2, c3, patches, lit, sky_rgb, fog_t, half_w, half_h, focal):
    """Perspective-correct full-scale 16x16 UV patch projection for ultra-close blocks (< 1.8m)."""
    c0x, c0y, c0z = c0
    c1x, c1y, c1z = c1
    c2x, c2y, c2z = c2
    c3x, c3y, c3z = c3
    top_dx, top_dy, top_dz = c1x - c0x, c1y - c0y, c1z - c0z
    bot_dx, bot_dy, bot_dz = c2x - c3x, c2y - c3y, c2z - c3z
    left_dx, left_dy, left_dz = c3x - c0x, c3y - c0y, c3z - c0z
    right_dx, right_dy, right_dz = c2x - c1x, c2y - c1y, c2z - c1z

    sky_r, sky_g, sky_b = sky_rgb
    has_fog = fog_t > 0.0
    if has_fog:
        lit_m = lit * (1.0 - fog_t)
        fr, fg, fb = sky_r * fog_t, sky_g * fog_t, sky_b * fog_t

    out = []
    append = out.append
    # Span vectors from v0..v1 top & bottom edges
    for u0, v0, u1, v1, rgb in patches:
        l0x = c0x + left_dx * v0
        l0y = c0y + left_dy * v0
        l0z = c0z + left_dz * v0
        r0x = c1x + right_dx * v0
        r0y = c1y + right_dy * v0
        r0z = c1z + right_dz * v0
        d0x, d0y, d0z = r0x - l0x, r0y - l0y, r0z - l0z

        l1x = c0x + left_dx * v1
        l1y = c0y + left_dy * v1
        l1z = c0z + left_dz * v1
        r1x = c1x + right_dx * v1
        r1y = c1y + right_dy * v1
        r1z = c1z + right_dz * v1
        d1x, d1y, d1z = r1x - l1x, r1y - l1y, r1z - l1z

        iz = focal / (l0z + d0z * u0)
        q0 = (half_w + (l0x + d0x * u0) * iz, half_h - (l0y + d0y * u0) * iz)
        iz = focal / (l0z + d0z * u1)
        q1 = (half_w + (l0x + d0x * u1) * iz, half_h - (l0y + d0y * u1) * iz)
        iz = focal / (l1z + d1z * u1)
        q2 = (half_w + (l1x + d1x * u1) * iz, half_h - (l1y + d1y * u1) * iz)
        iz = focal / (l1z + d1z * u0)
        q3 = (half_w + (l1x + d1x * u0) * iz, half_h - (l1y + d1y * u0) * iz)

        if has_fog:
            col = (int(rgb[0] * lit_m + fr), int(rgb[1] * lit_m + fg), int(rgb[2] * lit_m + fb))
        else:
            col = (int(rgb[0] * lit), int(rgb[1] * lit), int(rgb[2] * lit))
        append(((q0, q1, q2, q3), col))
    return out


def _project_tex_patches_2d(p0, p1, p2, p3, patches, lit, sky_rgb, fog_t):
    """Ultra-fast screen-space bilinear UV patch projection for 16x16 & 8x8 detail textures."""
    p0x, p0y = p0
    p1x, p1y = p1
    p2x, p2y = p2
    p3x, p3y = p3
    lx_d, ly_d = p3x - p0x, p3y - p0y
    rx_d, ry_d = p2x - p1x, p2y - p1y

    has_fog = fog_t > 0.0
    if has_fog:
        sky_r, sky_g, sky_b = sky_rgb
        lit_m = lit * (1.0 - fog_t)
        fr, fg, fb = sky_r * fog_t, sky_g * fog_t, sky_b * fog_t

    out = []
    append = out.append
    for u0, v0, u1, v1, rgb in patches:
        t_lx = p0x + lx_d * v0
        t_ly = p0y + ly_d * v0
        t_dx = (p1x + rx_d * v0) - t_lx
        t_dy = (p1y + ry_d * v0) - t_ly

        b_lx = p0x + lx_d * v1
        b_ly = p0y + ly_d * v1
        b_dx = (p1x + rx_d * v1) - b_lx
        b_dy = (p1y + ry_d * v1) - b_ly

        q0 = (t_lx + t_dx * u0, t_ly + t_dy * u0)
        q1 = (t_lx + t_dx * u1, t_ly + t_dy * u1)
        q2 = (b_lx + b_dx * u1, b_ly + b_dy * u1)
        q3 = (b_lx + b_dx * u0, b_ly + b_dy * u0)

        if has_fog:
            col = (int(rgb[0] * lit_m + fr), int(rgb[1] * lit_m + fg), int(rgb[2] * lit_m + fb))
        else:
            col = (int(rgb[0] * lit), int(rgb[1] * lit), int(rgb[2] * lit))
        append(((q0, q1, q2, q3), col))
    return out


class VoxelRenderer:
    __slots__ = ("assets", "render_dist", "perf_mode", "stars", "clouds")

    def __init__(self, assets=None, render_dist=15, perf_mode="balanced"):
        self.assets = assets
        self.render_dist = render_dist
        self.perf_mode = perf_mode
        self.stars = tuple(
            (math.cos(i * 2.39996) * math.cos(0.35 + (i % 7) * 0.14),
             0.35 + (i % 9) * 0.07,
             math.sin(i * 2.39996) * math.cos(0.35 + (i % 7) * 0.14))
            for i in range(48)
        )
        # Deterministic boxy Minecraft cloud patches
        self.clouds = tuple(
            ((i * 17) % 64 - 32, (i * 29) % 64 - 32, 3.5 + (i % 3) * 1.5, 2.5 + ((i + 1) % 3) * 1.5)
            for i in range(14)
        )

    def build_draw_list(self, world, player, width, height, sky_rgb, ambient, target_block,
                        use_tex_grid=True, cloud_shift=0.0, hand_light=False):
        cx = player.x
        cy = player.eye_y + math.sin(player.walk_bob) * 0.035
        cz = player.z

        sin_y = math.sin(player.yaw)
        cos_y = math.cos(player.yaw)
        sin_p = math.sin(player.pitch)
        cos_p = math.cos(player.pitch)

        fx = sin_y * cos_p
        fy = sin_p
        fz = cos_y * cos_p
        rx = cos_y
        rz = -sin_y
        ux = -sin_p * sin_y
        uy = cos_p
        uz = -sin_p * cos_y

        half_w = width * 0.5
        half_h = height * 0.5
        focal = width * 0.96 if height > width else min(width, height) * 0.85
        fov_x = (half_w / focal) + 0.18
        fov_y = (half_h / focal) + 0.18

        max_dist = self.render_dist
        max_dist_sq = max_dist * max_dist
        chunk_max_sq = (max_dist + 6.5) ** 2
        fog_start_sq = (max_dist * 0.78) ** 2
        fog_span = max(1.0, max_dist_sq - fog_start_sq)

        if not use_tex_grid:
            tex16_sq = 0.0
            tex8_sq = 0.0
        elif self.perf_mode == "fast":
            tex16_sq = 5.5
            tex8_sq = 14.0
        elif self.perf_mode == "fancy":
            tex16_sq = 30.0
            tex8_sq = 64.0
        else:  # balanced: full-scale 16x16 up to 4 blocks + 8x8 out to ~6.3 blocks
            tex16_sq = 16.0
            tex8_sq = 40.0

        pcx = math.floor(cx) >> 3
        pcz = math.floor(cz) >> 3
        rc = int(math.ceil(max_dist / CHUNK_SIZE)) + 1

        sky_r, sky_g, sky_b = sky_rgb
        default_lv = 0xF0 if world.dimension == "overworld" else 0
        sky_curve = _SKY_CURVE
        blk_curve = _BLK_CURVE

        # Precompute 8 unit-cube corner camera-space deltas ONCE per frame
        cube_cam = tuple(
            (
                ox * rx + oz * rz,
                ox * ux + oy * uy + oz * uz,
                ox * fx + oy * fy + oz * fz,
            )
            for ox, oy, oz in _UNIT_CORNERS
        )

        chunks = world.chunks
        draw_faces = []
        append_face = draw_faces.append
        faces_meta = _FACES_META
        corners_meta = FACES
        blk_top = _BLK_TOP
        blk_bot = _BLK_BOT
        blk_side = _BLK_SIDE
        blk_emissive = _BLK_EMISSIVE
        blk_trans = _BLK_TRANS
        blk_special = _BLK_SPECIAL
        face_base = self.assets.face_base_rgb if self.assets else None
        face_p16 = self.assets.face_patches_16 if self.assets else None
        face_p8 = self.assets.face_patches_8 if self.assets else None
        tx_target, ty_target, tz_target = target_block if target_block is not None else (-999999, -999999, -999999)

        for dcx in range(-rc, rc + 1):
            ccx = pcx + dcx
            x0 = ccx * CHUNK_SIZE
            x0_rel = x0 - cx
            cdx = x0_rel + 4.0
            cdx_sq = cdx * cdx
            if cdx_sq > chunk_max_sq:
                continue
            for dcz in range(-rc, rc + 1):
                ccz = pcz + dcz
                z0 = ccz * CHUNK_SIZE
                z0_rel = z0 - cz
                cdz = z0_rel + 4.0
                if cdx_sq + cdz * cdz > chunk_max_sq:
                    continue
                cpz_c = cdx * fx + cdz * fz
                if cpz_c < -7.5:
                    continue
                if cpz_c > 2.0 and abs(cdx * rx + cdz * rz) > cpz_c * fov_x + 7.5:
                    continue
                chunk = chunks.get((ccx, ccz))
                if chunk is None or not chunk.faces:
                    continue
                c_light = chunk.light
                xp_c = chunks.get((ccx + 1, ccz))
                xm_c = chunks.get((ccx - 1, ccz))
                zp_c = chunks.get((ccx, ccz + 1))
                zm_c = chunks.get((ccx, ccz - 1))
                xp_l = xp_c.light if xp_c is not None else None
                xm_l = xm_c.light if xm_c is not None else None
                zp_l = zp_c.light if zp_c is not None else None
                zm_l = zm_c.light if zm_c is not None else None
                for pf in chunk.faces:
                    lx = pf & 7
                    lz = (pf >> 3) & 7
                    by = (pf >> 6) & 31
                    fidx = (pf >> 11) & 7
                    bid = (pf >> 14) & 63

                    dx0 = x0_rel + lx
                    dy0 = by - cy
                    dz0 = z0_rel + lz
                    nx, ny, nz, shade, v_idxs = faces_meta[fidx]

                    vx = dx0 + 0.5 + nx * 0.5
                    vy = dy0 + 0.5 + ny * 0.5
                    vz = dz0 + 0.5 + nz * 0.5
                    dist_sq = vx * vx + vy * vy + vz * vz
                    if dist_sq > max_dist_sq:
                        continue
                    if vx * nx + vy * ny + vz * nz >= 0.0:
                        continue
                    pz_c = vx * fx + vy * fy + vz * fz
                    if pz_c < -0.78:
                        continue
                    if pz_c > 1.2:
                        if abs(vx * rx + vz * rz) > pz_c * fov_x + 1.45:
                            continue
                        if abs(vx * ux + vy * uy + vz * uz) > pz_c * fov_y + 1.45:
                            continue

                    if not blk_special[bid]:
                        # Ultra-fast unit-cube face transform using precomputed corner deltas
                        bpx = dx0 * rx + dz0 * rz
                        bpy = dx0 * ux + dy0 * uy + dz0 * uz
                        bpz = dx0 * fx + dy0 * fy + dz0 * fz

                        c0d = cube_cam[v_idxs[0]]
                        c1d = cube_cam[v_idxs[1]]
                        c2d = cube_cam[v_idxs[2]]
                        c3d = cube_cam[v_idxs[3]]

                        z0p = bpz + c0d[2]
                        z1p = bpz + c1d[2]
                        z2p = bpz + c2d[2]
                        z3p = bpz + c3d[2]

                        all_in_front = (z0p >= NEAR_PLANE and z1p >= NEAR_PLANE and z2p >= NEAR_PLANE and z3p >= NEAR_PLANE)
                        if all_in_front:
                            p0 = (bpx + c0d[0], bpy + c0d[1], z0p)
                            p1 = (bpx + c1d[0], bpy + c1d[1], z1p)
                            p2 = (bpx + c2d[0], bpy + c2d[1], z2p)
                            p3 = (bpx + c3d[0], bpy + c3d[1], z3p)

                            iz0 = focal / z0p
                            s0x, s0y = half_w + p0[0] * iz0, half_h - p0[1] * iz0
                            iz1 = focal / z1p
                            s1x, s1y = half_w + p1[0] * iz1, half_h - p1[1] * iz1
                            iz2 = focal / z2p
                            s2x, s2y = half_w + p2[0] * iz2, half_h - p2[1] * iz2
                            iz3 = focal / z3p
                            s3x, s3y = half_w + p3[0] * iz3, half_h - p3[1] * iz3

                            min_sx = min(s0x, s1x, s2x, s3x)
                            max_sx = max(s0x, s1x, s2x, s3x)
                            if max_sx < 0 or min_sx > width:
                                continue
                            min_sy = min(s0y, s1y, s2y, s3y)
                            max_sy = max(s0y, s1y, s2y, s3y)
                            if max_sy < 0 or min_sy > height:
                                continue
                            if max_sx - min_sx < 1.5 and max_sy - min_sy < 1.5:
                                continue

                            pts2d = ((s0x, s0y), (s1x, s1y), (s2x, s2y), (s3x, s3y))
                            cam_pts = (p0, p1, p2, p3)
                        else:
                            if z0p < NEAR_PLANE and z1p < NEAR_PLANE and z2p < NEAR_PLANE and z3p < NEAR_PLANE:
                                continue
                            clipped = clip_poly_near((
                                (bpx + c0d[0], bpy + c0d[1], z0p),
                                (bpx + c1d[0], bpy + c1d[1], z1p),
                                (bpx + c2d[0], bpy + c2d[1], z2p),
                                (bpx + c3d[0], bpy + c3d[1], z3p),
                            ))
                            if len(clipped) < 3:
                                continue
                            pts2d = []
                            min_sx, max_sx = 1e9, -1e9
                            min_sy, max_sy = 1e9, -1e9
                            for px, py, pz in clipped:
                                inv_z = focal / pz
                                sx = half_w + px * inv_z
                                sy = half_h - py * inv_z
                                pts2d.append((sx, sy))
                                if sx < min_sx:
                                    min_sx = sx
                                if sx > max_sx:
                                    max_sx = sx
                                if sy < min_sy:
                                    min_sy = sy
                                if sy > max_sy:
                                    max_sy = sy
                            if max_sx < 0 or min_sx > width or max_sy < 0 or min_sy > height:
                                continue
                            if max_sx - min_sx < 1.5 and max_sy - min_sy < 1.5:
                                continue
                            cam_pts = None
                    else:
                        cam_pts = []
                        all_in_front = True
                        any_in_front = False
                        bx = x0 + lx
                        bz = z0 + lz
                        corners = corners_meta[fidx][4]
                        if bid == TORCH:
                            ox0, sx0, sy0 = 0.36, 0.28, 0.68
                        elif bid in (FLOWER_RED, FLOWER_YELLOW):
                            ox0, sx0, sy0 = 0.28, 0.44, 0.62
                        elif bid == BED:
                            ox0, sx0, sy0 = 0.0, 1.0, 0.56
                        else:  # LADDER / DOOR_OPEN
                            ox0, sx0, sy0 = 0.0, 0.22, 1.0

                        for c in corners:
                            if bid in (LADDER, DOOR_OPEN):
                                dx = (bx + c[0] * sx0) - cx
                                dy = (by + c[1] * sy0) - cy
                                dz = (bz + c[2]) - cz
                            else:
                                dx = (bx + ox0 + c[0] * sx0) - cx
                                dy = (by + c[1] * sy0) - cy
                                dz = (bz + ox0 + c[2] * sx0) - cz
                            pz = dx * fx + dy * fy + dz * fz
                            if pz >= NEAR_PLANE:
                                any_in_front = True
                            else:
                                all_in_front = False
                            cam_pts.append((dx * rx + dz * rz, dx * ux + dy * uy + dz * uz, pz))

                        if not any_in_front:
                            continue
                        clipped = cam_pts if all_in_front else clip_poly_near(cam_pts)
                        if len(clipped) < 3:
                            continue
                        pts2d = []
                        min_sx, max_sx = 1e9, -1e9
                        min_sy, max_sy = 1e9, -1e9
                        for px, py, pz in clipped:
                            inv_z = focal / pz
                            sx = half_w + px * inv_z
                            sy = half_h - py * inv_z
                            pts2d.append((sx, sy))
                            if sx < min_sx:
                                min_sx = sx
                            if sx > max_sx:
                                max_sx = sx
                            if sy < min_sy:
                                min_sy = sy
                            if sy > max_sy:
                                max_sy = sy
                        if max_sx < 0 or min_sx > width or max_sy < 0 or min_sy > height:
                            continue
                        if max_sx - min_sx < 1.5 and max_sy - min_sy < 1.5:
                            continue

                    gkey = (bid << 3) | fidx
                    dom_rgb = face_base[gkey] if (face_base is not None and not blk_trans[bid]) else None
                    base_rgb = dom_rgb if dom_rgb is not None else (
                        blk_top[bid] if fidx == 0 else (blk_bot[bid] if fidx == 1 else blk_side[bid])
                    )
                    bx = x0 + lx
                    bz = z0 + lz

                    if blk_emissive[bid]:
                        light = 1.0
                    else:
                        if fidx == 0:
                            lv = c_light[((by + 1) << 6) | (lz << 3) | lx] if by < MAX_Y - 1 else default_lv
                        elif fidx == 1:
                            lv = c_light[((by - 1) << 6) | (lz << 3) | lx] if by > 0 else 0
                        elif fidx == 2:
                            if lx < 7:
                                lv = c_light[(by << 6) | (lz << 3) | (lx + 1)]
                            elif xp_l is not None:
                                lv = xp_l[(by << 6) | (lz << 3)]
                            else:
                                lv = default_lv
                        elif fidx == 3:
                            if lx > 0:
                                lv = c_light[(by << 6) | (lz << 3) | (lx - 1)]
                            elif xm_l is not None:
                                lv = xm_l[(by << 6) | (lz << 3) | 7]
                            else:
                                lv = default_lv
                        elif fidx == 4:
                            if lz < 7:
                                lv = c_light[(by << 6) | ((lz + 1) << 3) | lx]
                            elif zp_l is not None:
                                lv = zp_l[(by << 6) | lx]
                            else:
                                lv = default_lv
                        else:  # fidx == 5
                            if lz > 0:
                                lv = c_light[(by << 6) | ((lz - 1) << 3) | lx]
                            elif zm_l is not None:
                                lv = zm_l[(by << 6) | 56 | lx]
                            else:
                                lv = default_lv

                        sky_lit = sky_curve[lv >> 4] * ambient
                        blk_lit = blk_curve[lv & 0x0F]
                        light = sky_lit if sky_lit >= blk_lit else blk_lit
                        if hand_light and dist_sq < 64.0:
                            hd = abs(cx - bx) + abs(cy - by) + abs(cz - bz)
                            if hd <= 8.5:
                                hl = 1.0 - hd * 0.065
                                if hl > light:
                                    light = hl

                    lit = shade * light
                    fog_t = min(1.0, (dist_sq - fog_start_sq) / fog_span) if dist_sq > fog_start_sq else 0.0

                    sub_quads = None
                    if all_in_front and dist_sq < tex8_sq and face_p8 is not None and not blk_trans[bid]:
                        patches = face_p16[gkey] if dist_sq < tex16_sq else face_p8[gkey]
                        if patches:
                            if dist_sq < 3.2:
                                if fidx in (2, 5):
                                    sub_quads = _project_tex_patches_3d(cam_pts[3], cam_pts[2], cam_pts[1], cam_pts[0], patches, lit, sky_rgb, fog_t, half_w, half_h, focal)
                                elif fidx in (3, 4):
                                    sub_quads = _project_tex_patches_3d(cam_pts[1], cam_pts[2], cam_pts[3], cam_pts[0], patches, lit, sky_rgb, fog_t, half_w, half_h, focal)
                                else:
                                    sub_quads = _project_tex_patches_3d(cam_pts[0], cam_pts[1], cam_pts[2], cam_pts[3], patches, lit, sky_rgb, fog_t, half_w, half_h, focal)
                            else:
                                if fidx in (2, 5):
                                    sub_quads = _project_tex_patches_2d(pts2d[3], pts2d[2], pts2d[1], pts2d[0], patches, lit, sky_rgb, fog_t)
                                elif fidx in (3, 4):
                                    sub_quads = _project_tex_patches_2d(pts2d[1], pts2d[2], pts2d[3], pts2d[0], patches, lit, sky_rgb, fog_t)
                                else:
                                    sub_quads = _project_tex_patches_2d(pts2d[0], pts2d[1], pts2d[2], pts2d[3], patches, lit, sky_rgb, fog_t)

                    cr = base_rgb[0] * lit
                    cg = base_rgb[1] * lit
                    cb = base_rgb[2] * lit
                    if fog_t > 0.0:
                        cr += (sky_r - cr) * fog_t
                        cg += (sky_g - cg) * fog_t
                        cb += (sky_b - cb) * fog_t

                    is_target = (bx == tx_target and by == ty_target and bz == tz_target)
                    append_face((dist_sq, pts2d, (int(cr), int(cg), int(cb)), bid, fidx, is_target, sub_quads))

        # Project 3D mobs with authentic Minecraft features & pixel faces
        for m in world.mobs:
            st = MOB_STATS[m.kind]
            hw = st["w"] * 0.5
            creeper_flash = m.kind == "creeper" and m.fuse > 0 and int(m.fuse * 10) % 2 == 0
            body_c = (248, 248, 248) if creeper_flash else ((240, 80, 80) if m.hurt_timer > 0 else st["body"])
            head_c = (240, 80, 80) if m.hurt_timer > 0 else st["head"]
            leg_c = st["leg"]
            swing = math.sin(m.walk_phase) * 0.14
            syaw = math.sin(m.yaw)
            cyaw = math.cos(m.yaw)

            if m.kind in ("zombie", "creeper", "skeleton"):
                # Legs + Body + Head oriented to mob yaw
                draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                    m.x, m.y, m.z, syaw, cyaw, -hw * 0.85, 0.0, -0.14 + swing, -0.03, 0.55, 0.14 + swing,
                    leg_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                    m.x, m.y, m.z, syaw, cyaw, 0.03, 0.0, -0.14 - swing, hw * 0.85, 0.55, 0.14 - swing,
                    leg_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                    m.x, m.y, m.z, syaw, cyaw, -hw, 0.55, -hw * 0.55, hw, 1.25, hw * 0.55,
                    body_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                    m.x, m.y, m.z, syaw, cyaw, -hw * 0.85, 1.25, -hw * 0.85, hw * 0.85, st["h"], hw * 0.85,
                    head_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                # Facial pixels (Eyes & Mouth on front +Z face of mob)
                fz_face = hw * 0.86
                eye_c = (18, 18, 18) if m.kind != "skeleton" else (28, 28, 32)
                draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                    m.x, m.y, m.z, syaw, cyaw, -0.16, 1.44, fz_face - 0.02, -0.06, 1.54, fz_face + 0.02,
                    eye_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                    m.x, m.y, m.z, syaw, cyaw, 0.06, 1.44, fz_face - 0.02, 0.16, 1.54, fz_face + 0.02,
                    eye_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                if m.kind == "creeper":
                    draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                        m.x, m.y, m.z, syaw, cyaw, -0.09, 1.30, fz_face - 0.02, 0.09, 1.42, fz_face + 0.02,
                        (18, 18, 18), ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                elif m.kind == "zombie":
                    # Outstretched zombie arms
                    arm_c = head_c
                    draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                        m.x, m.y, m.z, syaw, cyaw, -hw - 0.16, 1.04, 0.0, -hw, 1.24, 0.48,
                        arm_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                    draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                        m.x, m.y, m.z, syaw, cyaw, hw, 1.04, 0.0, hw + 0.16, 1.24, 0.48,
                        arm_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
            elif m.kind == "spider":
                draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                    m.x, m.y, m.z, syaw, cyaw, -0.28, 0.18, -0.45, 0.28, 0.56, 0.20,
                    body_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                    m.x, m.y, m.z, syaw, cyaw, -0.22, 0.20, 0.20, 0.22, 0.54, 0.54,
                    head_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                # Glowing red eyes
                draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                    m.x, m.y, m.z, syaw, cyaw, -0.15, 0.36, 0.53, -0.05, 0.44, 0.56,
                    (235, 32, 32), ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span, emissive=True))
                draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                    m.x, m.y, m.z, syaw, cyaw, 0.05, 0.36, 0.53, 0.15, 0.44, 0.56,
                    (235, 32, 32), ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span, emissive=True))
                for lz_off in (-0.30, 0.0, 0.26):
                    draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                        m.x, m.y, m.z, syaw, cyaw, -0.62, 0.0, lz_off - 0.05, -0.26, 0.28, lz_off + 0.05,
                        leg_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                    draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                        m.x, m.y, m.z, syaw, cyaw, 0.26, 0.0, lz_off - 0.05, 0.62, 0.28, lz_off + 0.05,
                        leg_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
            else:
                # Farm animals (Pig, Cow, Sheep) with snout & face
                draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                    m.x, m.y, m.z, syaw, cyaw, -hw * 0.85, 0.32, -hw, hw * 0.85, st["h"] * 0.82, hw * 0.9,
                    body_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                    m.x, m.y, m.z, syaw, cyaw, -0.22, st["h"] * 0.46, hw * 0.72, 0.22, st["h"], hw * 1.35,
                    head_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                # Eyes & snout
                draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                    m.x, m.y, m.z, syaw, cyaw, -0.17, st["h"] * 0.74, hw * 1.34, -0.09, st["h"] * 0.84, hw * 1.37,
                    (20, 20, 20), ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                    m.x, m.y, m.z, syaw, cyaw, 0.09, st["h"] * 0.74, hw * 1.34, 0.17, st["h"] * 0.84, hw * 1.37,
                    (20, 20, 20), ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                if m.kind == "pig":
                    draw_faces.extend(_project_oriented_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                        m.x, m.y, m.z, syaw, cyaw, -0.11, st["h"] * 0.54, hw * 1.33, 0.11, st["h"] * 0.68, hw * 1.44,
                        (252, 134, 152), ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))
                for lx_off, lz_off in ((-0.18, -0.20), (0.18, -0.20), (-0.18, 0.22), (0.18, 0.22)):
                    draw_faces.extend(_project_box(cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                        m.x + lx_off - 0.08, m.y, m.z + lz_off - 0.08, m.x + lx_off + 0.08, m.y + 0.34, m.z + lz_off + 0.08,
                        leg_c, ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span))

        # Project flying 3D arrows
        for a in world.arrows:
            draw_faces.extend(_project_box(
                cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal,
                a.x - 0.07, a.y - 0.07, a.z - 0.07, a.x + 0.07, a.y + 0.07, a.z + 0.07,
                (235, 224, 180), ambient, sky_rgb, max_dist_sq, fog_start_sq, fog_span, emissive=True
            ))

        draw_faces.sort(key=_ITEM0, reverse=True)

        # Project blocky Minecraft clouds in Overworld (tinted darker during storms)
        cloud_2d = []
        if world.dimension == "overworld":
            storm_dim = 1.0 - world.weather_intensity * (0.48 if world.weather == "thunder" else 0.30)
            c_br = (0.45 + 0.55 * ambient) * storm_dim
            cloud_col = (min(255, int(238 * c_br)),
                         min(255, int(242 * c_br)),
                         min(255, int(250 * c_br)))
            for cl_x, cl_z, cw, cd in self.clouds:
                wx0 = cx + ((cl_x + cloud_shift - cx) % 64.0) - 32.0
                wz0 = cz + ((cl_z - cz) % 64.0) - 32.0
                dx_m = (wx0 + cw * 0.5) - cx
                dz_m = (wz0 + cd * 0.5) - cz
                if dx_m * fx + dz_m * fz < -4.0:
                    continue
                pts = []
                ok = True
                for cx_o, cz_o in ((wx0, wz0), (wx0 + cw, wz0), (wx0 + cw, wz0 + cd), (wx0, wz0 + cd)):
                    ddx, ddy, ddz = cx_o - cx, 34.5 - cy, cz_o - cz
                    pz = ddx * fx + ddy * fy + ddz * fz
                    if pz < 1.0:
                        ok = False
                        break
                    iz = focal / pz
                    pts.append((half_w + (ddx * rx + ddz * rz) * iz, half_h - (ddx * ux + ddy * uy + ddz * uz) * iz))
                if ok:
                    cloud_2d.append((pts, cloud_col))

        part_2d = []
        for p in world.particles:
            dx, dy, dz = p[0] - cx, p[1] - cy, p[2] - cz
            pz = dx * fx + dy * fy + dz * fz
            if pz >= NEAR_PLANE:
                px = dx * rx + dz * rz
                py = dx * ux + dy * uy + dz * uz
                inv_z = focal / pz
                psx = half_w + px * inv_z
                psy = half_h - py * inv_z
                sz_px = max(2, int(0.11 * inv_z))
                if -20 <= psx <= width + 20 and -20 <= psy <= height + 20:
                    part_2d.append((pz * pz, psx, psy, sz_px, p[6]))

        for sp in world.rain_splashes:
            dx, dy, dz = sp[0] - cx, sp[1] - cy, sp[2] - cz
            pz = dx * fx + dy * fy + dz * fz
            if pz >= NEAR_PLANE:
                px = dx * rx + dz * rz
                py = dx * ux + dy * uy + dz * uz
                inv_z = focal / pz
                psx = half_w + px * inv_z
                psy = half_h - py * inv_z
                sz_px = max(2, int(0.14 * inv_z * (1.0 - sp[3] * 1.8)))
                if -20 <= psx <= width + 20 and -20 <= psy <= height + 20:
                    part_2d.append((pz * pz, psx, psy, sz_px, (186, 220, 255)))

        return draw_faces, part_2d, (cx, cy, cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal), cloud_2d
