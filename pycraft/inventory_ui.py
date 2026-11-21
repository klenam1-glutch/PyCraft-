"""Touch-friendly Persistent Inventory Overlay & Shaped 3x3 Crafting Bench."""

from pycraft.blocks import (
    CRAFT_RECIPES, get_craft_meta, is_placeable, item_color, item_name, item_stat_tag,
)
from pycraft.constants import AIR


class InventoryUIHandler:
    __slots__ = (
        "active_tab", "collected_filter", "swap_pick",
        "craft_station", "craft_filter", "selected_recipe",
        "tab_rects", "filter_rects", "craft_filter_rects",
        "close_rect", "pin_rect",
        "prev_rect", "next_rect", "panel_rect",
        "item_rects", "slot_rects", "hotbar_rects", "craft_rects",
        "craft_one_rect", "craft_all_rect",
        "scroll_by_tab", "_max_scroll", "_visible_rows", "_row_step_px", "_drag_acc",
        "_ov_surf", "_ov_size",
    )

    TABS = ("blocks", "tools", "collected", "bag", "craft")
    TAB_LABELS = {
        "blocks": "Blocks",
        "tools": "Tools",
        "collected": "Collected",
        "bag": "Bag",
        "craft": "Craft",
    }
    COLLECTED_FILTERS = (("all", "All"), ("blocks", "Blocks"), ("tools", "Tools"))
    CRAFT_FILTERS = (
        ("all", "All"),
        ("ready", "Ready"),
        ("blocks", "Blocks"),
        ("tools", "Tools"),
        ("gear", "Gear"),
        ("utility", "Bench"),
    )

    def __init__(self):
        self.active_tab = "blocks"
        self.collected_filter = "all"
        self.craft_station = "hand"   # "hand" (2x2) or "table" (3x3 Crafting Table)
        self.craft_filter = "all"
        self.selected_recipe = 0
        self.swap_pick = None  # (group, index) when rearranging backpack/hotbar
        self.tab_rects = []
        self.filter_rects = []
        self.craft_filter_rects = []
        self.close_rect = None
        self.pin_rect = None
        self.prev_rect = None
        self.next_rect = None
        self.panel_rect = None
        self.item_rects = []
        self.slot_rects = []
        self.hotbar_rects = []
        self.craft_rects = []
        self.craft_one_rect = None
        self.craft_all_rect = None
        self.scroll_by_tab = {"blocks": 0, "tools": 0, "collected": 0, "craft": 0}
        self._max_scroll = 0
        self._visible_rows = 3
        self._row_step_px = 72
        self._drag_acc = 0.0
        self._ov_surf = None
        self._ov_size = None

    def reset_selection(self):
        self.swap_pick = None
        self._drag_acc = 0.0

    def scroll(self, delta_rows):
        if self.active_tab not in self.scroll_by_tab:
            return
        cur = self.scroll_by_tab[self.active_tab]
        self.scroll_by_tab[self.active_tab] = max(0, min(self._max_scroll, cur + delta_rows))

    def handle_drag(self, dy):
        if self.active_tab not in self.scroll_by_tab or self._row_step_px <= 0:
            return False
        self._drag_acc -= dy
        step = max(36, int(self._row_step_px * 0.65))
        moved = False
        while abs(self._drag_acc) >= step:
            if self._drag_acc > 0:
                self.scroll(1)
                self._drag_acc -= step
            else:
                self.scroll(-1)
                self._drag_acc += step
            moved = True
        return moved

    def _draw_icon(self, pygame, screen, assets, iid, rect):
        if iid == AIR:
            return
        icon = assets.get_icon(pygame, iid, rect.w)
        if icon is not None:
            screen.blit(icon, rect.topleft)
        else:
            tc, sc = item_color(iid)
            pygame.draw.rect(screen, sc, rect)
            pygame.draw.rect(screen, tc, (rect.x, rect.y, rect.w, max(4, rect.h // 3)))

    def _recipe_status(self, ridx, inventory):
        """Return (can_craft_now, has_materials, station_ok, max_batches, cat, needs_table, grid9)."""
        _res_id, _rcnt, reqs, _lbl = CRAFT_RECIPES[ridx]
        cat, needs_table, grid9 = get_craft_meta(ridx)
        station_ok = inventory.creative or (self.craft_station == "table") or (not needs_table)
        if inventory.creative:
            return True, True, True, 64, cat, needs_table, grid9
        max_batches = 64
        for rb, rc in reqs:
            have = inventory.count_of(rb)
            max_batches = min(max_batches, have // rc)
        has_materials = max_batches >= 1
        can_now = station_ok and has_materials
        return can_now, has_materials, station_ok, max_batches, cat, needs_table, grid9

    def _execute_craft(self, ridx, inventory, sound_bank, show_toast, craft_all=False):
        res_id, res_cnt, reqs, _lbl = CRAFT_RECIPES[ridx]
        can_now, has_mats, station_ok, max_batches, _cat, _nt, _g = self._recipe_status(ridx, inventory)
        if not station_ok:
            show_toast("Place & tap a Craft Table for 3x3 recipes!", 1.6)
            return False
        if not has_mats or not can_now:
            show_toast("Missing ingredients!", 1.2)
            return False
        batches = (16 if inventory.creative else max_batches) if craft_all else 1
        batches = max(1, batches)
        if not inventory.creative:
            for rb, rc in reqs:
                inventory.remove_item(rb, rc * batches)
        total_out = res_cnt * batches
        inventory.add_item(res_id, total_out)
        inventory.equip_to_hotbar(res_id)
        sound_bank.play("place")
        show_toast(f"Crafted {total_out}x {item_name(res_id)}!", 1.5)
        return True

    def render(self, pygame, screen, assets, inventory, fonts, width, height, is_vert=None):
        if is_vert is None:
            is_vert = height > width
        s = min(width, height)
        font_xs, font_sm, font_md, font_lg = fonts["xs"], fonts["sm"], fonts["md"], fonts["lg"]

        # Semi-transparent backdrop keeps the live 3D world visible behind the overlay
        if self._ov_surf is None or self._ov_size != (width, height):
            self._ov_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            self._ov_surf.fill((8, 12, 20, 178))
            self._ov_size = (width, height)
        screen.blit(self._ov_surf, (0, 0))

        outer_m = max(8, int(s * 0.018))
        panel = pygame.Rect(outer_m, outer_m, width - outer_m * 2, height - outer_m * 2)
        self.panel_rect = panel
        pygame.draw.rect(screen, (22, 28, 40), panel, border_radius=12)
        pygame.draw.rect(screen, (132, 148, 174), panel, 2, border_radius=12)

        pad = max(10, int(s * 0.020))
        inner_x = panel.x + pad
        inner_w = panel.w - pad * 2

        # Header Row
        btn_h = max(40, int(s * 0.072))
        close_w = max(88, int(s * 0.165))
        pin_w = max(92, int(s * 0.175))
        self.close_rect = pygame.Rect(panel.right - pad - close_w, panel.y + pad, close_w, btn_h)
        self.pin_rect = pygame.Rect(self.close_rect.x - 8 - pin_w, panel.y + pad, pin_w, btn_h)

        if self.active_tab == "craft":
            st_lbl = "CRAFTING TABLE (3x3)" if (self.craft_station == "table" or inventory.creative) else "POCKET CRAFTING (2x2)"
            title_txt = "CRAFTING" if is_vert else st_lbl
        else:
            title_txt = "INVENTORY" if is_vert else "INVENTORY OVERLAY"
        title_s = (font_md if is_vert else font_lg).render(title_txt, True, (245, 220, 110))
        screen.blit(title_s, (inner_x, panel.y + pad - 2))
        sub_txt = f"{inventory.collected_types_count()} types • {inventory.total_collected_count()} collected"
        screen.blit(font_xs.render(sub_txt, True, (168, 192, 222)), (inner_x, panel.y + pad + title_s.get_height() + 1))

        pin_on = inventory.hud_pinned
        pygame.draw.rect(screen, (48, 112, 168) if pin_on else (52, 60, 76), self.pin_rect, border_radius=8)
        pygame.draw.rect(screen, (190, 226, 255) if pin_on else (128, 142, 164), self.pin_rect, 2, border_radius=8)
        plbl = font_xs.render("HUD: PIN" if pin_on else "HUD: OFF", True, (255, 255, 255))
        screen.blit(plbl, plbl.get_rect(center=self.pin_rect.center))

        pygame.draw.rect(screen, (46, 142, 76), self.close_rect, border_radius=8)
        pygame.draw.rect(screen, (210, 250, 220), self.close_rect, 2, border_radius=8)
        clbl = font_sm.render("DONE", True, (255, 255, 255))
        screen.blit(clbl, clbl.get_rect(center=self.close_rect.center))

        # 5 Category Tabs
        tab_y = panel.y + pad + max(btn_h, title_s.get_height() + font_xs.get_height() + 4) + 8
        tab_h = max(40, int(s * 0.068))
        tab_gap = max(6, int(s * 0.011))
        tab_w = max(56, (inner_w - tab_gap * (len(self.TABS) - 1)) // len(self.TABS))
        self.tab_rects = []
        for idx, tab_id in enumerate(self.TABS):
            tr = pygame.Rect(inner_x + idx * (tab_w + tab_gap), tab_y, tab_w, tab_h)
            active = (tab_id == self.active_tab)
            bg = (52, 128, 78) if active else (38, 46, 60)
            bd = (240, 248, 255) if active else (112, 126, 148)
            pygame.draw.rect(screen, bg, tr, border_radius=8)
            pygame.draw.rect(screen, bd, tr, 2 if active else 1, border_radius=8)
            tf = font_xs if is_vert else font_sm
            tl = tf.render(self.TAB_LABELS[tab_id], True, (255, 255, 255))
            screen.blit(tl, tl.get_rect(center=tr.center))
            self.tab_rects.append((tab_id, tr))

        # Bottom Active Summary + 9-slot Hotbar Strip
        hb_gap = max(4, int(s * 0.009))
        hb_cell = max(38, min(62, (inner_w - hb_gap * 8) // 9))
        hb_y = panel.bottom - pad - hb_cell
        sel_bar_h = max(32, int(s * 0.052))
        sel_bar_y = hb_y - sel_bar_h - 6
        page_bar_h = max(36, int(s * 0.060))

        sel_rect = pygame.Rect(inner_x, sel_bar_y, inner_w, sel_bar_h)
        pygame.draw.rect(screen, (30, 38, 52), sel_rect, border_radius=8)
        pygame.draw.rect(screen, (96, 114, 142), sel_rect, 1, border_radius=8)
        sel_iid = inventory.selected_item
        if sel_iid != AIR:
            isz = max(22, sel_bar_h - 8)
            self._draw_icon(pygame, screen, assets, sel_iid, pygame.Rect(sel_rect.x + 8, sel_rect.y + (sel_bar_h - isz) // 2, isz, isz))
            tag = item_stat_tag(sel_iid)
            cnt_txt = "INF" if inventory.creative else f"Bag: {inventory.count_of(sel_iid)}"
            col_txt = f"Got: {inventory.collected_of(sel_iid)}"
            detail = f"Active: {item_name(sel_iid)}  [{tag}]  •  {cnt_txt}  •  {col_txt}"
            dlbl = font_xs.render(detail, True, (255, 232, 136))
            screen.blit(dlbl, (sel_rect.x + isz + 16, sel_rect.y + (sel_bar_h - dlbl.get_height()) // 2))
        else:
            dlbl = font_xs.render(f"Active Slot #{inventory.selected_slot + 1}: Empty — tap any item above to equip", True, (186, 200, 220))
            screen.blit(dlbl, (sel_rect.x + 12, sel_rect.y + (sel_bar_h - dlbl.get_height()) // 2))

        hb_x0 = panel.x + (panel.w - (hb_cell * 9 + hb_gap * 8)) // 2
        self.hotbar_rects = []
        for idx, slot in enumerate(inventory.hotbar):
            rect = pygame.Rect(hb_x0 + idx * (hb_cell + hb_gap), hb_y, hb_cell, hb_cell)
            picked = (self.active_tab == "bag" and self.swap_pick == ("hotbar", idx))
            active = (idx == inventory.selected_slot)
            pygame.draw.rect(screen, (52, 60, 78) if active else (38, 44, 58), rect, border_radius=6)
            bcol = (255, 224, 88) if (picked or active) else (126, 140, 162)
            pygame.draw.rect(screen, bcol, rect, 3 if (picked or active) else 1, border_radius=6)
            if not slot.is_empty():
                pin_in = max(4, hb_cell // 7)
                self._draw_icon(pygame, screen, assets, slot.item_id, pygame.Rect(rect.x + pin_in, rect.y + pin_in, hb_cell - pin_in * 2, hb_cell - pin_in * 2))
                if not inventory.creative and slot.count > 1:
                    cl = font_xs.render(str(slot.count), True, (255, 255, 255))
                    screen.blit(cl, (rect.right - cl.get_width() - 2, rect.bottom - cl.get_height() - 1))
            self.hotbar_rects.append((idx, rect))

        content_y = tab_y + tab_h + 10
        content_bottom = sel_bar_y - 8

        self.item_rects = []
        self.filter_rects = []
        self.craft_filter_rects = []
        self.slot_rects = []
        self.craft_rects = []
        self.craft_one_rect = None
        self.craft_all_rect = None
        self.prev_rect = None
        self.next_rect = None
        self._max_scroll = 0

        if self.active_tab in ("blocks", "tools", "collected"):
            if self.active_tab == "collected":
                f_h = max(34, int(s * 0.056))
                f_gap = 8
                f_w = min(130, (inner_w - f_gap * 2) // 3)
                for fidx, (fid, flabel) in enumerate(self.COLLECTED_FILTERS):
                    fr = pygame.Rect(inner_x + fidx * (f_w + f_gap), content_y, f_w, f_h)
                    fact = (self.collected_filter == fid)
                    pygame.draw.rect(screen, (62, 102, 148) if fact else (36, 44, 58), fr, border_radius=6)
                    pygame.draw.rect(screen, (215, 232, 255) if fact else (105, 118, 138), fr, 2 if fact else 1, border_radius=6)
                    fl = font_xs.render(flabel, True, (255, 255, 255))
                    screen.blit(fl, fl.get_rect(center=fr.center))
                    self.filter_rects.append((fid, fr))
                raw_entries = inventory.list_collected(self.collected_filter)
                grid_y = content_y + f_h + 8
                entries = raw_entries
            else:
                raw_entries = inventory.list_by_category(self.active_tab)
                entries = [(iid, cnt, inventory.collected_of(iid)) for iid, cnt in raw_entries]
                hint = (
                    "Tap any block to equip into active hotbar slot"
                    if self.active_tab == "blocks"
                    else "Tap any tool, weapon or gear to equip"
                )
                hint_lbl = font_xs.render(hint, True, (180, 198, 222))
                screen.blit(hint_lbl, (inner_x, content_y))
                grid_y = content_y + hint_lbl.get_height() + 6

            cols = 4 if is_vert else 7
            gap = max(7, int(s * 0.013))
            cell = max(58, min(108, (inner_w - gap * (cols - 1)) // cols))
            row_step = cell + gap
            self._row_step_px = row_step

            avail_h = content_bottom - grid_y
            total_rows = (len(entries) + cols - 1) // cols
            vis_rows_full = max(1, (avail_h + gap) // row_step)
            need_pager = total_rows > vis_rows_full
            if need_pager:
                avail_grid_h = avail_h - page_bar_h - 6
                vis_rows = max(1, (avail_grid_h + gap) // row_step)
            else:
                vis_rows = vis_rows_full
            self._visible_rows = vis_rows
            self._max_scroll = max(0, total_rows - vis_rows)
            scroll_r = max(0, min(self._max_scroll, self.scroll_by_tab.get(self.active_tab, 0)))
            self.scroll_by_tab[self.active_tab] = scroll_r

            start_idx = scroll_r * cols
            end_idx = min(len(entries), start_idx + vis_rows * cols)
            gx0 = panel.x + (panel.w - (cols * cell + (cols - 1) * gap)) // 2

            for pos_i, (iid, carried, col_total) in enumerate(entries[start_idx:end_idx]):
                c = pos_i % cols
                r_row = pos_i // cols
                rect = pygame.Rect(gx0 + c * (cell + gap), grid_y + r_row * row_step, cell, cell)
                equipped = (inventory.selected_item == iid)
                in_stock = inventory.creative or carried > 0
                if equipped:
                    bg_c, bd_c, bw = (56, 98, 68), (255, 224, 96), 3
                elif in_stock:
                    bg_c, bd_c, bw = (48, 58, 76), (138, 154, 178), 1
                else:
                    bg_c, bd_c, bw = (32, 36, 46), (82, 90, 106), 1
                pygame.draw.rect(screen, bg_c, rect, border_radius=8)
                pygame.draw.rect(screen, bd_c, rect, bw, border_radius=8)

                pad_in = max(8, cell // 6)
                icon_sz = max(24, cell - pad_in * 2 - 14)
                self._draw_icon(pygame, screen, assets, iid, pygame.Rect(rect.x + (cell - icon_sz) // 2, rect.y + 8, icon_sz, icon_sz))

                nm_col = (242, 246, 252) if in_stock else (142, 150, 166)
                nm = font_xs.render(item_name(iid)[:8], True, nm_col)
                screen.blit(nm, (rect.x + (cell - nm.get_width()) // 2, rect.bottom - nm.get_height() - 3))

                if not inventory.creative:
                    badge = str(carried) if self.active_tab != "collected" else f"{carried}/{col_total}"
                    bcol = (255, 220, 96) if in_stock else (142, 150, 166)
                    cl = font_xs.render(badge, True, bcol)
                    screen.blit(cl, (rect.x + 5, rect.y + 3))
                elif self.active_tab == "collected":
                    cl = font_xs.render(f"+{col_total}", True, (132, 232, 168))
                    screen.blit(cl, (rect.x + 5, rect.y + 3))

                self.item_rects.append((iid, rect))

            if not entries:
                empty_lbl = font_sm.render("No collected items in this filter yet.", True, (170, 182, 200))
                screen.blit(empty_lbl, empty_lbl.get_rect(center=(width // 2, grid_y + 70)))

            if need_pager:
                self._draw_pager(pygame, screen, font_xs, inner_x, inner_w, content_bottom - page_bar_h, page_bar_h, scroll_r, self._max_scroll)

        elif self.active_tab == "bag":
            screen.blit(font_xs.render("Tap two slots to swap or stack (Backpack -> Hotbar)", True, (186, 202, 224)), (inner_x, content_y))
            cols = 9
            gap = max(5, int(s * 0.01))
            cell = max(38, min(78, (inner_w - gap * (cols - 1)) // cols))
            avail_h = content_bottom - (content_y + font_xs.get_height() + 10)
            if cell * 3 + gap * 2 > avail_h:
                cell = max(34, (avail_h - gap * 2) // 3)
            gx0 = panel.x + (panel.w - (cols * cell + (cols - 1) * gap)) // 2
            by0 = content_y + font_xs.get_height() + 12

            for idx, slot in enumerate(inventory.backpack):
                c = idx % cols
                r_row = idx // cols
                rect = pygame.Rect(gx0 + c * (cell + gap), by0 + r_row * (cell + gap), cell, cell)
                picked = (self.swap_pick == ("backpack", idx))
                pygame.draw.rect(screen, (42, 48, 62), rect, border_radius=6)
                pygame.draw.rect(screen, (255, 220, 90) if picked else (130, 145, 165), rect, 3 if picked else 1, border_radius=6)
                if not slot.is_empty():
                    pad_in = max(4, cell // 7)
                    self._draw_icon(pygame, screen, assets, slot.item_id, pygame.Rect(rect.x + pad_in, rect.y + pad_in, cell - pad_in * 2, cell - pad_in * 2))
                    if not inventory.creative and slot.count > 1:
                        cl = font_xs.render(str(slot.count), True, (255, 255, 255))
                        screen.blit(cl, (rect.right - cl.get_width() - 3, rect.bottom - cl.get_height() - 2))
                self.slot_rects.append(("backpack", idx, rect))

        elif self.active_tab == "craft":
            self._render_craft_tab(
                pygame, screen, assets, inventory, fonts,
                inner_x, content_y, inner_w, content_bottom,
                is_vert, s, page_bar_h,
            )

    def _render_craft_tab(self, pygame, screen, assets, inventory, fonts,
                          inner_x, content_y, inner_w, content_bottom,
                          is_vert, s, page_bar_h):
        font_xs, font_sm, font_md = fonts["xs"], fonts["sm"], fonts["md"]

        # 1. Category Filter Strip + Craft Station Status Badge
        f_h = max(32, int(s * 0.052))
        f_gap = max(5, int(s * 0.008))
        n_flt = len(self.CRAFT_FILTERS)
        badge_w = 0 if is_vert else max(150, int(inner_w * 0.22))
        flt_area_w = inner_w - (badge_w + f_gap if badge_w else 0)
        f_w = (flt_area_w - f_gap * (n_flt - 1)) // n_flt
        for idx, (fid, flbl) in enumerate(self.CRAFT_FILTERS):
            fr = pygame.Rect(inner_x + idx * (f_w + f_gap), content_y, f_w, f_h)
            act = (self.craft_filter == fid)
            pygame.draw.rect(screen, (58, 112, 74) if act else (36, 44, 58), fr, border_radius=6)
            pygame.draw.rect(screen, (218, 244, 224) if act else (105, 118, 138), fr, 2 if act else 1, border_radius=6)
            tl = font_xs.render(flbl, True, (255, 255, 255))
            screen.blit(tl, tl.get_rect(center=fr.center))
            self.craft_filter_rects.append((fid, fr))

        is_table = (self.craft_station == "table" or inventory.creative)
        if badge_w > 0:
            br = pygame.Rect(inner_x + flt_area_w + f_gap, content_y, badge_w, f_h)
            pygame.draw.rect(screen, (44, 92, 62) if is_table else (88, 66, 36), br, border_radius=6)
            pygame.draw.rect(screen, (152, 224, 174) if is_table else (228, 186, 112), br, 1, border_radius=6)
            btxt = "3x3 Workbench" if is_table else "2x2 Hand Craft"
            bl = font_xs.render(btxt, True, (244, 250, 245))
            screen.blit(bl, bl.get_rect(center=br.center))

        body_y = content_y + f_h + 8
        body_h = content_bottom - body_y

        # Filter recipe indices
        filtered_indices = []
        for ridx in range(len(CRAFT_RECIPES)):
            can_now, has_mats, station_ok, max_b, cat, needs_tbl, grid9 = self._recipe_status(ridx, inventory)
            if self.craft_filter == "ready":
                if not can_now:
                    continue
            elif self.craft_filter != "all" and cat != self.craft_filter:
                continue
            filtered_indices.append(ridx)

        # Ensure selected recipe stays valid inside filtered view (or fallback to 0)
        if filtered_indices and self.selected_recipe not in filtered_indices:
            self.selected_recipe = filtered_indices[0]
        elif self.selected_recipe >= len(CRAFT_RECIPES):
            self.selected_recipe = 0

        # Split area: Shaped 3x3 Crafting Bench Card + Scrollable Recipe List
        if is_vert:
            bench_h = max(172, min(226, int(body_h * 0.44)))
            bench_rect = pygame.Rect(inner_x, body_y, inner_w, bench_h)
            list_rect = pygame.Rect(inner_x, body_y + bench_h + 8, inner_w, max(80, body_h - bench_h - 8))
        else:
            list_w = int(inner_w * 0.50)
            bench_w = inner_w - list_w - 10
            list_rect = pygame.Rect(inner_x, body_y, list_w, body_h)
            bench_rect = pygame.Rect(inner_x + list_w + 10, body_y, bench_w, body_h)

        # 2. Draw Shaped 3x3 Crafting Bench Card
        pygame.draw.rect(screen, (30, 36, 50), bench_rect, border_radius=10)
        pygame.draw.rect(screen, (112, 130, 158), bench_rect, 2, border_radius=10)
        self._draw_crafting_bench_card(pygame, screen, assets, inventory, fonts, bench_rect, is_table, is_vert)

        # 3. Draw Scrollable Recipe Picker List
        rh = max(42, int(s * 0.068))
        row_step = rh + 5
        self._row_step_px = row_step
        avail_list_h = list_rect.h
        total_rows = len(filtered_indices)
        vis_full = max(1, avail_list_h // row_step)
        need_pager = total_rows > vis_full
        vis_rows = max(1, (avail_list_h - page_bar_h - 4) // row_step) if need_pager else vis_full
        self._visible_rows = vis_rows
        self._max_scroll = max(0, total_rows - vis_rows)
        scroll_r = max(0, min(self._max_scroll, self.scroll_by_tab.get("craft", 0)))
        self.scroll_by_tab["craft"] = scroll_r

        start_i = scroll_r
        end_i = min(total_rows, start_i + vis_rows)
        for row_i, ridx in enumerate(filtered_indices[start_i:end_i]):
            res_id, rcnt, reqs, _lbl = CRAFT_RECIPES[ridx]
            can_now, has_mats, station_ok, max_b, _cat, needs_tbl, _g9 = self._recipe_status(ridx, inventory)
            cr = pygame.Rect(list_rect.x, list_rect.y + row_i * row_step, list_rect.w, rh)
            is_sel = (ridx == self.selected_recipe)

            if is_sel and can_now:
                bg, bd, bw = (52, 108, 72), (255, 224, 96), 2
            elif is_sel:
                bg, bd, bw = (56, 64, 84), (255, 224, 96), 2
            elif can_now:
                bg, bd, bw = (42, 82, 56), (132, 198, 152), 1
            elif has_mats and not station_ok:
                bg, bd, bw = (78, 62, 36), (196, 158, 92), 1
            else:
                bg, bd, bw = (38, 42, 54), (86, 94, 110), 1

            pygame.draw.rect(screen, bg, cr, border_radius=8)
            pygame.draw.rect(screen, bd, cr, bw, border_radius=8)

            isz = max(24, rh - 12)
            self._draw_icon(pygame, screen, assets, res_id, pygame.Rect(cr.x + 8, cr.y + (rh - isz) // 2, isz, isz))

            title_str = f"{rcnt}x {item_name(res_id)}" if rcnt > 1 else item_name(res_id)
            tl = (font_xs if is_vert else font_sm).render(title_str, True, (246, 250, 255) if (has_mats or is_sel) else (164, 174, 190))
            screen.blit(tl, (cr.x + isz + 14, cr.y + 4))

            # Compact ingredient requirement subtitle
            req_parts = []
            for rb, rc in reqs[:2]:
                have_n = inventory.count_of(rb)
                req_parts.append(f"{item_name(rb)[:7]} {have_n if not inventory.creative else rc}/{rc}")
            req_str = ("Need 3x3 Table • " if (needs_tbl and not station_ok) else "") + " + ".join(req_parts)
            sub_col = (242, 198, 106) if (needs_tbl and not station_ok) else ((154, 228, 172) if can_now else (160, 168, 184))
            sl = font_xs.render(req_str, True, sub_col)
            screen.blit(sl, (cr.x + isz + 14, cr.bottom - sl.get_height() - 4))

            self.craft_rects.append((ridx, cr))

        if not filtered_indices:
            el = font_sm.render("No recipes match this filter yet.", True, (170, 182, 200))
            screen.blit(el, el.get_rect(center=list_rect.center))

        if need_pager:
            self._draw_pager(
                pygame, screen, font_xs,
                list_rect.x, list_rect.w, list_rect.bottom - page_bar_h, page_bar_h,
                scroll_r, self._max_scroll,
            )

    def _draw_crafting_bench_card(self, pygame, screen, assets, inventory, fonts, rect, is_table, is_vert):
        font_xs, font_sm, font_md = fonts["xs"], fonts["sm"], fonts["md"]
        ridx = self.selected_recipe
        res_id, rcnt, reqs, _lbl = CRAFT_RECIPES[ridx]
        can_now, has_mats, station_ok, max_b, _cat, needs_tbl, grid9 = self._recipe_status(ridx, inventory)

        pad = 10
        x0 = rect.x + pad
        y0 = rect.y + pad

        # Title of selected recipe
        hdr_txt = f"{rcnt}x {item_name(res_id)}" if rcnt > 1 else item_name(res_id)
        hdr = (font_sm if is_vert else font_md).render(hdr_txt, True, (255, 232, 132))
        screen.blit(hdr, (x0, y0))

        mode_txt = "3x3 Craft Table" if needs_tbl else "2x2 Hand Craft"
        mode_col = (144, 232, 168) if station_ok else (246, 180, 92)
        mlbl = font_xs.render(mode_txt, True, mode_col)
        screen.blit(mlbl, (rect.right - mlbl.get_width() - pad, y0 + 2))

        grid_y = y0 + hdr.get_height() + 8
        btn_h = max(36, min(46, int(rect.h * 0.22)))
        btn_y = rect.bottom - pad - btn_h

        # Compute square 3x3 crafting grid cell size
        avail_grid_h = btn_y - grid_y - (42 if not is_vert else 28)
        if is_vert:
            cell = max(26, min(38, avail_grid_h // 3))
        else:
            cell = max(32, min(58, avail_grid_h // 3))
        g_gap = 4

        # Draw 3x3 Crafting Matrix with actual PNG ingredient sprites
        for gi, giid in enumerate(grid9):
            gc = gi % 3
            gr = gi // 3
            cx = x0 + gc * (cell + g_gap)
            cy = grid_y + gr * (cell + g_gap)
            cr = pygame.Rect(cx, cy, cell, cell)
            locked_cell = (not is_table) and (gc == 2 or gr == 2)
            if giid != AIR:
                cbg = (52, 62, 80) if station_ok else (68, 52, 42)
                cbd = (164, 186, 214) if station_ok else (212, 154, 92)
            elif locked_cell:
                cbg, cbd = (22, 26, 34), (58, 64, 78)
            else:
                cbg, cbd = (36, 42, 56), (92, 106, 128)
            pygame.draw.rect(screen, cbg, cr, border_radius=5)
            pygame.draw.rect(screen, cbd, cr, 1, border_radius=5)
            if giid != AIR:
                in_p = max(3, cell // 7)
                self._draw_icon(pygame, screen, assets, giid, pygame.Rect(cr.x + in_p, cr.y + in_p, cell - in_p * 2, cell - in_p * 2))

        matrix_w = cell * 3 + g_gap * 2
        matrix_mid_y = grid_y + (matrix_w // 2)

        # Arrow + Large Output Slot
        arr_x = x0 + matrix_w + 10
        albl = font_md.render("->", True, (218, 228, 244))
        screen.blit(albl, (arr_x, matrix_mid_y - albl.get_height() // 2))

        out_sz = max(42, min(68, int(cell * 1.45)))
        out_x = arr_x + albl.get_width() + 10
        out_r = pygame.Rect(out_x, matrix_mid_y - out_sz // 2, out_sz, out_sz)
        pygame.draw.rect(screen, (52, 92, 64) if can_now else (44, 48, 62), out_r, border_radius=8)
        pygame.draw.rect(screen, (255, 224, 96) if can_now else (130, 144, 168), out_r, 2, border_radius=8)
        in_op = max(5, out_sz // 7)
        self._draw_icon(pygame, screen, assets, res_id, pygame.Rect(out_r.x + in_op, out_r.y + in_op, out_sz - in_op * 2, out_sz - in_op * 2))
        if rcnt > 1:
            cl = font_sm.render(f"x{rcnt}", True, (255, 255, 255))
            screen.blit(cl, (out_r.right - cl.get_width() - 3, out_r.bottom - cl.get_height() - 2))

        # Ingredient Counts List to the right of Output (or below grid on narrow portrait)
        req_y = grid_y + matrix_w + 6 if is_vert else grid_y
        req_x = x0 if is_vert else (out_r.right + 12)
        for ri, (rb, rc) in enumerate(reqs):
            have = inventory.count_of(rb)
            ok = inventory.creative or have >= rc
            rc_col = (138, 238, 168) if ok else (244, 124, 124)
            txt = f"{item_name(rb)[:11]}: {rc if inventory.creative else have}/{rc}"
            rl = font_xs.render(txt, True, rc_col)
            if is_vert:
                # Arrange side-by-side in portrait so it fits above buttons cleanly
                screen.blit(rl, (req_x + ri * (rect.w // 2 - 12), req_y))
            else:
                screen.blit(rl, (req_x, req_y + ri * (rl.get_height() + 4)))

        if not station_ok:
            warn = font_xs.render("Tap a placed Craft Table for 3x3!", True, (248, 196, 98))
            screen.blit(warn, (x0, btn_y - warn.get_height() - 4))

        # Bottom Action Buttons: CRAFT x1 and CRAFT MAX
        b_gap = 8
        half_bw = (rect.w - pad * 2 - b_gap) // 2
        self.craft_one_rect = pygame.Rect(x0, btn_y, half_bw, btn_h)
        self.craft_all_rect = pygame.Rect(x0 + half_bw + b_gap, btn_y, half_bw, btn_h)

        c1_bg = (48, 138, 76) if can_now else (44, 48, 60)
        c1_bd = (196, 246, 208) if can_now else (92, 102, 118)
        pygame.draw.rect(screen, c1_bg, self.craft_one_rect, border_radius=8)
        pygame.draw.rect(screen, c1_bd, self.craft_one_rect, 2 if can_now else 1, border_radius=8)
        t1 = font_sm.render(f"CRAFT x{rcnt}", True, (255, 255, 255) if can_now else (142, 150, 166))
        screen.blit(t1, t1.get_rect(center=self.craft_one_rect.center))

        max_out = (rcnt * 16) if inventory.creative else (rcnt * max_b)
        can_multi = can_now and max_b >= 1
        ca_bg = (52, 108, 168) if can_multi else (44, 48, 60)
        ca_bd = (188, 224, 255) if can_multi else (92, 102, 118)
        pygame.draw.rect(screen, ca_bg, self.craft_all_rect, border_radius=8)
        pygame.draw.rect(screen, ca_bd, self.craft_all_rect, 2 if can_multi else 1, border_radius=8)
        max_lbl = f"CRAFT ALL (x{max_out})" if can_multi else "CRAFT ALL"
        t2 = (font_xs if is_vert else font_sm).render(max_lbl, True, (255, 255, 255) if can_multi else (142, 150, 166))
        screen.blit(t2, t2.get_rect(center=self.craft_all_rect.center))

    def _draw_pager(self, pygame, screen, font_xs, x0, width, y0, h, scroll_r, max_scroll):
        bw = min(130, width // 3)
        self.prev_rect = pygame.Rect(x0, y0, bw, h)
        self.next_rect = pygame.Rect(x0 + width - bw, y0, bw, h)
        can_prev = scroll_r > 0
        can_next = scroll_r < max_scroll
        for rect, lbl_txt, enabled in (
            (self.prev_rect, "< PREV", can_prev),
            (self.next_rect, "NEXT >", can_next),
        ):
            pygame.draw.rect(screen, (52, 68, 92) if enabled else (32, 36, 46), rect, border_radius=8)
            pygame.draw.rect(screen, (185, 206, 232) if enabled else (80, 90, 108), rect, 2 if enabled else 1, border_radius=8)
            t = font_xs.render(lbl_txt, True, (255, 255, 255) if enabled else (130, 140, 156))
            screen.blit(t, t.get_rect(center=rect.center))
        info = font_xs.render(f"Page {scroll_r + 1}/{max_scroll + 1}", True, (186, 204, 228))
        screen.blit(info, info.get_rect(center=(x0 + width // 2, y0 + h // 2)))

    def handle_tap(self, px, py, inventory, sound_bank, show_toast):
        if self.panel_rect and not self.panel_rect.collidepoint(px, py):
            self.reset_selection()
            return "close"

        if self.close_rect and self.close_rect.collidepoint(px, py):
            self.reset_selection()
            return "close"

        if self.pin_rect and self.pin_rect.collidepoint(px, py):
            inventory.hud_pinned = not inventory.hud_pinned
            sound_bank.play("step", 0.4)
            show_toast("Persistent HUD Overlay: " + ("PINNED" if inventory.hud_pinned else "HIDDEN"), 1.5)
            return "stay"

        for tab_id, rect in self.tab_rects:
            if rect.collidepoint(px, py):
                self.active_tab = tab_id
                inventory.ui_tab = tab_id
                self.reset_selection()
                sound_bank.play("step", 0.35)
                return "stay"

        for fid, rect in self.filter_rects:
            if rect.collidepoint(px, py):
                self.collected_filter = fid
                self.scroll_by_tab["collected"] = 0
                sound_bank.play("step", 0.35)
                return "stay"

        for fid, rect in self.craft_filter_rects:
            if rect.collidepoint(px, py):
                self.craft_filter = fid
                self.scroll_by_tab["craft"] = 0
                sound_bank.play("step", 0.35)
                return "stay"

        if self.prev_rect and self.prev_rect.collidepoint(px, py):
            self.scroll(-max(1, self._visible_rows - 1))
            sound_bank.play("step", 0.3)
            return "stay"
        if self.next_rect and self.next_rect.collidepoint(px, py):
            self.scroll(max(1, self._visible_rows - 1))
            sound_bank.play("step", 0.3)
            return "stay"

        for idx, rect in self.hotbar_rects:
            if rect.collidepoint(px, py):
                if self.active_tab == "bag":
                    if self.swap_pick is None:
                        self.swap_pick = ("hotbar", idx)
                        inventory.select_slot(idx)
                    else:
                        src_g, src_i = self.swap_pick
                        inventory.swap_slots(src_g, src_i, "hotbar", idx)
                        inventory.select_slot(idx)
                        self.swap_pick = None
                        sound_bank.play("place")
                else:
                    inventory.select_slot(idx)
                    sound_bank.play("step", 0.35)
                    show_toast(f"Slot {idx + 1}: {item_name(inventory.selected_item)}", 1.0)
                return "stay"

        for iid, rect in self.item_rects:
            if rect.collidepoint(px, py):
                if inventory.selected_item == iid:
                    self.reset_selection()
                    return "close"
                if inventory.equip_to_hotbar(iid):
                    kind_lbl = "block" if is_placeable(iid) else "tool/item"
                    show_toast(f"Active {kind_lbl}: {item_name(iid)} (Tap again or DONE)", 1.4)
                    sound_bank.play("place")
                    return "stay"
                col_n = inventory.collected_of(iid)
                show_toast(f"None left in bag (Collected total: {col_n})", 1.4)
                return "stay"

        for group, idx, rect in self.slot_rects:
            if rect.collidepoint(px, py):
                if self.swap_pick is None:
                    self.swap_pick = (group, idx)
                else:
                    src_g, src_i = self.swap_pick
                    inventory.swap_slots(src_g, src_i, group, idx)
                    self.swap_pick = None
                    sound_bank.play("place")
                return "stay"

        if self.craft_one_rect and self.craft_one_rect.collidepoint(px, py):
            self._execute_craft(self.selected_recipe, inventory, sound_bank, show_toast, craft_all=False)
            return "stay"

        if self.craft_all_rect and self.craft_all_rect.collidepoint(px, py):
            self._execute_craft(self.selected_recipe, inventory, sound_bank, show_toast, craft_all=True)
            return "stay"

        for ridx, rect in self.craft_rects:
            if rect.collidepoint(px, py):
                if self.selected_recipe == ridx:
                    # Tapping an already-selected recipe quick-crafts 1x
                    self._execute_craft(ridx, inventory, sound_bank, show_toast, craft_all=False)
                else:
                    self.selected_recipe = ridx
                    sound_bank.play("step", 0.3)
                return "stay"
        return "stay"
