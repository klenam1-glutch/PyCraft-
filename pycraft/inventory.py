"""Structured Inventory data model: 9-slot hotbar, 27-slot backpack, persistent collection tracking & quick switching."""

from pycraft.blocks import ALL_CREATIVE_ITEMS, BLOCKS, ITEMS, is_placeable, is_tool
from pycraft.constants import (
    AIR, COBBLE, CRAFT_TABLE, DIRT, GRASS, ITEM_APPLE, ITEM_ARROW, ITEM_BOW,
    ITEM_BUCKET_EMPTY, ITEM_BUCKET_LAVA, ITEM_BUCKET_WATER, ITEM_FLINT_STEEL, PLANKS,
    TOOL_WOOD_AXE, TOOL_WOOD_PICK, TOOL_WOOD_SHOVEL, TOOL_WOOD_SWORD, TORCH,
)


def max_stack_for(item_id):
    if item_id in ITEMS:
        meta = ITEMS[item_id]
        if any(k in meta for k in ("pick_speed", "axe_speed", "shovel_speed", "damage", "armor")) or item_id in (
            ITEM_BUCKET_EMPTY, ITEM_BUCKET_WATER, ITEM_BUCKET_LAVA, ITEM_FLINT_STEEL
        ):
            return 1
    return 64


class InventorySlot:
    __slots__ = ("item_id", "count")

    def __init__(self, item_id=AIR, count=0):
        self.item_id = item_id
        self.count = count if item_id != AIR else 0

    def is_empty(self):
        return self.item_id == AIR or self.count <= 0

    def clear(self):
        self.item_id = AIR
        self.count = 0

    def copy(self):
        return InventorySlot(self.item_id, self.count)

    def to_list(self):
        return [self.item_id, self.count]

    @classmethod
    def from_list(cls, pair):
        if not pair or len(pair) < 2:
            return cls()
        iid, cnt = int(pair[0]), int(pair[1])
        return cls(iid, cnt) if iid != AIR and cnt > 0 else cls()


class Inventory:
    __slots__ = ("creative", "selected_slot", "hotbar", "backpack", "collected", "ui_tab", "hud_pinned")
    HOTBAR_SIZE = 9
    BACKPACK_SIZE = 27

    def __init__(self, creative=False):
        self.creative = creative
        self.selected_slot = 0
        self.hotbar = [InventorySlot() for _ in range(self.HOTBAR_SIZE)]
        self.backpack = [InventorySlot() for _ in range(self.BACKPACK_SIZE)]
        self.collected = {}
        self.ui_tab = "blocks"
        self.hud_pinned = True
        self._seed_defaults()

    def _seed_defaults(self):
        defaults = [
            (TOOL_WOOD_PICK, 1),
            (TOOL_WOOD_SWORD, 1),
            (GRASS, 24),
            (DIRT, 24),
            (COBBLE, 16),
            (PLANKS, 24),
            (CRAFT_TABLE, 1),
            (TORCH, 8),
            (ITEM_APPLE, 4),
        ]
        for idx, (iid, cnt) in enumerate(defaults):
            self.hotbar[idx] = InventorySlot(iid, cnt)
        self.backpack[0] = InventorySlot(TOOL_WOOD_AXE, 1)
        self.backpack[1] = InventorySlot(TOOL_WOOD_SHOVEL, 1)
        self.backpack[2] = InventorySlot(ITEM_BOW, 1)
        self.backpack[3] = InventorySlot(ITEM_ARROW, 12)
        self._sync_initial_collected()

    def _sync_initial_collected(self):
        for s in self.hotbar + self.backpack:
            if not s.is_empty():
                self.collected[s.item_id] = max(self.collected.get(s.item_id, 0), s.count)

    @property
    def selected_item(self):
        slot = self.hotbar[self.selected_slot]
        return AIR if slot.is_empty() else slot.item_id

    @property
    def selected_count(self):
        return self.hotbar[self.selected_slot].count

    def select_slot(self, idx):
        self.selected_slot = max(0, min(self.HOTBAR_SIZE - 1, int(idx)))

    def cycle_slot(self, delta):
        self.selected_slot = (self.selected_slot + delta) % self.HOTBAR_SIZE

    def get_group(self, group_name):
        return self.hotbar if group_name == "hotbar" else self.backpack

    def count_of(self, item_id):
        if item_id == AIR:
            return 0
        total = 0
        for s in self.hotbar:
            if s.item_id == item_id:
                total += s.count
        for s in self.backpack:
            if s.item_id == item_id:
                total += s.count
        return total

    def collected_of(self, item_id):
        if item_id == AIR:
            return 0
        return self.collected.get(item_id, 0)

    def total_collected_count(self):
        return sum(self.collected.values())

    def collected_types_count(self):
        return len(self.collected)

    def record_collected(self, item_id, count=1):
        if item_id == AIR or count <= 0:
            return
        self.collected[item_id] = self.collected.get(item_id, 0) + count

    def add_item(self, item_id, count=1, record_collected=True):
        if item_id == AIR or count <= 0:
            return 0
        if record_collected:
            self.record_collected(item_id, count)
        rem = count
        mstack = max_stack_for(item_id)

        # 1. Stack into existing matching slots (hotbar first, then backpack)
        for group in (self.hotbar, self.backpack):
            for s in group:
                if s.item_id == item_id and s.count < mstack:
                    space = mstack - s.count
                    take = min(rem, space)
                    s.count += take
                    rem -= take
                    if rem == 0:
                        return 0

        # 2. Fill empty slots (hotbar first, then backpack)
        for group in (self.hotbar, self.backpack):
            for s in group:
                if s.is_empty():
                    take = min(rem, mstack)
                    s.item_id = item_id
                    s.count = take
                    rem -= take
                    if rem == 0:
                        return 0
        return rem

    def remove_item(self, item_id, count=1):
        if self.creative:
            return True
        if self.count_of(item_id) < count:
            return False
        rem = count
        for group in (self.backpack, self.hotbar):
            for s in group:
                if s.item_id == item_id and s.count > 0:
                    take = min(rem, s.count)
                    s.count -= take
                    rem -= take
                    if s.count <= 0:
                        s.clear()
                    if rem == 0:
                        return True
        return True

    def consume_selected(self, count=1):
        if self.creative:
            return True
        slot = self.hotbar[self.selected_slot]
        if slot.is_empty() or slot.count < count:
            return False
        slot.count -= count
        if slot.count <= 0:
            slot.clear()
        return True

    def swap_slots(self, src_group, src_idx, dst_group, dst_idx):
        g_src = self.get_group(src_group)
        g_dst = self.get_group(dst_group)
        if not (0 <= src_idx < len(g_src) and 0 <= dst_idx < len(g_dst)):
            return
        if src_group == dst_group and src_idx == dst_idx:
            return
        a = g_src[src_idx]
        b = g_dst[dst_idx]
        if not a.is_empty() and a.item_id == b.item_id:
            mstack = max_stack_for(a.item_id)
            if b.count < mstack:
                move = min(a.count, mstack - b.count)
                b.count += move
                a.count -= move
                if a.count <= 0:
                    a.clear()
                return
        g_src[src_idx], g_dst[dst_idx] = b, a

    def equip_to_hotbar(self, item_id, slot_idx=None):
        """Switches/equips a block or tool/item into the active hotbar slot for placement or use."""
        if item_id == AIR:
            return False
        if slot_idx is None:
            slot_idx = self.selected_slot

        if self.creative:
            self.hotbar[slot_idx] = InventorySlot(item_id, max_stack_for(item_id))
            self.selected_slot = slot_idx
            return True

        # If already in hotbar, select that slot directly
        for idx, s in enumerate(self.hotbar):
            if s.item_id == item_id and s.count > 0:
                self.selected_slot = idx
                return True

        # Otherwise find in backpack and swap into target hotbar slot
        for b_idx, s in enumerate(self.backpack):
            if s.item_id == item_id and s.count > 0:
                self.swap_slots("backpack", b_idx, "hotbar", slot_idx)
                self.selected_slot = slot_idx
                return True
        return False

    def list_by_category(self, category):
        """Returns list of (item_id, count) filtered by 'blocks', 'tools', 'items', or 'all'."""
        if self.creative:
            pool = ALL_CREATIVE_ITEMS
            if category == "blocks":
                return [(iid, 64) for iid in pool if is_placeable(iid)]
            if category == "tools":
                return [(iid, max_stack_for(iid)) for iid in pool if is_tool(iid)]
            if category == "items":
                return [(iid, 1 if max_stack_for(iid) == 1 else 64) for iid in pool if not is_placeable(iid)]
            return [(iid, max_stack_for(iid)) for iid in pool]

        counts = {}
        order = []
        for s in self.hotbar + self.backpack:
            if not s.is_empty():
                if s.item_id not in counts:
                    counts[s.item_id] = 0
                    order.append(s.item_id)
                counts[s.item_id] += s.count
        if category == "blocks":
            return [(iid, counts[iid]) for iid in order if is_placeable(iid)]
        if category == "tools":
            return [(iid, counts[iid]) for iid in order if is_tool(iid)]
        if category == "items":
            return [(iid, counts[iid]) for iid in order if not is_placeable(iid)]
        return [(iid, counts[iid]) for iid in order]

    def list_collected(self, filter_kind="all"):
        """Returns list of (item_id, carried_count, collected_total) across all discovered/collected blocks & tools."""
        carried = {}
        for s in self.hotbar + self.backpack:
            if not s.is_empty():
                carried[s.item_id] = carried.get(s.item_id, 0) + s.count

        all_ids = set(self.collected.keys()) | set(carried.keys())
        if filter_kind == "blocks":
            all_ids = [iid for iid in all_ids if is_placeable(iid)]
        elif filter_kind == "tools":
            all_ids = [iid for iid in all_ids if is_tool(iid)]
        else:
            all_ids = list(all_ids)

        all_ids.sort(key=lambda iid: (0 if carried.get(iid, 0) > 0 else 1, -self.collected.get(iid, 0), iid))
        return [(iid, carried.get(iid, 0), max(self.collected.get(iid, 0), carried.get(iid, 0))) for iid in all_ids]

    def quick_switch_items(self, max_tools=3, max_blocks=3):
        """Returns up to max_tools + max_blocks carried items for the pinned quick-switch HUD overlay."""
        tools = []
        blocks = []
        seen = set()
        for s in self.hotbar + self.backpack:
            if s.is_empty() or s.item_id in seen:
                continue
            seen.add(s.item_id)
            if is_tool(s.item_id) and len(tools) < max_tools:
                tools.append((s.item_id, self.count_of(s.item_id)))
            elif is_placeable(s.item_id) and len(blocks) < max_blocks:
                blocks.append((s.item_id, self.count_of(s.item_id)))
            if len(tools) >= max_tools and len(blocks) >= max_blocks:
                break
        return tools + blocks

    def to_dict(self):
        return {
            "selected_slot": self.selected_slot,
            "hotbar": [s.to_list() for s in self.hotbar],
            "backpack": [s.to_list() for s in self.backpack],
            "collected": {str(k): int(v) for k, v in self.collected.items() if v > 0},
            "ui_tab": self.ui_tab,
            "hud_pinned": bool(self.hud_pinned),
        }

    @classmethod
    def from_dict(cls, data, creative=False):
        inv = cls(creative=creative)
        if not isinstance(data, dict):
            return inv
        if "hotbar" in data and isinstance(data["hotbar"], list) and data["hotbar"] and isinstance(data["hotbar"][0], list):
            for i in range(min(cls.HOTBAR_SIZE, len(data["hotbar"]))):
                inv.hotbar[i] = InventorySlot.from_list(data["hotbar"][i])
            bp = data.get("backpack", [])
            for i in range(min(cls.BACKPACK_SIZE, len(bp))):
                inv.backpack[i] = InventorySlot.from_list(bp[i])
            inv.select_slot(data.get("selected_slot", 0))
            inv.collected = {}
            raw_col = data.get("collected", {})
            if isinstance(raw_col, dict):
                for k, v in raw_col.items():
                    try:
                        iid, cnt = int(k), int(v)
                        if iid != AIR and cnt > 0:
                            inv.collected[iid] = cnt
                    except (TypeError, ValueError):
                        pass
            inv._sync_initial_collected()
            tab = data.get("ui_tab", "blocks")
            inv.ui_tab = tab if tab in ("blocks", "tools", "collected", "bag", "craft") else "blocks"
            inv.hud_pinned = bool(data.get("hud_pinned", True))
            return inv

        # Legacy save compatibility
        inv.hotbar = [InventorySlot() for _ in range(cls.HOTBAR_SIZE)]
        inv.backpack = [InventorySlot() for _ in range(cls.BACKPACK_SIZE)]
        inv.collected = {}
        legacy_hb = data.get("hotbar", [])
        legacy_counts = data.get("inventory", {})
        placed = set()
        for i, iid in enumerate(legacy_hb[:cls.HOTBAR_SIZE]):
            cnt = int(legacy_counts.get(str(iid), 16))
            if cnt > 0:
                inv.hotbar[i] = InventorySlot(int(iid), cnt)
                placed.add(int(iid))
        for k, v in legacy_counts.items():
            iid, cnt = int(k), int(v)
            if iid not in placed and cnt > 0:
                inv.add_item(iid, cnt)
        inv._sync_initial_collected()
        inv.select_slot(data.get("selected_slot", 0))
        return inv
