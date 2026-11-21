"""Pygame primary runtime: High-FPS Minecraft clone with clouds, 3D mobs, Nether, Bow/Arrows, Buckets, Armor, HUD."""

import math
import os
import random
import time

from pycraft.assets import AssetManager
from pycraft.audio import SoundBank
from pycraft.blocks import BLOCKS, ITEMS, SMELT_RECIPES, is_placeable, item_color, item_name
from pycraft.constants import (
    AIR, ARMOR_DIAMOND, ARMOR_GOLD, ARMOR_IRON, BED, BEDROCK, CHEST, CRAFT_TABLE,
    DOOR_CLOSED, DOOR_OPEN, FURNACE, GLASS, GLOWSTONE, GRAVEL, ICE, ITEM_ARROW, ITEM_BOW,
    ITEM_BUCKET_EMPTY, ITEM_BUCKET_LAVA, ITEM_BUCKET_WATER, ITEM_COAL,
    ITEM_FLINT, ITEM_FLINT_STEEL, LAVA, PORTAL, TNT, TORCH, WATER, WOOD,
    get_save_path, is_android,
)
from pycraft.inventory import InventorySlot
from pycraft.inventory_ui import InventoryUIHandler
from pycraft.physics import raycast_block, raycast_mob
from pycraft.renderer import VoxelRenderer, compute_sky_and_light
from pycraft.storage import create_new_game, load_game, save_game


def _make_pixel_icons(pygame, sz):
    """Pre-bake classic Minecraft pixel-art HUD icons (heart, hunger, armor, bubble)."""
    def mk_surf(pattern, palette):
        surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
        rows = len(pattern)
        cols = len(pattern[0])
        pw = max(1, sz // cols)
        ph = max(1, sz // rows)
        for ry, line in enumerate(pattern):
            for rx, ch in enumerate(line):
                col = palette.get(ch)
                if col:
                    pygame.draw.rect(surf, col, (rx * pw, ry * ph, pw, ph))
        return surf

    heart_pat = (
        ".KK.KK.",
        "KRRKRRK",
        "KRWRRRK",
        "KRRRRRK",
        ".KRRRK.",
        "..KRK..",
        "...K...",
    )
    heart_full = mk_surf(heart_pat, {"K": (20, 12, 16), "R": (228, 34, 40), "W": (255, 196, 196)})
    heart_empty = mk_surf(heart_pat, {"K": (20, 12, 16), "R": (64, 42, 46), "W": (78, 52, 56)})

    meat_pat = (
        "...KKK.",
        "..KMMMK",
        ".KMMMMK",
        "KBBMMK.",
        "KBBBK..",
        ".KKK...",
    )
    meat_full = mk_surf(meat_pat, {"K": (28, 16, 10), "M": (204, 114, 52), "B": (244, 232, 206)})
    meat_empty = mk_surf(meat_pat, {"K": (28, 16, 10), "M": (70, 56, 46), "B": (88, 76, 66)})

    armor_pat = (
        "KK...KK",
        "KAA.AAK",
        "KAAAAAK",
        "KAAAAAK",
        ".KAAAK.",
        "..KKK..",
    )
    armor_full = mk_surf(armor_pat, {"K": (24, 28, 36), "A": (198, 212, 228)})
    armor_empty = mk_surf(armor_pat, {"K": (24, 28, 36), "A": (68, 74, 86)})

    bub_pat = (
        ".BBBB.",
        "BWBBBC",
        "BBBBCC",
        "BBCCCC",
        ".CCCC.",
    )
    bubble = mk_surf(bub_pat, {"B": (140, 215, 255), "W": (245, 252, 255), "C": (60, 148, 225)})
    return {
        "heart_full": heart_full, "heart_empty": heart_empty,
        "meat_full": meat_full, "meat_empty": meat_empty,
        "armor_full": armor_full, "armor_empty": armor_empty,
        "bubble": bubble,
    }


def _raycast_liquid(world, ox, oy, oz, dx, dy, dz, max_dist=5.0):
    """Find first Water or Lava block along look ray for Bucket scooping."""
    step = 0.25
    t = 0.5
    while t <= max_dist:
        bx = math.floor(ox + dx * t)
        by = math.floor(oy + dy * t)
        bz = math.floor(oz + dz * t)
        bid = world.get_block(bx, by, bz)
        if bid in (WATER, LAVA):
            return (bx, by, bz), bid
        if bid != AIR and BLOCKS[bid]["solid"]:
            return None, AIR
        t += step
    return None, AIR


def run_pygame(start_vertical=False):
    import pygame

    SoundBank.pre_init_pygame(pygame)
    pygame.init()
    sound_bank = SoundBank()
    sound_bank.init_pygame(pygame)

    android_env = is_android()
    orientation_mode = "vertical" if start_vertical else "horizontal"
    flags = pygame.FULLSCREEN | pygame.DOUBLEBUF if android_env else pygame.RESIZABLE | pygame.DOUBLEBUF
    if android_env:
        screen = pygame.display.set_mode((0, 0), flags)
    else:
        init_size = (600, 960) if orientation_mode == "vertical" else (1280, 720)
        screen = pygame.display.set_mode(init_size, flags)
    pygame.display.set_caption("PyCraft - Full-Scale Minecraft for Pydroid 3")
    clock = pygame.time.Clock()

    assets = AssetManager()
    assets.init_pygame(pygame)

    has_save = os.path.exists(get_save_path())
    world, player, time_of_day = create_new_game(creative=False)
    renderer = VoxelRenderer(assets=assets, render_dist=15, perf_mode="balanced")
    inv_ui = InventoryUIHandler()

    state = "TITLE"
    toast_msg = ""
    toast_timer = 0.0
    toast_cache_key = None
    toast_cache_surf = None
    using_touch = False
    active_fingers = {}
    mouse_looking = False
    mining_progress = 0.0
    mining_target = None
    step_timer = 0.0
    cloud_shift = 0.0
    portal_cd = 0.0
    bright_boost = True
    last_auto_save = 0.0
    selected_smelt = 0
    ui = {}

    def compute_layout(w, h):
        is_vert = (orientation_mode == "vertical")
        s = min(w, h)
        margin = max(12, int(s * 0.024))

        if is_vert:
            slot_sz = max(42, min(86, int((w - margin * 2 - 28) / 11.8)))
            cyc_w = max(32, int(slot_sz * 0.72))
            total_bar_w = cyc_w * 2 + slot_sz * 10 + 30
            bar_x = max(6, (w - total_bar_w) // 2)
            bar_y = h - slot_sz - margin

            pad_r = max(66, int(s * 0.175))
            pad_cx = pad_r + margin + 6
            pad_cy = bar_y - pad_r - max(26, int(h * 0.032))

            btn_sz = max(66, int(s * 0.155))
            ui["btn_prev"] = pygame.Rect(bar_x, bar_y, cyc_w, slot_sz)
            slots_x0 = bar_x + cyc_w + 4
            ui["slots"] = [pygame.Rect(slots_x0 + i * (slot_sz + 2), bar_y, slot_sz, slot_sz) for i in range(9)]
            ui["btn_next"] = pygame.Rect(slots_x0 + 9 * (slot_sz + 2) + 2, bar_y, cyc_w, slot_sz)
            ui["btn_inv"] = pygame.Rect(ui["btn_next"].right + 4, bar_y, slot_sz, slot_sz)

            top_h = max(44, int(s * 0.082))
            gap = max(6, int(w * 0.012))
            btn_w = max(58, (w - margin * 2 - gap * 4) // 5)
            ui["btn_pause"] = pygame.Rect(margin, margin, btn_w, top_h)
            ui["btn_fly"] = pygame.Rect(margin + (btn_w + gap), margin, btn_w, top_h)
            ui["btn_time"] = pygame.Rect(margin + (btn_w + gap) * 2, margin, btn_w, top_h)
            ui["btn_layout"] = pygame.Rect(margin + (btn_w + gap) * 3, margin, btn_w, top_h)
            ui["btn_save"] = pygame.Rect(margin + (btn_w + gap) * 4, margin, btn_w, top_h)

            act_gap = max(12, int(s * 0.025))
            ui["jump"] = pygame.Rect(w - btn_sz - margin, pad_cy - btn_sz // 2, btn_sz, btn_sz)
            ui["mine"] = pygame.Rect(w - btn_sz * 2 - margin - act_gap, pad_cy - btn_sz // 2 - int(btn_sz * 0.62), btn_sz, btn_sz)
            ui["place"] = pygame.Rect(w - btn_sz * 2 - margin - act_gap, pad_cy - btn_sz // 2 + int(btn_sz * 0.62), btn_sz, btn_sz)
            ui["fly_down"] = pygame.Rect(w - btn_sz - margin, pad_cy + btn_sz // 2 + act_gap, btn_sz, max(44, int(btn_sz * 0.72)))
        else:
            pad_r = max(72, int(s * 0.19))
            pad_cx = pad_r + margin + 10
            pad_cy = h - pad_r - max(42, int(s * 0.14))
            btn_sz = max(72, int(s * 0.16))

            slot_sz = max(48, min(92, int((w - margin * 2 - 44) / 12.2)))
            cyc_w = max(40, int(slot_sz * 0.72))
            bar_w = cyc_w * 2 + slot_sz * 10 + 30
            bar_x = (w - bar_w) // 2
            bar_y = h - slot_sz - margin

            ui["btn_prev"] = pygame.Rect(bar_x, bar_y, cyc_w, slot_sz)
            slots_x0 = bar_x + cyc_w + 4
            ui["slots"] = [pygame.Rect(slots_x0 + i * (slot_sz + 2), bar_y, slot_sz, slot_sz) for i in range(9)]
            ui["btn_next"] = pygame.Rect(slots_x0 + 9 * (slot_sz + 2) + 2, bar_y, cyc_w, slot_sz)
            ui["btn_inv"] = pygame.Rect(ui["btn_next"].right + 4, bar_y, slot_sz, slot_sz)

            top_h = max(44, int(s * 0.085))
            gap = max(8, int(s * 0.014))
            bw_unit = max(78, int(top_h * 1.95))
            ui["btn_pause"] = pygame.Rect(margin, margin, bw_unit, top_h)
            ui["btn_fly"] = pygame.Rect(ui["btn_pause"].right + gap, margin, bw_unit, top_h)
            ui["btn_time"] = pygame.Rect(ui["btn_fly"].right + gap, margin, bw_unit, top_h)
            ui["btn_layout"] = pygame.Rect(ui["btn_time"].right + gap, margin, bw_unit, top_h)
            ui["btn_save"] = pygame.Rect(ui["btn_layout"].right + gap, margin, bw_unit, top_h)

            act_gap = max(12, int(s * 0.024))
            ui["jump"] = pygame.Rect(w - btn_sz - margin, pad_cy - btn_sz // 2, btn_sz, btn_sz)
            ui["mine"] = pygame.Rect(w - btn_sz * 2 - margin - act_gap, pad_cy - btn_sz // 2 - int(btn_sz * 0.62), btn_sz, btn_sz)
            ui["place"] = pygame.Rect(w - btn_sz * 2 - margin - act_gap, pad_cy - btn_sz // 2 + int(btn_sz * 0.62), btn_sz, btn_sz)
            ui["fly_down"] = pygame.Rect(w - btn_sz - margin, pad_cy + btn_sz // 2 + act_gap, btn_sz, max(46, int(btn_sz * 0.72)))

        ui["w"] = w
        ui["h"] = h
        ui["is_vert"] = is_vert
        ui["pad"] = (pad_cx, pad_cy, pad_r)
        ui["fonts"] = {
            "xs": pygame.font.SysFont("sans", max(12, int(s * 0.025)), bold=True),
            "sm": pygame.font.SysFont("sans", max(15, int(s * 0.032)), bold=True),
            "md": pygame.font.SysFont("sans", max(19, int(s * 0.042)), bold=True),
            "lg": pygame.font.SysFont("sans", max(28, int(s * 0.062)), bold=True),
        }

        top_btn_surfs = {}
        for key in ("btn_pause", "btn_fly", "btn_time", "btn_layout", "btn_save"):
            r = ui[key]
            dim = (r.w, r.h)
            if dim not in top_btn_surfs:
                tb = pygame.Surface(dim, pygame.SRCALPHA)
                tb.fill((20, 24, 34, 175))
                top_btn_surfs[dim] = tb

        pad_surf = pygame.Surface((pad_r * 2 + 4, pad_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(pad_surf, (20, 24, 32, 118), (pad_r + 2, pad_r + 2), pad_r)
        pygame.draw.circle(pad_surf, (220, 230, 245, 170), (pad_r + 2, pad_r + 2), pad_r, 3)

        action_surfs = {}
        for key, accent in (
            ("jump", (68, 168, 92)),
            ("mine", (204, 78, 66)),
            ("place", (64, 134, 214)),
            ("fly_down", (88, 118, 148)),
        ):
            r = ui[key]
            bs = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            pygame.draw.rect(bs, (*accent, 172), (0, 0, r.w, r.h), border_radius=16)
            pygame.draw.rect(bs, (245, 248, 255, 235), (0, 0, r.w, r.h), 2, border_radius=16)
            action_surfs[key] = bs

        cyc_surf = pygame.Surface((ui["btn_prev"].w, ui["btn_prev"].h), pygame.SRCALPHA)
        cyc_surf.fill((48, 52, 62, 215))

        slot_surf = pygame.Surface((ui["slots"][0].w, ui["slots"][0].h), pygame.SRCALPHA)
        slot_surf.fill((40, 42, 48, 215))

        inv_surf = pygame.Surface((ui["btn_inv"].w, ui["btn_inv"].h), pygame.SRCALPHA)
        inv_surf.fill((48, 52, 62, 215))

        ov_dark = pygame.Surface((w, h), pygame.SRCALPHA)
        ov_dark.fill((10, 14, 22, 202))

        ov_title = pygame.Surface((w, h), pygame.SRCALPHA)
        ov_title.fill((8, 12, 20, 125))

        ov_water = pygame.Surface((w, h), pygame.SRCALPHA)
        ov_water.fill((28, 86, 198, 82))

        ov_hurt = pygame.Surface((w, h), pygame.SRCALPHA)
        ov_hurt.fill((212, 24, 24, 96))

        ov_storm = pygame.Surface((w, h))
        ov_storm.fill((20, 30, 48))

        ov_flash = pygame.Surface((w, h))
        ov_flash.fill((218, 234, 255))

        alpha_scratch = pygame.Surface((w, h), pygame.SRCALPHA)
        title_bg_scaled = pygame.transform.smoothscale(assets.title_bg, (w, h)) if assets.title_bg is not None else None

        pin_tile = max(34, min(42, int(s * 0.068)))
        pin_gap = 5
        pin_pad = 8
        pin_w = pin_pad * 2 + pin_tile * 5 + pin_gap * 4
        pin_hdr_h = 28
        pin_h = pin_pad * 2 + pin_hdr_h + 4 + pin_tile
        pin_x = margin
        pin_y = ui["btn_pause"].bottom + (34 if is_vert else 10)
        ui["pin_metrics"] = (pin_x, pin_y, pin_w, pin_h, pin_tile, pin_gap, pin_pad, pin_hdr_h)

        pin_bg = pygame.Surface((pin_w, pin_h), pygame.SRCALPHA)
        pygame.draw.rect(pin_bg, (16, 22, 34, 178), (0, 0, pin_w, pin_h), border_radius=10)
        pygame.draw.rect(pin_bg, (132, 152, 182, 200), (0, 0, pin_w, pin_h), 1, border_radius=10)

        pin_mini_w = 138
        pin_mini_h = 34
        pin_mini_bg = pygame.Surface((pin_mini_w, pin_mini_h), pygame.SRCALPHA)
        pygame.draw.rect(pin_mini_bg, (18, 24, 36, 178), (0, 0, pin_mini_w, pin_mini_h), border_radius=8)
        pygame.draw.rect(pin_mini_bg, (132, 152, 182, 200), (0, 0, pin_mini_w, pin_mini_h), 1, border_radius=8)

        icon_px = max(14, min(26, int(s * 0.032)))
        ui["cache"] = {
            "top_btn_surfs": top_btn_surfs,
            "pad_surf": pad_surf,
            "action_surfs": action_surfs,
            "cyc_surf": cyc_surf,
            "slot_surf": slot_surf,
            "inv_surf": inv_surf,
            "ov_dark": ov_dark,
            "ov_title": ov_title,
            "ov_water": ov_water,
            "ov_hurt": ov_hurt,
            "ov_storm": ov_storm,
            "ov_flash": ov_flash,
            "pin_bg": pin_bg,
            "pin_mini_bg": pin_mini_bg,
            "alpha_scratch": alpha_scratch,
            "title_bg_scaled": title_bg_scaled,
            "pix_icons": _make_pixel_icons(pygame, icon_px),
            "pix_step": icon_px + 2,
            "lbl_sm": {},
            "lbl_md": {},
            "cnt_xs": {},
            "info_key": None,
            "info_surf": None,
        }

    W, H = screen.get_size()
    compute_layout(W, H)

    def show_toast(msg, dur=2.2):
        nonlocal toast_msg, toast_timer
        toast_msg = msg
        toast_timer = dur

    def auto_save(force=False):
        nonlocal has_save, last_auto_save
        if state == "TITLE":
            return
        now_t = time.monotonic()
        if force or (now_t - last_auto_save >= 2.0):
            save_game(world, player, time_of_day)
            has_save = True
            last_auto_save = now_t

    def enter_nether_or_overworld():
        nonlocal portal_cd
        if portal_cd > 0:
            return
        portal_cd = 2.5
        new_dim = world.switch_dimension()
        world.ensure_chunks_around(2.5, 3.0, 20, max_gen_per_frame=64)
        player.x, player.z = 2.5, 1.5
        player.y = 8.2 if new_dim == "nether" else world.get_surface_y(2, 1) + 0.5
        player.vy = 0.0
        sound_bank.play("ignite")
        show_toast("Entered the NETHER!" if new_dim == "nether" else "Returned to Overworld!", 2.5)

    def set_orientation_mode(mode):
        nonlocal screen, orientation_mode
        if mode not in ("horizontal", "vertical"):
            mode = "vertical" if orientation_mode == "horizontal" else "horizontal"
        orientation_mode = mode
        if not android_env:
            new_size = (600, 960) if orientation_mode == "vertical" else (1280, 720)
            screen = pygame.display.set_mode(new_size, flags)
        nw, nh = screen.get_size()
        compute_layout(nw, nh)
        show_toast("Horizontal Mode" if orientation_mode == "horizontal" else "Vertical Mode", 1.6)

    def cycle_perf_mode():
        modes = ("fast", "balanced", "fancy")
        idx = (modes.index(renderer.perf_mode) + 1) % len(modes) if renderer.perf_mode in modes else 1
        renderer.perf_mode = modes[idx]
        show_toast(f"Graphics: {renderer.perf_mode.title()}", 1.5)

    def draw_item_icon(iid, rect):
        if iid == AIR:
            return
        icon = assets.get_icon(pygame, iid, rect.w)
        if icon is not None:
            screen.blit(icon, rect.topleft)
        else:
            tc, sc = item_color(iid)
            pygame.draw.rect(screen, sc, rect)
            pygame.draw.rect(screen, tc, (rect.x, rect.y, rect.w, max(4, rect.h // 3)))

    def do_place_or_use(target, prev_air):
        nonlocal state, time_of_day
        player.swing_timer = 0.18
        sel = player.selected_item
        look = player.look_dir()

        # Food eating
        if sel in ITEMS and "food" in ITEMS[sel]:
            if player.hunger < 20 or player.creative:
                if not player.inv.consume_selected(1):
                    return
                player.hunger = min(20, player.hunger + ITEMS[sel]["food"])
                player.health = min(player.max_health, player.health + 3)
                sound_bank.play("place")
                show_toast(f"Ate {item_name(sel)} (+Food)", 1.4)
            else:
                show_toast("Already full!", 1.1)
            return

        # Equip Armor
        if sel in (ARMOR_IRON, ARMOR_GOLD, ARMOR_DIAMOND):
            player.armor = ITEMS[sel]["armor"]
            if not player.creative:
                player.inv.consume_selected(1)
            sound_bank.play("place")
            show_toast(f"Equipped {item_name(sel)} (Armor {player.armor})!", 1.8)
            return

        # Flint & Steel ignites TNT
        if sel == ITEM_FLINT_STEEL:
            if target is not None and world.get_block(*target) == TNT:
                world.trigger_tnt(*target)
                sound_bank.play("ignite")
                show_toast("TNT Ignited!", 1.2)
            else:
                sound_bank.play("ignite", 0.5)
                show_toast("Tap TNT with Flint & Steel to ignite!", 1.3)
            return

        # Shoot Bow & Arrow
        if sel == ITEM_BOW:
            if player.creative or player.inv.remove_item(ITEM_ARROW, 1):
                world.shoot_arrow(player.x, player.eye_y, player.z, *look)
                sound_bank.play("hit", 0.7)
            else:
                show_toast("Out of Arrows!", 1.2)
            return

        # Buckets (scoop Water/Lava or pour Water/Lava)
        if sel == ITEM_BUCKET_EMPTY:
            liq_pos, liq_bid = _raycast_liquid(world, player.x, player.eye_y, player.z, *look)
            if liq_pos is not None:
                world.set_block(*liq_pos, AIR)
                new_bkt = ITEM_BUCKET_LAVA if liq_bid == LAVA else ITEM_BUCKET_WATER
                if not player.creative:
                    player.inv.hotbar[player.inv.selected_slot] = InventorySlot(new_bkt, 1)
                else:
                    player.inv.equip_to_hotbar(new_bkt)
                sound_bank.play("place")
                show_toast("Filled Bucket!", 1.2)
            return
        if sel in (ITEM_BUCKET_WATER, ITEM_BUCKET_LAVA) and prev_air is not None:
            liq = WATER if sel == ITEM_BUCKET_WATER else LAVA
            world.set_block(*prev_air, liq)
            if not player.creative:
                player.inv.hotbar[player.inv.selected_slot] = InventorySlot(ITEM_BUCKET_EMPTY, 1)
            sound_bank.play("place")
            return

        # Interactive blocks (Craft Table, Furnace, Chest, Door, Bed, Portal)
        if target is not None:
            tbid = world.get_block(*target)
            if tbid == CRAFT_TABLE:
                inv_ui.craft_station = "table"
                inv_ui.active_tab = "craft"
                inv_ui.reset_selection()
                state = "INVENTORY"
                return
            if tbid == FURNACE:
                state = "FURNACE"
                return
            if tbid == CHEST:
                sound_bank.play("chest")
                state = "CHEST"
                return
            if tbid in (DOOR_CLOSED, DOOR_OPEN):
                world.set_block(*target, DOOR_OPEN if tbid == DOOR_CLOSED else DOOR_CLOSED)
                sound_bank.play("break_wood", 0.7)
                return
            if tbid == BED:
                player.spawn_x, player.spawn_y, player.spawn_z = target[0] + 0.5, target[1] + 0.8, target[2] + 0.5
                _, _, _, is_day_now, _ = compute_sky_and_light(time_of_day, world.dimension)
                if not is_day_now and world.dimension == "overworld":
                    time_of_day = 0.08
                    player.health = player.max_health
                    show_toast("Slept till Dawn • Spawn Set!", 2.0)
                else:
                    show_toast("Respawn Point Set!", 1.6)
                sound_bank.play("place")
                return
            if tbid == PORTAL:
                enter_nether_or_overworld()
                return

        if prev_air is None or not is_placeable(sel):
            if sel == AIR:
                show_toast("Empty slot — tap [...] to switch blocks", 1.5)
            return
        bx, by, bz = prev_air
        if BLOCKS[sel]["solid"] and player.overlaps_block(bx, by, bz):
            return
        if not player.inv.consume_selected(1):
            show_toast("Out of " + item_name(sel) + "!")
            return
        world.set_block(bx, by, bz, sel)
        sound_bank.play("place")

    def do_attack_or_break():
        player.swing_timer = 0.20
        look = player.look_dir()
        mob, mdist = raycast_mob(world, player.x, player.eye_y, player.z, *look)
        _, _, bdist = raycast_block(world, player.x, player.eye_y, player.z, *look)
        if mob is not None and mdist <= bdist:
            sel = player.selected_item
            dmg = ITEMS.get(sel, {}).get("damage", 2)
            mob.hp -= dmg
            mob.hurt_timer = 0.25
            mob.x += look[0] * 0.45
            mob.z += look[2] * 0.45
            sound_bank.play("hit")
            if mob.hp <= 0:
                show_toast(f"Defeated {mob.kind.title()}! (+5 XP)", 1.3)
            return True
        return False

    def do_break_block(target):
        if target is None:
            return
        bx, by, bz = target
        bid = world.get_block(bx, by, bz)
        if bid == AIR or bid == BEDROCK:
            return
        if bid == TNT:
            world.trigger_tnt(bx, by, bz)
            sound_bank.play("ignite")
            show_toast("TNT Ignited!", 1.2)
            return
        snd_key = BLOCKS[bid].get("sound", "break")
        world.spawn_break_particles(bx, by, bz, bid)
        world.set_block(bx, by, bz, AIR)
        sound_bank.play(snd_key)
        drop = ITEM_FLINT if (bid == GRAVEL and random.random() < 0.25) else BLOCKS[bid].get("drop", bid)
        if not player.creative:
            if drop != AIR:
                player.add_item(drop, 1)
            player.xp += BLOCKS[bid].get("xp", 0)
        elif drop != AIR:
            player.inv.record_collected(drop, 1)

    def handle_ui_tap(px, py):
        nonlocal state, time_of_day, world, player, has_save, bright_boost
        if state == "TITLE":
            for label, rect in ui.get("title_btns", []):
                if rect.collidepoint(px, py):
                    if label == "Play Survival":
                        world, player, time_of_day = create_new_game(creative=False)
                        inv_ui.active_tab = player.inv.ui_tab
                        state = "PLAYING"
                        sound_bank.play("place", 0.6)
                        show_toast("Survival Mode • Nether, Crafting & Mobs!", 2.5)
                    elif label == "Play Creative":
                        world, player, time_of_day = create_new_game(creative=True)
                        inv_ui.active_tab = player.inv.ui_tab
                        state = "PLAYING"
                        sound_bank.play("place", 0.6)
                        show_toast("Creative Mode • Infinite Blocks & Fly!", 2.5)
                    elif label == "Continue Saved World":
                        loaded = load_game()
                        if loaded:
                            world, player, time_of_day = loaded
                            inv_ui.active_tab = player.inv.ui_tab
                            state = "PLAYING"
                            sound_bank.play("place", 0.6)
                            show_toast(f"Loaded World ({world.dimension.title()})!", 2.0)
                    elif label.startswith("Layout:"):
                        set_orientation_mode("horizontal" if orientation_mode == "vertical" else "vertical")
                        sound_bank.play("place", 0.5)
                    return "ui"
            return "ui"

        elif state == "PLAYING":
            if ui["btn_pause"].collidepoint(px, py):
                state = "PAUSED"
                return "pause"
            if ui["btn_fly"].collidepoint(px, py):
                if player.creative:
                    player.flying = not player.flying
                    show_toast("Fly: " + ("ON" if player.flying else "OFF"))
                else:
                    show_toast("Fly only in Creative mode")
                return "fly"
            if ui["btn_time"].collidepoint(px, py):
                time_of_day = (time_of_day + 0.25) % 1.0
                show_toast("Time advanced")
                return "time"
            if ui["btn_layout"].collidepoint(px, py):
                set_orientation_mode("horizontal" if orientation_mode == "vertical" else "vertical")
                return "layout"
            if ui["btn_save"].collidepoint(px, py):
                auto_save(force=True)
                sound_bank.play("place", 0.5)
                show_toast("World Saved!")
                return "save"
            if ui["btn_inv"].collidepoint(px, py):
                inv_ui.craft_station = "hand"
                inv_ui.reset_selection()
                state = "INVENTORY"
                return "inv"
            if ui["btn_prev"].collidepoint(px, py):
                player.inv.cycle_slot(-1)
                sound_bank.play("step", 0.35)
                show_toast(item_name(player.selected_item), 1.0)
                return "slot"
            if ui["btn_next"].collidepoint(px, py):
                player.inv.cycle_slot(1)
                sound_bank.play("step", 0.35)
                show_toast(item_name(player.selected_item), 1.0)
                return "slot"
            for idx, r in enumerate(ui["slots"]):
                if r.collidepoint(px, py):
                    player.inv.select_slot(idx)
                    sound_bank.play("step", 0.35)
                    show_toast(item_name(player.selected_item), 1.0)
                    return "slot"

            # Pinned persistent inventory overlay taps
            if player.inv.hud_pinned:
                if ui.get("pin_close") and ui["pin_close"].collidepoint(px, py):
                    player.inv.hud_pinned = False
                    auto_save(force=True)
                    sound_bank.play("step", 0.35)
                    return "ui"
                if ui.get("pin_bag") and ui["pin_bag"].collidepoint(px, py):
                    inv_ui.craft_station = "hand"
                    inv_ui.reset_selection()
                    state = "INVENTORY"
                    return "inv"
                for iid, tr in ui.get("pin_tiles", []):
                    if tr.collidepoint(px, py):
                        if player.inv.equip_to_hotbar(iid):
                            sound_bank.play("step", 0.4)
                            show_toast(f"Active: {item_name(iid)}", 1.1)
                            auto_save()
                        return "slot"
                if ui.get("pin_rect") and ui["pin_rect"].collidepoint(px, py):
                    return "ui"
            else:
                if ui.get("pin_expand") and ui["pin_expand"].collidepoint(px, py):
                    player.inv.hud_pinned = True
                    auto_save(force=True)
                    sound_bank.play("step", 0.35)
                    return "ui"
                if ui.get("pin_bag") and ui["pin_bag"].collidepoint(px, py):
                    inv_ui.craft_station = "hand"
                    inv_ui.reset_selection()
                    state = "INVENTORY"
                    return "inv"

            if ui["jump"].collidepoint(px, py):
                return "jump"
            if player.flying and ui["fly_down"].collidepoint(px, py):
                return "fly_down"
            if ui["mine"].collidepoint(px, py):
                do_attack_or_break()
                return "mine"
            if ui["place"].collidepoint(px, py):
                look = player.look_dir()
                t, prev, _ = raycast_block(world, player.x, player.eye_y, player.z, *look)
                do_place_or_use(t, prev)
                return "place"
            pcx, pad_cy, pr = ui["pad"]
            if (px - pcx) ** 2 + (py - pad_cy) ** 2 <= (pr * 1.25) ** 2:
                return "pad"
            return "look"

        elif state == "PAUSED":
            for label, rect in ui.get("pause_btns", []):
                if rect.collidepoint(px, py):
                    if label == "Resume Game":
                        state = "PLAYING"
                    elif label.startswith("Mode:"):
                        player.creative = not player.creative
                        player.flying = player.creative
                        show_toast("Mode: " + ("Creative" if player.creative else "Survival"))
                    elif label.startswith("Layout:"):
                        set_orientation_mode("horizontal" if orientation_mode == "vertical" else "vertical")
                    elif label.startswith("Graphics:"):
                        cycle_perf_mode()
                    elif label.startswith("Render:"):
                        opts = [10, 15, 22, 28]
                        renderer.render_dist = opts[(opts.index(renderer.render_dist) + 1) % len(opts)] if renderer.render_dist in opts else 15
                    elif label.startswith("Bright:"):
                        bright_boost = not bright_boost
                        show_toast("Visibility: " + ("Clear" if bright_boost else "Moody"), 1.4)
                    elif label.startswith("Weather:"):
                        nw = world.cycle_weather()
                        show_toast("Weather: " + nw.title(), 1.5)
                    elif label.startswith("Sound:"):
                        sound_bank.enabled = not sound_bank.enabled
                        if sound_bank.enabled:
                            sound_bank.play("place", 0.6)
                        else:
                            sound_bank.update_rain_ambience(0.0)
                    elif label == "Save World":
                        save_game(world, player, time_of_day)
                        has_save = True
                        sound_bank.play("place", 0.5)
                        show_toast("World Saved!")
                    elif label == "Main Title":
                        save_game(world, player, time_of_day)
                        has_save = True
                        state = "TITLE"
            return "ui"

        elif state == "INVENTORY":
            res = inv_ui.handle_tap(px, py, player.inv, sound_bank, show_toast)
            if res == "close":
                auto_save(force=True)
                state = "PLAYING"
            else:
                auto_save()
            return "ui"

        elif state == "FURNACE":
            if ui.get("inv_close") and ui["inv_close"].collidepoint(px, py):
                auto_save(force=True)
                state = "PLAYING"
                return "ui"

            def _do_smelt(ridx, smelt_all=False):
                in_id, out_id, out_cnt, _ = SMELT_RECIPES[ridx]
                coal_n = player.inv.count_of(ITEM_COAL)
                wood_n = player.inv.count_of(WOOD)
                fuel_n = 64 if player.creative else (coal_n + wood_n)
                in_n = 64 if player.creative else player.inv.count_of(in_id)
                avail = min(fuel_n, in_n)
                if avail <= 0:
                    show_toast("Need input item + Coal or Oak Log fuel!", 1.4)
                    return
                batches = min(16, avail) if (smelt_all and player.creative) else (avail if smelt_all else 1)
                if not player.creative:
                    player.inv.remove_item(in_id, batches)
                    rem = batches
                    take_c = min(rem, coal_n)
                    if take_c > 0:
                        player.inv.remove_item(ITEM_COAL, take_c)
                        rem -= take_c
                    if rem > 0:
                        player.inv.remove_item(WOOD, rem)
                tot_out = out_cnt * batches
                player.add_item(out_id, tot_out)
                player.inv.equip_to_hotbar(out_id)
                player.xp += 4 * batches
                auto_save()
                sound_bank.play("place")
                show_toast(f"Smelted {tot_out}x {item_name(out_id)}!", 1.4)

            if ui.get("smelt_one") and ui["smelt_one"].collidepoint(px, py):
                _do_smelt(selected_smelt, smelt_all=False)
                return "ui"
            if ui.get("smelt_all") and ui["smelt_all"].collidepoint(px, py):
                _do_smelt(selected_smelt, smelt_all=True)
                return "ui"
            for ridx, rect in ui.get("smelt_btns", []):
                if rect.collidepoint(px, py):
                    if selected_smelt == ridx:
                        _do_smelt(ridx, smelt_all=False)
                    else:
                        selected_smelt = ridx
                        sound_bank.play("step", 0.3)
                    return "ui"
            return "ui"

        elif state == "CHEST":
            if ui.get("inv_close") and ui["inv_close"].collidepoint(px, py):
                auto_save(force=True)
                state = "PLAYING"
                return "ui"
            for iid, rect in ui.get("chest_store", []):
                if rect.collidepoint(px, py) and player.inv.count_of(iid) > 0:
                    player.inv.remove_item(iid, 1)
                    world.chest_storage[iid] = world.chest_storage.get(iid, 0) + 1
                    sound_bank.play("chest")
                    return "ui"
            for iid, rect in ui.get("chest_take", []):
                if rect.collidepoint(px, py) and world.chest_storage.get(iid, 0) > 0:
                    world.chest_storage[iid] -= 1
                    player.add_item(iid, 1, record_collected=False)
                    sound_bank.play("chest")
                    return "ui"
            return "ui"
        return None

    running = True
    while running:
        dt = min(clock.tick(120) / 1000.0, 0.05)
        W, H = screen.get_size()
        cloud_shift += dt * 0.85
        if portal_cd > 0:
            portal_cd = max(0.0, portal_cd - dt)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.VIDEORESIZE:
                if not android_env:
                    orientation_mode = "vertical" if ev.h > ev.w else "horizontal"
                compute_layout(ev.w, ev.h)
            elif ev.type == pygame.FINGERDOWN:
                using_touch = True
                px, py = ev.x * W, ev.y * H
                role = handle_ui_tap(px, py)
                active_fingers[ev.finger_id] = {"x": px, "y": py, "role": role}
            elif ev.type == pygame.FINGERMOTION:
                using_touch = True
                px, py = ev.x * W, ev.y * H
                f = active_fingers.get(ev.finger_id)
                if f:
                    if f["role"] == "look" and state == "PLAYING":
                        dx, dy = px - f["x"], py - f["y"]
                        player.yaw += dx * 0.0052
                        player.pitch = max(-1.45, min(1.45, player.pitch - dy * 0.0052))
                    elif state == "INVENTORY":
                        inv_ui.handle_drag(py - f["y"])
                    f["x"], f["y"] = px, py
            elif ev.type == pygame.FINGERUP:
                active_fingers.pop(ev.finger_id, None)
            elif not using_touch:
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    px, py = ev.pos
                    if ev.button == 1:
                        role = handle_ui_tap(px, py)
                        if role == "look":
                            mouse_looking = True
                        elif role in ("jump", "mine", "fly_down", "pad") or (role == "ui" and state == "INVENTORY"):
                            active_fingers[-1] = {"x": px, "y": py, "role": role}
                    elif ev.button == 3 and state == "PLAYING":
                        look = player.look_dir()
                        t, prev, _ = raycast_block(world, player.x, player.eye_y, player.z, *look)
                        do_place_or_use(t, prev)
                    elif ev.button in (4, 5):
                        if state == "PLAYING":
                            player.inv.cycle_slot(-1 if ev.button == 4 else 1)
                            show_toast(item_name(player.selected_item), 0.9)
                        elif state == "INVENTORY":
                            inv_ui.scroll(-1 if ev.button == 4 else 1)
                elif ev.type == pygame.MOUSEMOTION:
                    px, py = ev.pos
                    if -1 in active_fingers:
                        if state == "INVENTORY":
                            inv_ui.handle_drag(py - active_fingers[-1]["y"])
                        active_fingers[-1]["x"], active_fingers[-1]["y"] = px, py
                    elif mouse_looking and state == "PLAYING":
                        dx, dy = ev.rel
                        player.yaw += dx * 0.0045
                        player.pitch = max(-1.45, min(1.45, player.pitch - dy * 0.0045))
                elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                    mouse_looking = False
                    active_fingers.pop(-1, None)

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE and state != "TITLE":
                    if state == "INVENTORY":
                        auto_save(force=True)
                    state = "PAUSED" if state == "PLAYING" else "PLAYING"
                elif ev.key == pygame.K_e and state in ("PLAYING", "INVENTORY"):
                    if state == "INVENTORY":
                        auto_save(force=True)
                    else:
                        inv_ui.craft_station = "hand"
                        inv_ui.reset_selection()
                    state = "INVENTORY" if state == "PLAYING" else "PLAYING"
                elif ev.key == pygame.K_v:
                    set_orientation_mode("vertical" if orientation_mode == "horizontal" else "horizontal")
                elif ev.key == pygame.K_h:
                    set_orientation_mode("horizontal")
                elif ev.key == pygame.K_g:
                    cycle_perf_mode()
                elif ev.key == pygame.K_b:
                    bright_boost = not bright_boost
                    show_toast("Visibility: " + ("Clear" if bright_boost else "Moody"), 1.4)
                elif ev.key == pygame.K_t and state == "PLAYING":
                    nw = world.cycle_weather()
                    show_toast("Weather: " + nw.title(), 1.5)
                elif ev.key == pygame.K_f and player.creative:
                    player.flying = not player.flying
                elif pygame.K_1 <= ev.key <= pygame.K_9:
                    player.inv.select_slot(ev.key - pygame.K_1)
                    show_toast(item_name(player.selected_item), 0.9)

        if toast_timer > 0:
            toast_timer -= dt

        move_fwd = move_right = 0.0
        want_jump = want_descend = want_mine = want_sprint = False

        if state == "PLAYING":
            keys = pygame.key.get_pressed()
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                move_fwd += 1.0
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                move_fwd -= 1.0
            if keys[pygame.K_d]:
                move_right += 1.0
            if keys[pygame.K_a]:
                move_right -= 1.0
            if keys[pygame.K_LEFT]:
                player.yaw -= 2.1 * dt
            if keys[pygame.K_RIGHT]:
                player.yaw += 2.1 * dt
            if keys[pygame.K_SPACE]:
                want_jump = True
            if keys[pygame.K_LSHIFT] or keys[pygame.K_c]:
                want_descend = True
                want_sprint = True

            pad_cx, pad_cy, pad_r = ui["pad"]
            for f in active_fingers.values():
                role = f["role"]
                if role == "pad":
                    ox = (f["x"] - pad_cx) / (pad_r * 0.72)
                    oy = -(f["y"] - pad_cy) / (pad_r * 0.72)
                    move_right += max(-1.0, min(1.0, ox))
                    move_fwd += max(-1.0, min(1.0, oy))
                    if math.hypot(ox, oy) > 0.90:
                        want_sprint = True
                elif role == "jump":
                    want_jump = True
                elif role == "fly_down":
                    want_descend = True
                elif role == "mine":
                    want_mine = True

            time_of_day = (time_of_day + dt * 0.0032) % 1.0
            world.ensure_chunks_around(player.x, player.z, renderer.render_dist + 4, max_gen_per_frame=4)
            player.update(world, dt, move_fwd, move_right, want_jump, want_descend, want_sprint, sound_bank=sound_bank)

            if portal_cd <= 0.0 and world.get_block(math.floor(player.x), math.floor(player.y + 0.5), math.floor(player.z)) == PORTAL:
                enter_nether_or_overworld()

            if player.on_ground and not player.flying and (abs(player.vx) > 0.45 or abs(player.vz) > 0.45):
                step_timer += dt * (1.35 if want_sprint else 1.0)
                if step_timer >= 0.42:
                    step_timer = 0.0
                    sound_bank.play("step", volume=0.45)
            else:
                step_timer = 0.30

            sky_rgb, ambient, sun_dir, is_day, day_fac = compute_sky_and_light(
                time_of_day, world.dimension, bright_boost=bright_boost,
                weather=world.weather, weather_intensity=world.weather_intensity,
                lightning_flash=world.lightning_flash,
            )
            world.update(dt, player, is_day, sound_bank)

            p_biome = world.get_biome(int(player.x), int(player.z))
            in_shelter = world.has_roof_above(player.x, player.eye_y, player.z)
            is_overworld = (world.dimension == "overworld")
            is_cold_biome = p_biome in ("snowy_mountains", "taiga")
            is_dry_biome = p_biome in ("desert", "badlands")
            rain_audio_int = world.weather_intensity if (is_overworld and not is_cold_biome and not is_dry_biome) else 0.0
            sound_bank.update_rain_ambience(rain_audio_int, in_shelter=in_shelter)

            if not player.creative and player.health <= 0:
                player.health = player.max_health
                player.hunger = 20
                player.air = 20
                if world.dimension == "nether":
                    world.switch_dimension()
                    world.ensure_chunks_around(player.spawn_x, player.spawn_z, 20, max_gen_per_frame=64)
                player.x, player.z = player.spawn_x, player.spawn_z
                player.y = player.spawn_y
                sound_bank.play("hit")
                show_toast("You died! Respawned at spawn", 2.8)
        else:
            p_biome = world.get_biome(int(player.x), int(player.z))
            in_shelter = False
            is_overworld = (world.dimension == "overworld")
            is_cold_biome = p_biome in ("snowy_mountains", "taiga")
            is_dry_biome = p_biome in ("desert", "badlands")
            sound_bank.update_rain_ambience(0.0)
            sky_rgb, ambient, sun_dir, is_day, day_fac = compute_sky_and_light(
                time_of_day, world.dimension, bright_boost=bright_boost,
                weather=world.weather, weather_intensity=world.weather_intensity,
                lightning_flash=world.lightning_flash,
            )

        look = player.look_dir()
        target_block, _prev_air, _ = raycast_block(world, player.x, player.eye_y, player.z, *look)

        if state == "PLAYING" and want_mine and target_block is not None:
            if target_block != mining_target:
                mining_target = target_block
                mining_progress = 0.0
            bid = world.get_block(*target_block)
            bmeta = BLOCKS.get(bid, {})
            base_t = bmeta.get("break_time", 0.5)
            sel_meta = ITEMS.get(player.selected_item, {})
            tool_spd = 1.0
            if bmeta.get("pick") and "pick_speed" in sel_meta:
                tool_spd = sel_meta["pick_speed"]
            elif bmeta.get("axe") and "axe_speed" in sel_meta:
                tool_spd = sel_meta["axe_speed"]
            elif bmeta.get("shovel") and "shovel_speed" in sel_meta:
                tool_spd = sel_meta["shovel_speed"]
            req_t = 0.12 if player.creative else (base_t / tool_spd)
            mining_progress += dt
            if int(mining_progress * 8) != int((mining_progress - dt) * 8):
                player.swing_timer = 0.16
            if mining_progress >= req_t:
                do_break_block(target_block)
                mining_progress = 0.0
                mining_target = None
        else:
            mining_progress = 0.0
            mining_target = None

        fonts = ui["fonts"]
        font_xs, font_sm, font_md, font_lg = fonts["xs"], fonts["sm"], fonts["md"], fonts["lg"]
        cache = ui["cache"]

        if state == "TITLE":
            if cache["title_bg_scaled"] is not None:
                screen.blit(cache["title_bg_scaled"], (0, 0))
                screen.blit(cache["ov_title"], (0, 0))
            else:
                screen.fill((22, 34, 54))

            t1 = font_lg.render("PYCRAFT", True, (118, 232, 92))
            t2 = font_sm.render("Full-Scale 16x16 Textures • Crafting, Nether & Mobs", True, (240, 245, 250))
            screen.blit(t1, t1.get_rect(center=(W // 2, int(H * 0.14))))
            screen.blit(t2, t2.get_rect(center=(W // 2, int(H * 0.22))))

            labels = [
                "Play Survival",
                "Play Creative",
                "Layout: " + ("Vertical Mode" if ui["is_vert"] else "Horizontal Mode"),
            ]
            if has_save:
                labels.insert(0, "Continue Saved World")
            bw = min(520, int(W * 0.84))
            bh = max(56, min(86, int(H * 0.105)))
            gap_y = max(12, int(H * 0.02))
            y0 = int(H * 0.30)
            title_btns = []
            for i, lbl_txt in enumerate(labels):
                r = pygame.Rect((W - bw) // 2, y0 + i * (bh + gap_y), bw, bh)
                col = (44, 138, 72) if "Survival" in lbl_txt or "Continue" in lbl_txt else (52, 74, 112)
                pygame.draw.rect(screen, col, r, border_radius=12)
                pygame.draw.rect(screen, (230, 240, 250), r, 2, border_radius=12)
                lbl = font_md.render(lbl_txt, True, (255, 255, 255))
                screen.blit(lbl, lbl.get_rect(center=r.center))
                title_btns.append((lbl_txt, r))
            ui["title_btns"] = title_btns
            pygame.display.flip()
            continue

        screen.fill(sky_rgb)
        hand_lit = player.selected_item in (TORCH, GLOWSTONE, ITEM_BUCKET_LAVA, PORTAL)
        draw_faces, part_2d, cam_vars, cloud_2d = renderer.build_draw_list(
            world, player, W, H, sky_rgb, ambient, target_block if state == "PLAYING" else None,
            use_tex_grid=(state == "PLAYING"), cloud_shift=cloud_shift, hand_light=hand_lit,
        )
        _cx, _cy, _cz, fx, fy, fz, rx, rz, ux, uy, uz, half_w, half_h, focal = cam_vars

        if is_overworld and day_fac < 0.45 and world.weather_intensity < 0.65:
            star_vis = max(0.0, 1.0 - world.weather_intensity * 1.5)
            star_alpha = int((1.0 - day_fac / 0.45) * 220 * star_vis)
            if star_alpha > 12:
                star_col = (star_alpha, star_alpha, min(255, star_alpha + 25))
                for sdx, sdy, sdz in renderer.stars:
                    spz = sdx * fx + sdy * fy + sdz * fz
                    if spz > 0.1:
                        ssx = int(half_w + ((sdx * rx + sdz * rz) / spz) * focal)
                        ssy = int(half_h - ((sdx * ux + sdy * uy + sdz * uz) / spz) * focal)
                        if 0 <= ssx < W and 0 <= ssy < H:
                            pygame.draw.rect(screen, star_col, (ssx, ssy, 2, 2))

        if is_overworld and world.weather_intensity < 0.75:
            for is_sun, svec in ((True, sun_dir), (False, (-sun_dir[0], -sun_dir[1], -sun_dir[2]))):
                sdx, sdy, sdz = svec
                spz = sdx * fx + sdy * fy + sdz * fz
                if spz > 0.1:
                    ssx = int(half_w + ((sdx * rx + sdz * rz) / spz) * focal)
                    ssy = int(half_h - ((sdx * ux + sdy * uy + sdz * uz) / spz) * focal)
                    sz = max(16, int(focal * 0.088))
                    halo = (255, 224, 108) if is_sun else (175, 190, 218)
                    core = (255, 250, 196) if is_sun else (232, 238, 248)
                    pygame.draw.rect(screen, halo, (ssx - sz, ssy - sz, sz * 2, sz * 2))
                    isz = max(8, int(sz * 0.7))
                    pygame.draw.rect(screen, core, (ssx - isz, ssy - isz, isz * 2, isz * 2))

        for cpts, ccol in cloud_2d:
            pygame.draw.polygon(screen, ccol, cpts)

        # Sky lightning bolt (rendered behind world terrain)
        if is_overworld and world.lightning_flash > 0.30:
            lpos_x, lpos_h = world.lightning_pos
            bx_cur = int(W * (0.5 + lpos_x * 0.44))
            by_end = int(H * lpos_h)
            bolt_pts = [(bx_cur, 0)]
            seed_b = int((lpos_x + 1.0) * 997)
            steps_b = 7
            for bi in range(1, steps_b + 1):
                jag = (((seed_b * (bi + 3) * 37) % 39) - 19)
                bx_cur = max(16, min(W - 16, bx_cur + jag))
                by_cur = int((by_end * bi) / steps_b)
                bolt_pts.append((bx_cur, by_cur))
            pygame.draw.lines(screen, (150, 196, 255), False, bolt_pts, 6)
            pygame.draw.lines(screen, (245, 250, 255), False, bolt_pts, 2)
            # Short secondary fork
            if len(bolt_pts) >= 5:
                fx0, fy0 = bolt_pts[2]
                fork_pts = [(fx0, fy0), (fx0 + 22, fy0 + 28), (fx0 + 34, fy0 + 56)]
                pygame.draw.lines(screen, (190, 222, 255), False, fork_pts, 2)

        alpha_scratch = cache["alpha_scratch"]
        sw, sh = alpha_scratch.get_size()
        for dist_sq, pts2d, color, bid, _fidx, is_target, sub_quads in draw_faces:
            if bid in (WATER, GLASS, ICE, PORTAL):
                p0x, p0y = pts2d[0]
                min_x = max_x = p0x
                min_y = max_y = p0y
                for px_p, py_p in pts2d[1:]:
                    if px_p < min_x:
                        min_x = px_p
                    elif px_p > max_x:
                        max_x = px_p
                    if py_p < min_y:
                        min_y = py_p
                    elif py_p > max_y:
                        max_y = py_p
                min_x = 0 if min_x < 0 else int(min_x)
                max_x = W if max_x > W else int(max_x)
                min_y = 0 if min_y < 0 else int(min_y)
                max_y = H if max_y > H else int(max_y)
                bw, bh = min(sw, max_x - min_x), min(sh, max_y - min_y)
                if bw > 1 and bh > 1:
                    alpha = 152 if bid == WATER else (175 if bid == ICE else (168 if bid == PORTAL else 108))
                    alpha_scratch.fill((0, 0, 0, 0), (0, 0, bw, bh))
                    local_pts = [(x - min_x, y - min_y) for x, y in pts2d]
                    pygame.draw.polygon(alpha_scratch, (*color, alpha), local_pts)
                    if bid == GLASS:
                        pygame.draw.polygon(alpha_scratch, (235, 250, 255, 210), local_pts, 1)
                    screen.blit(alpha_scratch, (min_x, min_y), (0, 0, bw, bh))
            elif sub_quads is not None:
                pygame.draw.polygon(screen, color, pts2d)
                for sq_pts, sq_col in sub_quads:
                    pygame.draw.polygon(screen, sq_col, sq_pts)
                if is_target:
                    pygame.draw.polygon(screen, (20, 20, 20), pts2d, 2)
                    if mining_progress > 0:
                        cx_t = sum(p[0] for p in pts2d) / len(pts2d)
                        cy_t = sum(p[1] for p in pts2d) / len(pts2d)
                        for p in pts2d:
                            pygame.draw.line(screen, (25, 25, 25), (cx_t, cy_t), ((cx_t + p[0]) * 0.5, (cy_t + p[1]) * 0.5), 2)
            else:
                pygame.draw.polygon(screen, color, pts2d)
                if is_target:
                    pygame.draw.polygon(screen, (20, 20, 20), pts2d, 2)
                elif bid > 0 and dist_sq < 24.0:
                    ec = (max(0, color[0] - 18), max(0, color[1] - 18), max(0, color[2] - 18))
                    pygame.draw.polygon(screen, ec, pts2d, 1)

        for _, psx, psy, sz_px, prgb in part_2d:
            pygame.draw.rect(screen, prgb, (int(psx - sz_px * 0.5), int(psy - sz_px * 0.5), sz_px, sz_px))

        # Biome-aware Overworld precipitation (rain streaks, drifting snow, desert wind dust) + storm overlays
        if state == "PLAYING" and is_overworld and world.weather_intensity > 0.03:
            wint = world.weather_intensity
            is_thunder = (world.weather == "thunder")
            t_off = int(cloud_shift * 260)
            if is_cold_biome:
                n_flakes = int((34 if renderer.perf_mode == "fast" else 48) * wint)
                for ri in range(n_flakes):
                    wobble = int(math.sin(cloud_shift * 2.4 + ri * 0.7) * 14)
                    rx_s = (ri * 97 + t_off // 5 + wobble) % W
                    if in_shelter and (W * 0.25 < rx_s < W * 0.75):
                        continue
                    ry_s = (ri * 59 + int(cloud_shift * (78 if (ri & 1) else 108))) % H
                    sz_f = 4 if (ri & 3) == 0 else 2
                    col_f = (244, 250, 255) if (ri & 1) else (216, 232, 248)
                    pygame.draw.rect(screen, col_f, (rx_s, ry_s, sz_f, sz_f))
            elif is_dry_biome:
                if is_thunder or wint > 0.45:
                    n_dust = int(18 * wint)
                    dcol = (212, 188, 138)
                    for ri in range(n_dust):
                        rx_s = (ri * 113 + t_off * 2) % W
                        ry_s = (ri * 67 + t_off // 3) % H
                        pygame.draw.line(screen, dcol, (rx_s, ry_s), (rx_s + 10, ry_s + 2), 1)
            else:
                base_drops = 38 if renderer.perf_mode == "fast" else (64 if is_thunder else 48)
                n_drops = int(base_drops * wint)
                sl_dx = -5 if is_thunder else -2
                sl_dy = 17 if is_thunder else 12
                bg_col = (118, 162, 224)
                fg_col = (168, 210, 252)
                for ri in range(n_drops):
                    near = (ri & 1) == 0
                    spd = 4 if near else 3
                    rx_s = (ri * 97 + (t_off // (2 if is_thunder else 4))) % W
                    if in_shelter and (W * 0.22 < rx_s < W * 0.78):
                        continue
                    ry_s = (ri * 53 + t_off * spd) % H
                    if near:
                        pygame.draw.line(screen, fg_col, (rx_s, ry_s), (rx_s + sl_dx, ry_s + sl_dy), 2 if is_thunder else 1)
                    else:
                        pygame.draw.line(screen, bg_col, (rx_s, ry_s), (rx_s + sl_dx // 2, ry_s + sl_dy - 4), 1)

            if wint > 0.10 and not is_dry_biome:
                st_surf = cache["ov_storm"]
                st_surf.set_alpha(int(wint * (36 if is_thunder else 18)))
                screen.blit(st_surf, (0, 0))

        if is_overworld and world.lightning_flash > 0.04:
            fl_surf = cache["ov_flash"]
            fl_surf.set_alpha(int(world.lightning_flash * 76))
            screen.blit(fl_surf, (0, 0))

        if player.head_in_water:
            screen.blit(cache["ov_water"], (0, 0))
        if player.hurt_flash > 0:
            screen.blit(cache["ov_hurt"], (0, 0))

        if state == "PLAYING":
            # First-person Steve Arm + Held 3D Block/Tool
            swing_off = math.sin(player.swing_timer * 24.0) * 32.0 if player.swing_timer > 0 else 0.0
            bob_y = math.sin(player.walk_bob) * 7.0
            icon_sz = max(50, int(min(W, H) * 0.10))
            hx = int((W * 0.80 if ui["is_vert"] else W * 0.82) - swing_off * 0.65)
            hy = int((H * 0.63 if ui["is_vert"] else H * 0.80) + bob_y + swing_off * 0.4)
            # Arm sleeve behind held item
            pygame.draw.polygon(screen, (62, 168, 172), [
                (hx - 14, hy + 8), (hx + 22, hy - 4), (W, H), (W - 44, H)
            ])
            draw_item_icon(player.selected_item, pygame.Rect(hx - icon_sz // 2, hy - icon_sz // 2, icon_sz, icon_sz))

            ch_x, ch_y = W // 2, H // 2
            pygame.draw.line(screen, (255, 255, 255), (ch_x - 10, ch_y), (ch_x + 10, ch_y), 2)
            pygame.draw.line(screen, (255, 255, 255), (ch_x, ch_y - 10), (ch_x, ch_y + 10), 2)

            if mining_progress > 0 and mining_target is not None:
                bid = world.get_block(*mining_target)
                base_t = BLOCKS.get(bid, {}).get("break_time", 0.5)
                req_t = 0.12 if player.creative else base_t
                frac = min(1.0, mining_progress / max(0.05, req_t))
                pygame.draw.rect(screen, (30, 30, 30), (ch_x - 28, ch_y + 18, 56, 7))
                pygame.draw.rect(screen, (255, 220, 80), (ch_x - 28, ch_y + 18, int(56 * frac), 7))

            top_surfs = cache["top_btn_surfs"]
            lbl_sm_cache = cache["lbl_sm"]
            layout_lbl = "HORZ" if ui["is_vert"] else "VERT"
            for rect, txt in (
                (ui["btn_pause"], "MENU"),
                (ui["btn_fly"], "FLY*" if player.flying else "FLY"),
                (ui["btn_time"], "TIME"),
                (ui["btn_layout"], layout_lbl),
                (ui["btn_save"], "SAVE"),
            ):
                screen.blit(top_surfs[(rect.w, rect.h)], rect.topleft)
                pygame.draw.rect(screen, (200, 210, 225), rect, 2, border_radius=8)
                lbl = lbl_sm_cache.get(txt)
                if lbl is None:
                    lbl = font_sm.render(txt, True, (245, 248, 255))
                    lbl_sm_cache[txt] = lbl
                screen.blit(lbl, lbl.get_rect(center=rect.center))

            biome_lbl = p_biome.replace("_", " ").title()
            info_key = (biome_lbl, int(player.x), int(player.y), int(player.z), int(clock.get_fps()), world.weather)
            if cache["info_key"] != info_key:
                wtag = " • Storm" if world.weather == "thunder" else (" • Rain" if world.weather == "rain" else "")
                info_str = f"{biome_lbl}{wtag}  {info_key[1]},{info_key[2]},{info_key[3]}  {info_key[4]}fps"
                cache["info_surf"] = font_xs.render(info_str, True, (245, 250, 255))
                cache["info_key"] = info_key
            info_txt = cache["info_surf"]
            pix = cache["pix_icons"]
            pstep = cache["pix_step"]

            if ui["is_vert"]:
                info_y = ui["btn_pause"].bottom + 8
                screen.blit(info_txt, (12, info_y))
                if not player.creative:
                    hearts = player.health // 2
                    hungers = player.hunger // 2
                    armors = player.armor // 2
                    for i in range(10):
                        ix = W - 14 - (i + 1) * pstep
                        if armors > 0:
                            screen.blit(pix["armor_full"] if i < armors else pix["armor_empty"], (ix, info_y))
                        screen.blit(pix["heart_full"] if i < hearts else pix["heart_empty"], (ix, info_y + (pstep if armors > 0 else 0)))
                        screen.blit(pix["meat_full"] if i < hungers else pix["meat_empty"], (ix, info_y + pstep * (2 if armors > 0 else 1)))
                        if player.head_in_water and i < (player.air // 2):
                            screen.blit(pix["bubble"], (ix, info_y + pstep * (3 if armors > 0 else 2)))
            else:
                screen.blit(info_txt, (W - info_txt.get_width() - 14, 10))
                if not player.creative:
                    hearts = player.health // 2
                    hungers = player.hunger // 2
                    armors = player.armor // 2
                    hy_row = 14 + info_txt.get_height()
                    for i in range(10):
                        ix = W - 14 - (i + 1) * pstep
                        if armors > 0:
                            screen.blit(pix["armor_full"] if i < armors else pix["armor_empty"], (ix, hy_row))
                        screen.blit(pix["heart_full"] if i < hearts else pix["heart_empty"], (ix, hy_row + (pstep if armors > 0 else 0)))
                        screen.blit(pix["meat_full"] if i < hungers else pix["meat_empty"], (ix, hy_row + pstep * (2 if armors > 0 else 1)))
                        if player.head_in_water and i < (player.air // 2):
                            screen.blit(pix["bubble"], (ix, hy_row + pstep * (3 if armors > 0 else 2)))

            pcx, pcy, pr = ui["pad"]
            screen.blit(cache["pad_surf"], (pcx - pr - 2, pcy - pr - 2))

            knob_x, knob_y = pcx, pcy
            for f in active_fingers.values():
                if f["role"] == "pad":
                    dx, dy = f["x"] - pcx, f["y"] - pcy
                    d = math.hypot(dx, dy)
                    lim = pr * 0.65
                    if d > lim and d > 0:
                        dx, dy = dx / d * lim, dy / d * lim
                    knob_x, knob_y = int(pcx + dx), int(pcy + dy)
                    break
            pygame.draw.circle(screen, (240, 245, 255), (knob_x, knob_y), int(pr * 0.28))

            action_surfs = cache["action_surfs"]
            action_keys = [
                ("jump", "UP" if player.flying else "JUMP"),
                ("mine", "MINE"),
                ("place", "USE"),
            ]
            if player.flying:
                action_keys.append(("fly_down", "DOWN"))
            for key, txt in action_keys:
                rect = ui[key]
                screen.blit(action_surfs[key], rect.topleft)
                lbl = lbl_sm_cache.get(txt)
                if lbl is None:
                    lbl = font_sm.render(txt, True, (255, 255, 255))
                    lbl_sm_cache[txt] = lbl
                screen.blit(lbl, lbl.get_rect(center=rect.center))

            # Minecraft XP Bar + Level Number above hotbar
            first_slot, last_slot = ui["slots"][0], ui["slots"][-1]
            xp_w = last_slot.right - first_slot.x
            pygame.draw.rect(screen, (18, 22, 28), (first_slot.x, first_slot.y - 11, xp_w, 7))
            pygame.draw.rect(screen, (116, 248, 72), (first_slot.x, first_slot.y - 11, int(xp_w * ((player.xp % 20) / 20.0)), 7))
            lv_num = player.xp // 20
            if lv_num > 0:
                lvl_txt = cache["cnt_xs"].get(("lv", lv_num))
                if lvl_txt is None:
                    lvl_txt = font_xs.render(str(lv_num), True, (132, 252, 82))
                    cache["cnt_xs"][("lv", lv_num)] = lvl_txt
                screen.blit(lvl_txt, lvl_txt.get_rect(center=(first_slot.x + xp_w // 2, first_slot.y - 14)))

            # Stone-framed Minecraft Hotbar
            cyc_surf = cache["cyc_surf"]
            lbl_md_cache = cache["lbl_md"]
            for btn_r, sym in ((ui["btn_prev"], "<"), (ui["btn_next"], ">")):
                screen.blit(cyc_surf, btn_r.topleft)
                pygame.draw.rect(screen, (170, 185, 205), btn_r, 2, border_radius=6)
                cl = lbl_md_cache.get(sym)
                if cl is None:
                    cl = font_md.render(sym, True, (255, 255, 255))
                    lbl_md_cache[sym] = cl
                screen.blit(cl, cl.get_rect(center=btn_r.center))

            slot_surf = cache["slot_surf"]
            cnt_cache = cache["cnt_xs"]
            for idx, rect in enumerate(ui["slots"]):
                slot = player.inv.hotbar[idx]
                screen.blit(slot_surf, rect.topleft)
                is_sel = (idx == player.inv.selected_slot)
                pygame.draw.rect(screen, (250, 250, 255) if is_sel else (110, 118, 128), rect, 3 if is_sel else 2, border_radius=4)
                if not slot.is_empty():
                    pad_in = max(5, rect.w // 6)
                    draw_item_icon(slot.item_id, pygame.Rect(rect.x + pad_in, rect.y + pad_in, rect.w - pad_in * 2, rect.h - pad_in * 2))
                    if not player.creative and slot.count > 1:
                        c_lbl = cnt_cache.get(slot.count)
                        if c_lbl is None:
                            c_lbl = font_xs.render(str(slot.count), True, (255, 255, 255))
                            cnt_cache[slot.count] = c_lbl
                        screen.blit(c_lbl, (rect.right - c_lbl.get_width() - 3, rect.bottom - c_lbl.get_height() - 2))

            inv_r = ui["btn_inv"]
            screen.blit(cache["inv_surf"], inv_r.topleft)
            pygame.draw.rect(screen, (210, 218, 230), inv_r, 2, border_radius=6)
            ilbl = lbl_md_cache.get("...")
            if ilbl is None:
                ilbl = font_md.render("...", True, (255, 255, 255))
                lbl_md_cache["..."] = ilbl
            screen.blit(ilbl, ilbl.get_rect(center=inv_r.center))

            # Persistent Quick Inventory & Collection Overlay (touch-friendly active item switcher)
            px0, py0, pw0, ph0, ptile, pgap, ppad, phdr = ui["pin_metrics"]
            tot_col = player.inv.total_collected_count()
            if player.inv.hud_pinned:
                ui["pin_rect"] = pygame.Rect(px0, py0, pw0, ph0)
                screen.blit(cache["pin_bg"], (px0, py0))

                bag_r = pygame.Rect(px0 + pw0 - ppad - 74, py0 + 5, 42, 24)
                cls_r = pygame.Rect(px0 + pw0 - ppad - 28, py0 + 5, 28, 24)
                ui["pin_bag"] = bag_r
                ui["pin_close"] = cls_r
                ui["pin_expand"] = None

                act_name = item_name(player.selected_item)[:10]
                hdr_txt = font_xs.render(f"{act_name} • {tot_col}", True, (255, 230, 128))
                screen.blit(hdr_txt, (px0 + ppad, py0 + 8))

                pygame.draw.rect(screen, (50, 96, 146), bag_r, border_radius=5)
                pygame.draw.rect(screen, (186, 212, 244), bag_r, 1, border_radius=5)
                blbl = font_xs.render("BAG", True, (255, 255, 255))
                screen.blit(blbl, blbl.get_rect(center=bag_r.center))

                pygame.draw.rect(screen, (52, 60, 76), cls_r, border_radius=5)
                pygame.draw.rect(screen, (150, 165, 188), cls_r, 1, border_radius=5)
                mlbl = font_xs.render("-", True, (255, 255, 255))
                screen.blit(mlbl, mlbl.get_rect(center=cls_r.center))

                q_items = player.inv.quick_switch_items(3, 3)[:5]
                pin_tiles = []
                ty0 = py0 + ppad + phdr + 2
                for qi, (qiid, qcnt) in enumerate(q_items):
                    tr = pygame.Rect(px0 + ppad + qi * (ptile + pgap), ty0, ptile, ptile)
                    q_sel = (qiid == player.selected_item)
                    pygame.draw.rect(screen, (54, 92, 66) if q_sel else (38, 46, 62), tr, border_radius=6)
                    pygame.draw.rect(screen, (255, 224, 88) if q_sel else (120, 136, 160), tr, 2 if q_sel else 1, border_radius=6)
                    in_p = max(4, ptile // 7)
                    draw_item_icon(qiid, pygame.Rect(tr.x + in_p, tr.y + in_p, ptile - in_p * 2, ptile - in_p * 2))
                    if not player.creative and qcnt > 1:
                        qc_lbl = cnt_cache.get(qcnt)
                        if qc_lbl is None:
                            qc_lbl = font_xs.render(str(qcnt), True, (255, 255, 255))
                            cnt_cache[qcnt] = qc_lbl
                        screen.blit(qc_lbl, (tr.right - qc_lbl.get_width() - 2, tr.bottom - qc_lbl.get_height() - 1))
                    pin_tiles.append((qiid, tr))
                ui["pin_tiles"] = pin_tiles
            else:
                mini_r = pygame.Rect(px0, py0, 138, 34)
                bag_r = pygame.Rect(px0, py0, 102, 34)
                exp_r = pygame.Rect(px0 + 104, py0, 34, 34)
                ui["pin_rect"] = mini_r
                ui["pin_bag"] = bag_r
                ui["pin_expand"] = exp_r
                ui["pin_close"] = None
                ui["pin_tiles"] = []
                screen.blit(cache["pin_mini_bg"], (px0, py0))
                pygame.draw.line(screen, (120, 140, 168), (px0 + 103, py0 + 5), (px0 + 103, py0 + 29), 1)
                blbl = font_xs.render(f"INV • {tot_col}", True, (240, 246, 255))
                screen.blit(blbl, blbl.get_rect(center=bag_r.center))
                plbl = font_xs.render("+", True, (132, 248, 152))
                screen.blit(plbl, plbl.get_rect(center=exp_r.center))

            if toast_timer > 0 and toast_msg:
                if toast_cache_key != (toast_msg, W):
                    tlbl = font_sm.render(toast_msg, True, (255, 246, 196))
                    bg_w = tlbl.get_width() + 28
                    bg_h = tlbl.get_height() + 14
                    ts = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
                    pygame.draw.rect(ts, (15, 18, 25, 185), (0, 0, bg_w, bg_h), border_radius=10)
                    ts.blit(tlbl, (14, 7))
                    toast_cache_surf = ts
                    toast_cache_key = (toast_msg, W)
                tr = toast_cache_surf.get_rect(center=(W // 2, max(104, int(H * 0.17))))
                screen.blit(toast_cache_surf, tr.topleft)

        elif state == "PAUSED":
            screen.blit(cache["ov_dark"], (0, 0))
            title = font_lg.render("PYCRAFT MENU", True, (118, 212, 92))
            screen.blit(title, title.get_rect(center=(W // 2, int(H * 0.08))))
            labels = [
                "Resume Game",
                "Mode: " + ("Creative (Infinite/Fly)" if player.creative else "Survival"),
                "Layout: " + ("Vertical Mode" if ui["is_vert"] else "Horizontal Mode"),
                f"Graphics: {renderer.perf_mode.title()} (FPS Boost)",
                f"Render: {renderer.render_dist} Blocks",
                "Bright: " + ("Clear (High Vis)" if bright_boost else "Moody"),
                "Weather: " + world.weather.title(),
                "Sound: " + ("ON" if sound_bank.enabled else "OFF"),
                "Save World",
                "Main Title",
            ]
            bw = min(520, int(W * 0.84))
            bh = max(36, min(52, int(H * 0.066)))
            gap_y = max(5, int(H * 0.008))
            y0 = int(H * 0.13)
            pause_btns = []
            for i, txt in enumerate(labels):
                r = pygame.Rect((W - bw) // 2, y0 + i * (bh + gap_y), bw, bh)
                pygame.draw.rect(screen, (48, 56, 70), r, border_radius=10)
                pygame.draw.rect(screen, (170, 185, 205), r, 2, border_radius=10)
                lbl = font_sm.render(txt, True, (245, 248, 255))
                screen.blit(lbl, lbl.get_rect(center=r.center))
                pause_btns.append((txt, r))
            ui["pause_btns"] = pause_btns

        elif state == "INVENTORY":
            inv_ui.render(pygame, screen, assets, player.inv, fonts, W, H, is_vert=ui["is_vert"])

        elif state == "FURNACE":
            screen.blit(cache["ov_dark"], (0, 0))
            s_min = min(W, H)
            close_w = max(110, int(s_min * 0.22))
            close_h = max(44, int(s_min * 0.082))
            screen.blit(font_lg.render("FURNACE", True, (245, 220, 110)), (16, 14))
            close_r = pygame.Rect(W - close_w - 16, 14, close_w, close_h)
            pygame.draw.rect(screen, (190, 68, 58), close_r, border_radius=8)
            pygame.draw.rect(screen, (255, 220, 215), close_r, 2, border_radius=8)
            clbl = font_sm.render("CLOSE", True, (255, 255, 255))
            screen.blit(clbl, clbl.get_rect(center=close_r.center))
            ui["inv_close"] = close_r

            # Visual Furnace Chamber (Input + Fuel -> Flame -> Output + Smelt Buttons)
            if selected_smelt >= len(SMELT_RECIPES):
                selected_smelt = 0
            s_in_id, s_out_id, s_out_cnt, _ = SMELT_RECIPES[selected_smelt]
            coal_cnt = player.inv.count_of(ITEM_COAL)
            wood_cnt = player.inv.count_of(WOOD)
            fuel_tot = 64 if player.creative else (coal_cnt + wood_cnt)
            in_tot = 64 if player.creative else player.inv.count_of(s_in_id)
            can_smelt_sel = fuel_tot > 0 and in_tot > 0
            max_smelt = min(fuel_tot, in_tot)

            bw = min(680, W - 32)
            bx = (W - bw) // 2
            top_y = 24 + close_h
            cham_h = max(130, int(H * 0.22))
            cham_r = pygame.Rect(bx, top_y, bw, cham_h)
            pygame.draw.rect(screen, (36, 30, 32), cham_r, border_radius=12)
            pygame.draw.rect(screen, (192, 132, 76), cham_r, 2, border_radius=12)

            slot_sz = max(46, min(68, cham_h - 36))
            in_r = pygame.Rect(bx + 18, top_y + 14, slot_sz, slot_sz)
            fuel_r = pygame.Rect(bx + 18 + slot_sz + 14, top_y + 14, slot_sz, slot_sz)
            out_r = pygame.Rect(fuel_r.right + 56, top_y + 14, slot_sz, slot_sz)
            for sr, iid, scnt, sc_col in (
                (in_r, s_in_id, in_tot, (150, 236, 168) if in_tot > 0 else (244, 120, 120)),
                (fuel_r, ITEM_COAL if coal_cnt > 0 or player.creative else WOOD, fuel_tot, (255, 196, 98) if fuel_tot > 0 else (244, 120, 120)),
                (out_r, s_out_id, s_out_cnt, (255, 232, 132)),
            ):
                pygame.draw.rect(screen, (52, 46, 48), sr, border_radius=8)
                pygame.draw.rect(screen, sc_col, sr, 2, border_radius=8)
                draw_item_icon(iid, pygame.Rect(sr.x + 6, sr.y + 6, sr.w - 12, sr.h - 12))
                c_txt = font_xs.render(f"x{scnt}", True, (255, 255, 255))
                screen.blit(c_txt, (sr.right - c_txt.get_width() - 3, sr.bottom - c_txt.get_height() - 2))

            f_arrow = font_md.render("=>", True, (255, 152, 56) if can_smelt_sel else (120, 114, 114))
            screen.blit(f_arrow, f_arrow.get_rect(center=((fuel_r.right + out_r.x) // 2, in_r.centery)))

            s_btn_w = max(110, (bw - (out_r.right - bx) - 42) // 2)
            s_btn_h = max(40, min(52, cham_h - 32))
            if ui["is_vert"]:
                btn_y_f = cham_r.bottom - s_btn_h - 10
                half_fbw = (bw - 44) // 2
                sm1_r = pygame.Rect(bx + 16, btn_y_f, half_fbw, s_btn_h)
                sma_r = pygame.Rect(bx + 28 + half_fbw, btn_y_f, half_fbw, s_btn_h)
            else:
                btn_y_f = top_y + (cham_h - s_btn_h) // 2
                sm1_r = pygame.Rect(out_r.right + 18, btn_y_f, s_btn_w, s_btn_h)
                sma_r = pygame.Rect(sm1_r.right + 10, btn_y_f, s_btn_w, s_btn_h)
            ui["smelt_one"] = sm1_r
            ui["smelt_all"] = sma_r
            for sr, txt, en in (
                (sm1_r, f"SMELT x{s_out_cnt}", can_smelt_sel),
                (sma_r, f"SMELT ALL (x{max_smelt * s_out_cnt})" if can_smelt_sel else "SMELT ALL", can_smelt_sel),
            ):
                pygame.draw.rect(screen, (182, 88, 36) if en else (48, 42, 46), sr, border_radius=8)
                pygame.draw.rect(screen, (255, 214, 146) if en else (96, 86, 88), sr, 2 if en else 1, border_radius=8)
                tl = (font_xs if ui["is_vert"] else font_sm).render(txt, True, (255, 255, 255) if en else (142, 136, 140))
                screen.blit(tl, tl.get_rect(center=sr.center))

            smelt_btns = []
            list_y0 = cham_r.bottom + 10
            avail_sh = H - list_y0 - 12
            rh = max(40, min(54, (avail_sh - 7 * 6) // len(SMELT_RECIPES)))
            for ridx, (in_id, out_id, oc, label) in enumerate(SMELT_RECIPES):
                cr = pygame.Rect(bx, list_y0 + ridx * (rh + 6), bw, rh)
                has_in = player.creative or player.inv.count_of(in_id) > 0
                can = fuel_tot > 0 and has_in
                sel_s = (ridx == selected_smelt)
                bg = (148, 78, 38) if sel_s else ((86, 54, 34) if can else (44, 38, 42))
                bd = (255, 224, 96) if sel_s else ((220, 168, 108) if can else (96, 86, 88))
                pygame.draw.rect(screen, bg, cr, border_radius=8)
                pygame.draw.rect(screen, bd, cr, 2 if (sel_s or can) else 1, border_radius=8)
                isz = max(22, rh - 10)
                draw_item_icon(in_id, pygame.Rect(cr.x + 10, cr.y + (rh - isz) // 2, isz, isz))
                draw_item_icon(out_id, pygame.Rect(cr.right - isz - 10, cr.y + (rh - isz) // 2, isz, isz))
                rlbl = (font_xs if ui["is_vert"] else font_sm).render(label, True, (255, 250, 245))
                screen.blit(rlbl, rlbl.get_rect(center=cr.center))
                smelt_btns.append((ridx, cr))
            ui["smelt_btns"] = smelt_btns

        elif state == "CHEST":
            screen.blit(cache["ov_dark"], (0, 0))
            s_min = min(W, H)
            close_w = max(110, int(s_min * 0.22))
            close_h = max(44, int(s_min * 0.082))
            screen.blit(font_lg.render("CHEST", True, (245, 220, 110)), (16, 14))
            close_r = pygame.Rect(W - close_w - 16, 14, close_w, close_h)
            pygame.draw.rect(screen, (190, 68, 58), close_r, border_radius=8)
            pygame.draw.rect(screen, (255, 220, 215), close_r, 2, border_radius=8)
            clbl = font_sm.render("CLOSE", True, (255, 255, 255))
            screen.blit(clbl, clbl.get_rect(center=close_r.center))
            ui["inv_close"] = close_r

            y_start = 24 + close_h + 26
            screen.blit(font_xs.render("Tap Inventory -> Store | Tap Chest -> Take", True, (200, 210, 225)), (16, 24 + close_h))
            chest_store, chest_take = [], []
            row_h = max(40, int(H * 0.068))
            inv_entries = player.inv.list_by_category("all")
            for idx, (iid, cnt) in enumerate(inv_entries[:9]):
                r = pygame.Rect(16, y_start + idx * (row_h + 6), W // 2 - 24, row_h)
                if r.bottom > H - 10:
                    break
                pygame.draw.rect(screen, (48, 56, 70), r, border_radius=6)
                pygame.draw.rect(screen, (140, 155, 175), r, 1, border_radius=6)
                screen.blit(font_xs.render(f"{item_name(iid)[:10]} ({cnt}) ->", True, (240, 245, 255)), (r.x + 10, r.y + (row_h - font_xs.get_height()) // 2))
                chest_store.append((iid, r))
            ch_keys = [k for k, v in world.chest_storage.items() if v > 0]
            for idx, iid in enumerate(ch_keys[:9]):
                r = pygame.Rect(W // 2 + 8, y_start + idx * (row_h + 6), W // 2 - 24, row_h)
                if r.bottom > H - 10:
                    break
                pygame.draw.rect(screen, (82, 64, 42), r, border_radius=6)
                pygame.draw.rect(screen, (190, 150, 96), r, 1, border_radius=6)
                screen.blit(font_xs.render(f"<- {item_name(iid)[:10]} ({world.chest_storage[iid]})", True, (255, 236, 196)), (r.x + 10, r.y + (row_h - font_xs.get_height()) // 2))
                chest_take.append((iid, r))
            ui["chest_store"] = chest_store
            ui["chest_take"] = chest_take

        pygame.display.flip()

    save_game(world, player, time_of_day)
    pygame.quit()
