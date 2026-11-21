"""Native Pygame asset loader: C-accelerated PNG loading + full-scale 16x16 & 8x8 greedy UV patch tables."""

import os

from pycraft.blocks import BLOCKS, item_texture_name
from pycraft.constants import get_assets_dir


def _dominant_base_rgb(grid, n):
    """Find the most common 16-step quantized RGB bucket average among opaque pixels."""
    buckets = {}
    for row in grid:
        for r, g, b, a in row:
            if a < 24:
                continue
            key = (r >> 4, g >> 4, b >> 4)
            entry = buckets.get(key)
            if entry is None:
                buckets[key] = [1, r, g, b]
            else:
                entry[0] += 1
                entry[1] += r
                entry[2] += g
                entry[3] += b
    if not buckets:
        return (128, 128, 128)
    best = max(buckets.values(), key=lambda v: v[0])
    cnt = best[0]
    return (best[1] // cnt, best[2] // cnt, best[3] // cnt)


def _greedy_merge_grid(grid, n, base_rgb, tol):
    """Merge matching adjacent texels into minimal normalized UV rectangles (u0, v0, u1, v1, rgb)."""
    br, bg, bb = base_rgb
    visited = [[False] * n for _ in range(n)]
    patches = []
    inv_n = 1.0 / n

    for y in range(n):
        row = grid[y]
        vrow = visited[y]
        for x in range(n):
            if vrow[x]:
                continue
            r, g, b, a = row[x]
            if a < 24 or (abs(r - br) + abs(g - bg) + abs(b - bb) <= tol):
                vrow[x] = True
                continue

            # Expand horizontally as far as pixels stay within tolerance of seed pixel
            w = 1
            sr, sg, sb = r, g, b
            while x + w < n and not vrow[x + w]:
                nr, ng, nb, na = row[x + w]
                if na < 24 or (abs(nr - r) + abs(ng - g) + abs(nb - b) > tol):
                    break
                if abs(nr - br) + abs(ng - bg) + abs(nb - bb) <= tol:
                    break
                sr += nr
                sg += ng
                sb += nb
                w += 1

            # Expand vertically if full horizontal run matches
            h = 1
            while y + h < n:
                y2_row = grid[y + h]
                y2_vis = visited[y + h]
                ok = True
                rsum = gsum = bsum = 0
                for dx in range(w):
                    if y2_vis[x + dx]:
                        ok = False
                        break
                    nr, ng, nb, na = y2_row[x + dx]
                    if na < 24 or (abs(nr - r) + abs(ng - g) + abs(nb - b) > tol):
                        ok = False
                        break
                    if abs(nr - br) + abs(ng - bg) + abs(nb - bb) <= tol:
                        ok = False
                        break
                    rsum += nr
                    gsum += ng
                    bsum += nb
                if not ok:
                    break
                sr += rsum
                sg += gsum
                sb += bsum
                h += 1

            for dy in range(h):
                vy = visited[y + dy]
                for dx in range(w):
                    vy[x + dx] = True

            area = w * h
            patches.append((
                x * inv_n,
                y * inv_n,
                (x + w) * inv_n,
                (y + h) * inv_n,
                (sr // area, sg // area, sb // area),
            ))

    return tuple(patches)


def build_patches_from_rgba_16(pixels_16):
    """Build (base_rgb, patches_16x16, patches_8x8) from a 16x16 RGBA pixel grid."""
    base_rgb = _dominant_base_rgb(pixels_16, 16)
    patches_16 = _greedy_merge_grid(pixels_16, 16, base_rgb, tol=18)

    grid8 = []
    for gy in range(0, 16, 2):
        r0, r1 = pixels_16[gy], pixels_16[gy + 1]
        row8 = []
        for gx in range(0, 16, 2):
            c00, c01 = r0[gx], r0[gx + 1]
            c10, c11 = r1[gx], r1[gx + 1]
            row8.append((
                (c00[0] + c01[0] + c10[0] + c11[0]) >> 2,
                (c00[1] + c01[1] + c10[1] + c11[1]) >> 2,
                (c00[2] + c01[2] + c10[2] + c11[2]) >> 2,
                (c00[3] + c01[3] + c10[3] + c11[3]) >> 2,
            ))
        grid8.append(row8)
    patches_8 = _greedy_merge_grid(grid8, 8, base_rgb, tol=22)
    return base_rgb, patches_16, patches_8


class AssetManager:
    __slots__ = (
        "tex_dir", "pg_raw", "pg_icons", "title_bg",
        "face_base_rgb", "face_patches_16", "face_patches_8",
    )

    def __init__(self):
        self.tex_dir = os.path.join(get_assets_dir(), "textures")
        self.pg_raw = {}              # filename -> native pygame.Surface
        self.pg_icons = {}            # (iid, size) -> scaled pygame.Surface
        self.title_bg = None          # pygame.Surface or None
        self.face_base_rgb = [None] * 512
        self.face_patches_16 = [None] * 512
        self.face_patches_8 = [None] * 512

    def _compile_surface_patches(self, pygame, surf):
        w, h = surf.get_size()
        s16 = surf if (w == 16 and h == 16) else pygame.transform.scale(surf, (16, 16))
        pixels_16 = []
        for py in range(16):
            row = []
            for px in range(16):
                c = s16.get_at((px, py))
                row.append((int(c[0]), int(c[1]), int(c[2]), int(c[3]) if len(c) > 3 else 255))
            pixels_16.append(row)
        return build_patches_from_rgba_16(pixels_16)

    def init_pygame(self, pygame):
        if not os.path.isdir(self.tex_dir):
            return
        needed_names = set()
        for bid in BLOCKS:
            for fidx in range(6):
                tname = item_texture_name(bid, fidx)
                if tname:
                    needed_names.add(tname)

        compiled = {}
        for fname in os.listdir(self.tex_dir):
            fpath = os.path.join(self.tex_dir, fname)
            if fname.endswith(".png"):
                try:
                    surf = pygame.image.load(fpath).convert_alpha()
                    self.pg_raw[fname] = surf
                    if fname in needed_names:
                        compiled[fname] = self._compile_surface_patches(pygame, surf)
                except Exception:
                    pass
            elif fname == "title_bg.jpg":
                try:
                    self.title_bg = pygame.image.load(fpath).convert()
                except Exception:
                    pass

        for bid in BLOCKS:
            for fidx in range(6):
                tname = item_texture_name(bid, fidx)
                if tname and tname in compiled:
                    key = (bid << 3) | fidx
                    base_rgb, p16, p8 = compiled[tname]
                    self.face_base_rgb[key] = base_rgb
                    self.face_patches_16[key] = p16
                    self.face_patches_8[key] = p8

    def get_icon(self, pygame, iid, size):
        key = (iid, size)
        if key in self.pg_icons:
            return self.pg_icons[key]
        tname = item_texture_name(iid, face_idx=2)
        if tname and tname in self.pg_raw:
            scaled = pygame.transform.scale(self.pg_raw[tname], (size, size))
            self.pg_icons[key] = scaled
            return scaled
        return None
