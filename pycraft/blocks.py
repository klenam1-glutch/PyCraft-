"""Full Minecraft block definitions, tool/weapon/armor/food metadata, textures, and crafting recipes."""

from pycraft.constants import (
    AIR, ARMOR_DIAMOND, ARMOR_GOLD, ARMOR_IRON, BED, BEDROCK,
    BIRCH_LEAVES, BIRCH_WOOD, BOOKSHELF, BRICK, CACTUS, CHEST, CLAY,
    COAL_ORE, COBBLE, CRAFT_TABLE, DIAMOND_BLOCK, DIAMOND_ORE, DIRT, DOOR_CLOSED, DOOR_OPEN,
    EMERALD_BLOCK, EMERALD_ORE, FLOWER_RED, FLOWER_YELLOW, FURNACE,
    GLASS, GLOWSTONE, GOLD_BLOCK, GOLD_ORE, GRASS, GRAVEL, ICE,
    IRON_BLOCK, IRON_ORE, ITEM_APPLE, ITEM_ARROW, ITEM_BOW, ITEM_BREAD,
    ITEM_BUCKET_EMPTY, ITEM_BUCKET_LAVA, ITEM_BUCKET_WATER, ITEM_COAL,
    ITEM_DIAMOND, ITEM_EMERALD, ITEM_FLINT, ITEM_FLINT_STEEL,
    ITEM_GOLD_INGOT, ITEM_IRON_INGOT, ITEM_RAW_MEAT, ITEM_STEAK, ITEM_STICK,
    LADDER, LAVA, LEAVES, MOSSY_COBBLE, NETHERRACK, OBSIDIAN,
    PINE_LEAVES, PINE_WOOD, PLANKS, PORTAL, RED_SANDSTONE,
    SAND, SANDSTONE, SNOW, SNOW_BLOCK, STONE, TERRACOTTA, TNT,
    TOOL_DIAMOND_AXE, TOOL_DIAMOND_PICK, TOOL_DIAMOND_SHOVEL, TOOL_DIAMOND_SWORD,
    TOOL_GOLD_PICK, TOOL_GOLD_SWORD,
    TOOL_IRON_AXE, TOOL_IRON_PICK, TOOL_IRON_SHOVEL, TOOL_IRON_SWORD,
    TOOL_STONE_AXE, TOOL_STONE_PICK, TOOL_STONE_SHOVEL, TOOL_STONE_SWORD,
    TOOL_WOOD_AXE, TOOL_WOOD_PICK, TOOL_WOOD_SHOVEL, TOOL_WOOD_SWORD,
    TORCH, WATER, WOOD, WOOL_BLUE, WOOL_GREEN, WOOL_RED, WOOL_WHITE, WOOL_YELLOW,
)

BLOCKS = {
    GRASS: {"name": "Grass", "top": (88, 178, 66), "side": (132, 94, 66), "bottom": (118, 82, 56), "solid": True, "transparent": False, "emissive": False, "break_time": 0.40, "drop": DIRT, "shovel": True, "tex_top": "grass_top.png", "tex_side": "grass_side.png", "tex_bottom": "dirt.png", "sound": "break"},
    DIRT: {"name": "Dirt", "top": (132, 94, 66), "side": (122, 86, 58), "bottom": (108, 74, 50), "solid": True, "transparent": False, "emissive": False, "break_time": 0.35, "drop": DIRT, "shovel": True, "tex": "dirt.png", "sound": "break"},
    STONE: {"name": "Stone", "top": (130, 132, 136), "side": (120, 122, 126), "bottom": (106, 108, 112), "solid": True, "transparent": False, "emissive": False, "break_time": 1.10, "drop": COBBLE, "pick": True, "tex": "stone.png", "sound": "break_stone"},
    COBBLE: {"name": "Cobble", "top": (110, 112, 116), "side": (100, 102, 106), "bottom": (90, 92, 96), "solid": True, "transparent": False, "emissive": False, "break_time": 1.00, "drop": COBBLE, "pick": True, "tex": "cobble.png", "sound": "break_stone"},
    WOOD: {"name": "Oak Log", "top": (176, 142, 92), "side": (102, 72, 42), "bottom": (160, 126, 80), "solid": True, "transparent": False, "emissive": False, "break_time": 0.65, "drop": WOOD, "axe": True, "tex_top": "wood_top.png", "tex_side": "wood_side.png", "tex_bottom": "wood_top.png", "sound": "break_wood"},
    PLANKS: {"name": "Planks", "top": (194, 154, 98), "side": (184, 144, 90), "bottom": (170, 132, 82), "solid": True, "transparent": False, "emissive": False, "break_time": 0.55, "drop": PLANKS, "axe": True, "tex": "planks.png", "sound": "break_wood"},
    LEAVES: {"name": "Oak Leaves", "top": (54, 138, 46), "side": (46, 124, 40), "bottom": (40, 108, 34), "solid": True, "transparent": True, "emissive": False, "break_time": 0.18, "drop": ITEM_APPLE, "tex": "leaves.png", "sound": "break"},
    SAND: {"name": "Sand", "top": (224, 210, 156), "side": (214, 200, 146), "bottom": (200, 186, 134), "solid": True, "transparent": False, "emissive": False, "break_time": 0.30, "drop": SAND, "shovel": True, "tex": "sand.png", "sound": "break"},
    WATER: {"name": "Water", "top": (46, 122, 218), "side": (40, 108, 204), "bottom": (34, 96, 188), "solid": False, "transparent": True, "emissive": False, "break_time": 999.0, "drop": AIR, "tex": "water.png", "sound": "break"},
    GLASS: {"name": "Glass", "top": (182, 232, 246), "side": (172, 222, 238), "bottom": (162, 212, 228), "solid": True, "transparent": True, "emissive": False, "break_time": 0.20, "drop": AIR, "tex": "glass.png", "sound": "glass"},
    BRICK: {"name": "Brick", "top": (168, 76, 62), "side": (156, 68, 54), "bottom": (142, 60, 48), "solid": True, "transparent": False, "emissive": False, "break_time": 0.90, "drop": BRICK, "pick": True, "tex": "brick.png", "sound": "break_stone"},
    COAL_ORE: {"name": "Coal Ore", "top": (118, 120, 124), "side": (108, 110, 114), "bottom": (98, 100, 104), "solid": True, "transparent": False, "emissive": False, "break_time": 1.25, "drop": ITEM_COAL, "pick": True, "xp": 2, "tex": "coal_ore.png", "sound": "break_stone"},
    IRON_ORE: {"name": "Iron Ore", "top": (124, 122, 120), "side": (116, 114, 112), "bottom": (104, 102, 100), "solid": True, "transparent": False, "emissive": False, "break_time": 1.45, "drop": IRON_ORE, "pick": True, "xp": 3, "tex": "iron_ore.png", "sound": "break_stone"},
    GOLD_ORE: {"name": "Gold Ore", "top": (126, 124, 118), "side": (118, 116, 110), "bottom": (106, 104, 98), "solid": True, "transparent": False, "emissive": False, "break_time": 1.60, "drop": GOLD_ORE, "pick": True, "xp": 5, "tex": "gold_ore.png", "sound": "break_stone"},
    DIAMOND_ORE: {"name": "Diamond Ore", "top": (122, 128, 134), "side": (114, 120, 126), "bottom": (102, 108, 114), "solid": True, "transparent": False, "emissive": False, "break_time": 1.90, "drop": ITEM_DIAMOND, "pick": True, "xp": 8, "tex": "diamond_ore.png", "sound": "break_stone"},
    GLOWSTONE: {"name": "Glowstone", "top": (252, 218, 104), "side": (244, 198, 78), "bottom": (228, 178, 64), "solid": True, "transparent": False, "emissive": True, "break_time": 0.35, "drop": GLOWSTONE, "tex": "glowstone.png", "sound": "glass"},
    BEDROCK: {"name": "Bedrock", "top": (46, 46, 52), "side": (38, 38, 44), "bottom": (30, 30, 36), "solid": True, "transparent": False, "emissive": False, "break_time": 999.0, "drop": AIR, "tex": "bedrock.png", "sound": "break_stone"},
    SNOW: {"name": "Snow", "top": (244, 249, 255), "side": (226, 236, 246), "bottom": (208, 220, 234), "solid": True, "transparent": False, "emissive": False, "break_time": 0.25, "drop": SNOW, "shovel": True, "tex": "snow.png", "sound": "break"},
    TNT: {"name": "TNT", "top": (212, 72, 58), "side": (202, 56, 46), "bottom": (182, 48, 40), "solid": True, "transparent": False, "emissive": False, "break_time": 0.15, "drop": TNT, "tex_top": "tnt_top.png", "tex_side": "tnt_side.png", "tex_bottom": "tnt_top.png", "sound": "ignite"},
    CRAFT_TABLE: {"name": "Craft Table", "top": (178, 122, 74), "side": (152, 104, 64), "bottom": (136, 92, 56), "solid": True, "transparent": False, "emissive": False, "break_time": 0.55, "drop": CRAFT_TABLE, "axe": True, "usable": True, "tex_top": "craft_top.png", "tex_side": "craft_side.png", "tex_bottom": "planks.png", "sound": "break_wood"},
    FURNACE: {"name": "Furnace", "top": (118, 120, 124), "side": (104, 106, 110), "bottom": (92, 94, 98), "solid": True, "transparent": False, "emissive": False, "break_time": 1.10, "drop": FURNACE, "pick": True, "usable": True, "tex_top": "furnace_side.png", "tex_side": "furnace_front.png", "tex_bottom": "furnace_side.png", "sound": "break_stone"},
    CHEST: {"name": "Chest", "top": (174, 126, 58), "side": (158, 112, 48), "bottom": (140, 98, 42), "solid": True, "transparent": False, "emissive": False, "break_time": 0.60, "drop": CHEST, "axe": True, "usable": True, "tex_top": "craft_top.png", "tex_side": "chest_front.png", "tex_bottom": "planks.png", "sound": "break_wood"},
    SANDSTONE: {"name": "Sandstone", "top": (218, 202, 146), "side": (206, 188, 134), "bottom": (192, 174, 122), "solid": True, "transparent": False, "emissive": False, "break_time": 0.85, "drop": SANDSTONE, "pick": True, "tex": "sandstone.png", "sound": "break_stone"},
    CACTUS: {"name": "Cactus", "top": (62, 154, 58), "side": (48, 134, 46), "bottom": (42, 116, 40), "solid": True, "transparent": False, "emissive": False, "break_time": 0.30, "drop": CACTUS, "tex_top": "cactus_top.png", "tex_side": "cactus_side.png", "tex_bottom": "cactus_top.png", "sound": "break"},
    TORCH: {"name": "Torch", "top": (255, 224, 98), "side": (196, 148, 76), "bottom": (122, 86, 44), "solid": False, "transparent": True, "emissive": True, "break_time": 0.12, "drop": TORCH, "tex": "torch.png", "sound": "break_wood"},
    OBSIDIAN: {"name": "Obsidian", "top": (38, 28, 56), "side": (28, 20, 44), "bottom": (22, 14, 34), "solid": True, "transparent": False, "emissive": False, "break_time": 2.80, "drop": OBSIDIAN, "pick": True, "xp": 5, "tex": "obsidian.png", "sound": "break_stone"},
    MOSSY_COBBLE: {"name": "Mossy Cobble", "top": (88, 124, 82), "side": (82, 114, 78), "bottom": (72, 98, 70), "solid": True, "transparent": False, "emissive": False, "break_time": 1.00, "drop": MOSSY_COBBLE, "pick": True, "tex": "mossycobble.png", "sound": "break_stone"},
    BOOKSHELF: {"name": "Bookshelf", "top": (184, 144, 90), "side": (152, 108, 68), "bottom": (170, 132, 82), "solid": True, "transparent": False, "emissive": False, "break_time": 0.65, "drop": BOOKSHELF, "axe": True, "tex_top": "planks.png", "tex_side": "bookshelf.png", "tex_bottom": "planks.png", "sound": "break_wood"},
    LAVA: {"name": "Lava", "top": (244, 112, 24), "side": (224, 88, 18), "bottom": (196, 68, 14), "solid": False, "transparent": False, "emissive": True, "break_time": 999.0, "drop": AIR, "tex": "lava.png", "sound": "ignite"},
    GRAVEL: {"name": "Gravel", "top": (134, 130, 126), "side": (122, 118, 114), "bottom": (108, 104, 100), "solid": True, "transparent": False, "emissive": False, "break_time": 0.35, "drop": GRAVEL, "shovel": True, "tex": "gravel.png", "sound": "break"},
    ICE: {"name": "Ice", "top": (156, 208, 248), "side": (136, 192, 238), "bottom": (118, 174, 224), "solid": True, "transparent": True, "emissive": False, "break_time": 0.35, "drop": ICE, "pick": True, "tex": "ice.png", "sound": "glass"},
    GOLD_BLOCK: {"name": "Gold Block", "top": (248, 212, 54), "side": (236, 192, 42), "bottom": (214, 168, 34), "solid": True, "transparent": False, "emissive": False, "break_time": 1.35, "drop": GOLD_BLOCK, "pick": True, "tex": "gold_block.png", "sound": "break_stone"},
    IRON_BLOCK: {"name": "Iron Block", "top": (218, 222, 228), "side": (200, 204, 210), "bottom": (182, 186, 192), "solid": True, "transparent": False, "emissive": False, "break_time": 1.45, "drop": IRON_BLOCK, "pick": True, "tex": "iron_block.png", "sound": "break_stone"},
    DIAMOND_BLOCK: {"name": "Diamond Blk", "top": (84, 232, 236), "side": (68, 210, 216), "bottom": (54, 188, 194), "solid": True, "transparent": False, "emissive": False, "break_time": 1.80, "drop": DIAMOND_BLOCK, "pick": True, "tex": "diamond_block.png", "sound": "break_stone"},
    WOOL_WHITE: {"name": "White Wool", "top": (238, 240, 244), "side": (222, 224, 228), "bottom": (204, 206, 210), "solid": True, "transparent": False, "emissive": False, "break_time": 0.30, "drop": WOOL_WHITE, "tex": "wool_white.png", "sound": "break"},
    WOOL_RED: {"name": "Red Wool", "top": (196, 48, 44), "side": (176, 40, 38), "bottom": (156, 34, 32), "solid": True, "transparent": False, "emissive": False, "break_time": 0.30, "drop": WOOL_RED, "tex": "wool_red.png", "sound": "break"},
    WOOL_BLUE: {"name": "Blue Wool", "top": (54, 88, 196), "side": (46, 76, 174), "bottom": (38, 64, 152), "solid": True, "transparent": False, "emissive": False, "break_time": 0.30, "drop": WOOL_BLUE, "tex": "wool_blue.png", "sound": "break"},
    WOOL_YELLOW: {"name": "Yellow Wool", "top": (238, 206, 56), "side": (218, 186, 48), "bottom": (196, 166, 42), "solid": True, "transparent": False, "emissive": False, "break_time": 0.30, "drop": WOOL_YELLOW, "tex": "wool_yellow.png", "sound": "break"},
    LADDER: {"name": "Ladder", "top": (176, 134, 78), "side": (156, 116, 66), "bottom": (136, 98, 54), "solid": False, "transparent": True, "emissive": False, "break_time": 0.25, "drop": LADDER, "axe": True, "tex": "ladder.png", "sound": "break_wood"},
    DOOR_CLOSED: {"name": "Oak Door", "top": (162, 118, 66), "side": (148, 106, 58), "bottom": (132, 94, 50), "solid": True, "transparent": False, "emissive": False, "break_time": 0.55, "drop": DOOR_CLOSED, "axe": True, "usable": True, "tex": "door.png", "sound": "break_wood"},
    DOOR_OPEN: {"name": "Open Door", "top": (148, 108, 58), "side": (132, 94, 50), "bottom": (118, 84, 44), "solid": False, "transparent": True, "emissive": False, "break_time": 0.55, "drop": DOOR_CLOSED, "axe": True, "usable": True, "tex": "door.png", "sound": "break_wood"},
    BED: {"name": "Bed", "top": (196, 54, 48), "side": (164, 120, 70), "bottom": (138, 98, 56), "solid": True, "transparent": False, "emissive": False, "break_time": 0.30, "drop": BED, "usable": True, "tex_top": "wool_red.png", "tex_side": "bed.png", "tex_bottom": "planks.png", "sound": "break_wood"},
    PORTAL: {"name": "Nether Portal", "top": (176, 62, 242), "side": (152, 46, 224), "bottom": (128, 36, 198), "solid": False, "transparent": True, "emissive": True, "break_time": 1.20, "drop": PORTAL, "usable": True, "tex": "obsidian.png", "sound": "ignite"},
    PINE_WOOD: {"name": "Pine Log", "top": (118, 84, 48), "side": (72, 48, 28), "bottom": (106, 74, 42), "solid": True, "transparent": False, "emissive": False, "break_time": 0.65, "drop": PINE_WOOD, "axe": True, "tex_top": "pine_wood_top.png", "tex_side": "pine_wood.png", "tex_bottom": "pine_wood_top.png", "sound": "break_wood"},
    PINE_LEAVES: {"name": "Pine Needles", "top": (38, 96, 54), "side": (30, 82, 46), "bottom": (24, 68, 38), "solid": True, "transparent": True, "emissive": False, "break_time": 0.18, "drop": ITEM_APPLE, "tex": "pine_leaves.png", "sound": "break"},
    BIRCH_WOOD: {"name": "Birch Log", "top": (204, 188, 152), "side": (222, 220, 214), "bottom": (188, 172, 138), "solid": True, "transparent": False, "emissive": False, "break_time": 0.60, "drop": BIRCH_WOOD, "axe": True, "tex_top": "birch_wood_top.png", "tex_side": "birch_wood.png", "tex_bottom": "birch_wood_top.png", "sound": "break_wood"},
    BIRCH_LEAVES: {"name": "Birch Leaves", "top": (92, 168, 72), "side": (78, 152, 60), "bottom": (66, 134, 52), "solid": True, "transparent": True, "emissive": False, "break_time": 0.18, "drop": ITEM_APPLE, "tex": "birch_leaves.png", "sound": "break"},
    RED_SANDSTONE: {"name": "Red Sandst", "top": (186, 98, 52), "side": (172, 86, 44), "bottom": (154, 76, 38), "solid": True, "transparent": False, "emissive": False, "break_time": 0.85, "drop": RED_SANDSTONE, "pick": True, "tex": "red_sandstone.png", "sound": "break_stone"},
    TERRACOTTA: {"name": "Terracotta", "top": (162, 88, 62), "side": (148, 78, 54), "bottom": (132, 68, 46), "solid": True, "transparent": False, "emissive": False, "break_time": 0.90, "drop": TERRACOTTA, "pick": True, "tex": "terracotta.png", "sound": "break_stone"},
    CLAY: {"name": "Clay Block", "top": (162, 168, 182), "side": (148, 154, 168), "bottom": (134, 140, 154), "solid": True, "transparent": False, "emissive": False, "break_time": 0.38, "drop": CLAY, "shovel": True, "tex": "clay.png", "sound": "break"},
    EMERALD_ORE: {"name": "Emerald Ore", "top": (118, 132, 124), "side": (108, 124, 114), "bottom": (96, 110, 102), "solid": True, "transparent": False, "emissive": False, "break_time": 1.95, "drop": ITEM_EMERALD, "pick": True, "xp": 10, "tex": "emerald_ore.png", "sound": "break_stone"},
    EMERALD_BLOCK: {"name": "Emerald Blk", "top": (56, 224, 108), "side": (42, 202, 92), "bottom": (34, 178, 78), "solid": True, "transparent": False, "emissive": False, "break_time": 1.80, "drop": EMERALD_BLOCK, "pick": True, "tex": "emerald_block.png", "sound": "break_stone"},
    FLOWER_RED: {"name": "Rose", "top": (224, 48, 48), "side": (196, 42, 46), "bottom": (64, 142, 54), "solid": False, "transparent": True, "emissive": False, "break_time": 0.08, "drop": FLOWER_RED, "tex": "flower_red.png", "sound": "break"},
    FLOWER_YELLOW: {"name": "Dandelion", "top": (246, 218, 52), "side": (228, 198, 46), "bottom": (72, 148, 58), "solid": False, "transparent": True, "emissive": False, "break_time": 0.08, "drop": FLOWER_YELLOW, "tex": "flower_yellow.png", "sound": "break"},
    NETHERRACK: {"name": "Netherrack", "top": (122, 46, 44), "side": (108, 38, 36), "bottom": (92, 32, 30), "solid": True, "transparent": False, "emissive": False, "break_time": 0.45, "drop": NETHERRACK, "pick": True, "tex": "netherrack.png", "sound": "break_stone"},
    SNOW_BLOCK: {"name": "Snow Block", "top": (240, 246, 255), "side": (222, 232, 246), "bottom": (204, 216, 232), "solid": True, "transparent": False, "emissive": False, "break_time": 0.45, "drop": SNOW_BLOCK, "shovel": True, "tex": "snow.png", "sound": "break"},
    WOOL_GREEN: {"name": "Green Wool", "top": (64, 168, 62), "side": (54, 148, 52), "bottom": (46, 128, 44), "solid": True, "transparent": False, "emissive": False, "break_time": 0.30, "drop": WOOL_GREEN, "tex": "pine_leaves.png", "sound": "break"},
}

ITEMS = {
    ITEM_STICK: {"name": "Stick", "color": (168, 122, 72), "tex": "stick.png"},
    ITEM_COAL: {"name": "Coal", "color": (42, 44, 48), "tex": "coal.png"},
    ITEM_IRON_INGOT: {"name": "Iron Ingot", "color": (218, 222, 228), "tex": "iron_ingot.png"},
    ITEM_GOLD_INGOT: {"name": "Gold Ingot", "color": (248, 208, 64), "tex": "gold_ingot.png"},
    ITEM_DIAMOND: {"name": "Diamond", "color": (82, 232, 242), "tex": "diamond.png"},
    ITEM_EMERALD: {"name": "Emerald", "color": (52, 224, 104), "tex": "emerald.png"},
    ITEM_FLINT: {"name": "Flint", "color": (56, 58, 66), "tex": "flint.png"},
    ITEM_APPLE: {"name": "Apple", "color": (218, 48, 52), "food": 4, "tex": "apple.png"},
    ITEM_RAW_MEAT: {"name": "Raw Meat", "color": (204, 108, 104), "food": 3, "tex": "bread.png"},
    ITEM_STEAK: {"name": "Steak", "color": (146, 72, 48), "food": 8, "tex": "bread.png"},
    ITEM_BREAD: {"name": "Bread", "color": (208, 162, 86), "food": 5, "tex": "bread.png"},

    TOOL_WOOD_PICK: {"name": "Wood Pick", "color": (176, 134, 78), "pick_speed": 2.4, "damage": 3, "tex": "wood_pick.png"},
    TOOL_STONE_PICK: {"name": "Stone Pick", "color": (148, 152, 158), "pick_speed": 3.6, "damage": 4, "tex": "stone_pick.png"},
    TOOL_IRON_PICK: {"name": "Iron Pick", "color": (216, 220, 226), "pick_speed": 5.0, "damage": 5, "tex": "iron_pick.png"},
    TOOL_GOLD_PICK: {"name": "Gold Pick", "color": (248, 212, 56), "pick_speed": 9.0, "damage": 4, "tex": "gold_ingot.png"},
    TOOL_DIAMOND_PICK: {"name": "Dia Pick", "color": (86, 232, 244), "pick_speed": 7.5, "damage": 6, "tex": "diamond_pick.png"},

    TOOL_WOOD_AXE: {"name": "Wood Axe", "color": (176, 134, 78), "axe_speed": 3.2, "damage": 4, "tex": "wood_axe.png"},
    TOOL_STONE_AXE: {"name": "Stone Axe", "color": (148, 152, 158), "axe_speed": 4.4, "damage": 5, "tex": "stone_axe.png"},
    TOOL_IRON_AXE: {"name": "Iron Axe", "color": (216, 220, 226), "axe_speed": 5.8, "damage": 7, "tex": "iron_axe.png"},
    TOOL_DIAMOND_AXE: {"name": "Dia Axe", "color": (86, 232, 244), "axe_speed": 8.0, "damage": 9, "tex": "diamond_axe.png"},

    TOOL_WOOD_SHOVEL: {"name": "Wood Shovel", "color": (176, 134, 78), "shovel_speed": 3.2, "damage": 2, "tex": "wood_shovel.png"},
    TOOL_STONE_SHOVEL: {"name": "Stone Shov", "color": (148, 152, 158), "shovel_speed": 4.4, "damage": 2, "tex": "stone_shovel.png"},
    TOOL_IRON_SHOVEL: {"name": "Iron Shovel", "color": (216, 220, 226), "shovel_speed": 6.0, "damage": 3, "tex": "iron_shovel.png"},
    TOOL_DIAMOND_SHOVEL: {"name": "Dia Shovel", "color": (86, 232, 244), "shovel_speed": 8.5, "damage": 4, "tex": "diamond_shovel.png"},

    TOOL_WOOD_SWORD: {"name": "Wood Sword", "color": (182, 138, 82), "pick_speed": 1.2, "damage": 5, "tex": "wood_sword.png"},
    TOOL_STONE_SWORD: {"name": "Stone Sword", "color": (152, 156, 162), "pick_speed": 1.2, "damage": 7, "tex": "stone_sword.png"},
    TOOL_IRON_SWORD: {"name": "Iron Sword", "color": (222, 226, 232), "pick_speed": 1.2, "damage": 9, "tex": "iron_sword.png"},
    TOOL_GOLD_SWORD: {"name": "Gold Sword", "color": (248, 212, 56), "pick_speed": 1.2, "damage": 8, "tex": "gold_ingot.png"},
    TOOL_DIAMOND_SWORD: {"name": "Dia Sword", "color": (92, 236, 248), "pick_speed": 1.2, "damage": 12, "tex": "diamond_sword.png"},

    ITEM_BOW: {"name": "Bow", "color": (168, 120, 68), "damage": 6, "tex": "stick.png"},
    ITEM_ARROW: {"name": "Arrow", "color": (220, 220, 228), "tex": "stick.png"},
    ITEM_FLINT_STEEL: {"name": "Flint&Steel", "color": (196, 200, 210), "tex": "flint.png"},
    ITEM_BUCKET_EMPTY: {"name": "Bucket", "color": (198, 204, 212), "tex": "bucket_empty.png"},
    ITEM_BUCKET_WATER: {"name": "Water Bkt", "color": (56, 140, 236), "tex": "bucket_water.png"},
    ITEM_BUCKET_LAVA: {"name": "Lava Bkt", "color": (244, 118, 28), "tex": "bucket_lava.png"},
    ARMOR_IRON: {"name": "Iron Armor", "color": (214, 220, 228), "armor": 12, "tex": "iron_block.png"},
    ARMOR_GOLD: {"name": "Gold Armor", "color": (248, 212, 56), "armor": 14, "tex": "gold_block.png"},
    ARMOR_DIAMOND: {"name": "Dia Armor", "color": (84, 232, 238), "armor": 18, "tex": "diamond_block.png"},
}

ALL_CREATIVE_ITEMS = [
    GRASS, DIRT, STONE, COBBLE, MOSSY_COBBLE, WOOD, PINE_WOOD, BIRCH_WOOD,
    PLANKS, BOOKSHELF, LEAVES, PINE_LEAVES, BIRCH_LEAVES,
    SAND, SANDSTONE, RED_SANDSTONE, TERRACOTTA, CLAY, GRAVEL, GLASS, ICE,
    BRICK, NETHERRACK, GLOWSTONE, TORCH, SNOW, SNOW_BLOCK,
    CRAFT_TABLE, FURNACE, CHEST, BED, DOOR_CLOSED, LADDER,
    OBSIDIAN, PORTAL, TNT, CACTUS, FLOWER_RED, FLOWER_YELLOW,
    WOOL_WHITE, WOOL_RED, WOOL_BLUE, WOOL_YELLOW, WOOL_GREEN,
    GOLD_BLOCK, IRON_BLOCK, DIAMOND_BLOCK, EMERALD_BLOCK,
    COAL_ORE, IRON_ORE, GOLD_ORE, DIAMOND_ORE, EMERALD_ORE,
    TOOL_DIAMOND_PICK, TOOL_GOLD_PICK, TOOL_DIAMOND_AXE, TOOL_DIAMOND_SHOVEL, TOOL_DIAMOND_SWORD,
    ITEM_BOW, ITEM_ARROW, ITEM_FLINT_STEEL,
    ITEM_BUCKET_WATER, ITEM_BUCKET_LAVA, ITEM_BUCKET_EMPTY,
    ARMOR_DIAMOND, ARMOR_GOLD, ITEM_STEAK, ITEM_BREAD, ITEM_APPLE,
]

CRAFT_RECIPES = [
    (PLANKS, 4, [(WOOD, 1)], "4x Planks <- 1 Oak Log"),
    (PLANKS, 4, [(PINE_WOOD, 1)], "4x Planks <- 1 Pine Log"),
    (PLANKS, 4, [(BIRCH_WOOD, 1)], "4x Planks <- 1 Birch Log"),
    (ITEM_STICK, 4, [(PLANKS, 2)], "4x Stick <- 2 Planks"),
    (CRAFT_TABLE, 1, [(PLANKS, 4)], "1x Craft Table <- 4 Planks"),
    (TORCH, 4, [(ITEM_COAL, 1), (ITEM_STICK, 1)], "4x Torch <- 1 Coal + 1 Stick"),
    (FURNACE, 1, [(COBBLE, 8)], "1x Furnace <- 8 Cobble"),
    (CHEST, 1, [(PLANKS, 8)], "1x Chest <- 8 Planks"),
    (LADDER, 3, [(ITEM_STICK, 5)], "3x Ladder <- 5 Sticks"),
    (DOOR_CLOSED, 1, [(PLANKS, 6)], "1x Oak Door <- 6 Planks"),
    (BED, 1, [(PLANKS, 3), (WOOL_WHITE, 2)], "1x Bed <- 3 Planks + 2 Wool"),
    (BOOKSHELF, 1, [(PLANKS, 6)], "1x Bookshelf <- 6 Planks"),
    (SNOW_BLOCK, 1, [(SNOW, 4)], "Snow Block <- 4 Snow"),
    (RED_SANDSTONE, 1, [(TERRACOTTA, 2)], "Red Sandst <- 2 Terracotta"),
    (TOOL_WOOD_PICK, 1, [(PLANKS, 3), (ITEM_STICK, 2)], "Wood Pickaxe <- 3 Planks + 2 Stick"),
    (TOOL_STONE_PICK, 1, [(COBBLE, 3), (ITEM_STICK, 2)], "Stone Pickaxe <- 3 Cobble + 2 Stick"),
    (TOOL_IRON_PICK, 1, [(ITEM_IRON_INGOT, 3), (ITEM_STICK, 2)], "Iron Pickaxe <- 3 Iron + 2 Stick"),
    (TOOL_GOLD_PICK, 1, [(ITEM_GOLD_INGOT, 3), (ITEM_STICK, 2)], "Gold Pickaxe <- 3 Gold + 2 Stick"),
    (TOOL_DIAMOND_PICK, 1, [(ITEM_DIAMOND, 3), (ITEM_STICK, 2)], "Diamond Pickaxe <- 3 Dia + 2 Stick"),
    (TOOL_WOOD_AXE, 1, [(PLANKS, 3), (ITEM_STICK, 2)], "Wood Axe <- 3 Planks + 2 Stick"),
    (TOOL_STONE_AXE, 1, [(COBBLE, 3), (ITEM_STICK, 2)], "Stone Axe <- 3 Cobble + 2 Stick"),
    (TOOL_IRON_AXE, 1, [(ITEM_IRON_INGOT, 3), (ITEM_STICK, 2)], "Iron Axe <- 3 Iron + 2 Stick"),
    (TOOL_DIAMOND_AXE, 1, [(ITEM_DIAMOND, 3), (ITEM_STICK, 2)], "Diamond Axe <- 3 Dia + 2 Stick"),
    (TOOL_WOOD_SHOVEL, 1, [(PLANKS, 1), (ITEM_STICK, 2)], "Wood Shovel <- 1 Plank + 2 Stick"),
    (TOOL_STONE_SHOVEL, 1, [(COBBLE, 1), (ITEM_STICK, 2)], "Stone Shovel <- 1 Cobble + 2 Stick"),
    (TOOL_IRON_SHOVEL, 1, [(ITEM_IRON_INGOT, 1), (ITEM_STICK, 2)], "Iron Shovel <- 1 Iron + 2 Stick"),
    (TOOL_DIAMOND_SHOVEL, 1, [(ITEM_DIAMOND, 1), (ITEM_STICK, 2)], "Diamond Shovel <- 1 Dia + 2 Stick"),
    (TOOL_WOOD_SWORD, 1, [(PLANKS, 2), (ITEM_STICK, 1)], "Wood Sword <- 2 Planks + 1 Stick"),
    (TOOL_STONE_SWORD, 1, [(COBBLE, 2), (ITEM_STICK, 1)], "Stone Sword <- 2 Cobble + 1 Stick"),
    (TOOL_IRON_SWORD, 1, [(ITEM_IRON_INGOT, 2), (ITEM_STICK, 1)], "Iron Sword <- 2 Iron + 1 Stick"),
    (TOOL_GOLD_SWORD, 1, [(ITEM_GOLD_INGOT, 2), (ITEM_STICK, 1)], "Gold Sword <- 2 Gold + 1 Stick"),
    (TOOL_DIAMOND_SWORD, 1, [(ITEM_DIAMOND, 2), (ITEM_STICK, 1)], "Diamond Sword <- 2 Dia + 1 Stick"),
    (ITEM_FLINT_STEEL, 1, [(ITEM_IRON_INGOT, 1), (ITEM_FLINT, 1)], "Flint & Steel <- 1 Iron + 1 Flint"),
    (ITEM_BOW, 1, [(ITEM_STICK, 3)], "1x Bow <- 3 Sticks"),
    (ITEM_ARROW, 6, [(ITEM_STICK, 2), (ITEM_FLINT, 1)], "6x Arrows <- 2 Sticks + 1 Flint"),
    (ITEM_BUCKET_EMPTY, 1, [(ITEM_IRON_INGOT, 3)], "1x Bucket <- 3 Iron Ingots"),
    (ARMOR_IRON, 1, [(ITEM_IRON_INGOT, 6)], "Iron Armor <- 6 Iron Ingots"),
    (ARMOR_GOLD, 1, [(ITEM_GOLD_INGOT, 6)], "Gold Armor <- 6 Gold Ingots"),
    (ARMOR_DIAMOND, 1, [(ITEM_DIAMOND, 6)], "Diamond Armor <- 6 Diamonds"),
    (IRON_BLOCK, 1, [(ITEM_IRON_INGOT, 9)], "Iron Block <- 9 Iron Ingots"),
    (GOLD_BLOCK, 1, [(ITEM_GOLD_INGOT, 9)], "Gold Block <- 9 Gold Ingots"),
    (DIAMOND_BLOCK, 1, [(ITEM_DIAMOND, 9)], "Diamond Block <- 9 Diamonds"),
    (EMERALD_BLOCK, 1, [(ITEM_EMERALD, 9)], "Emerald Block <- 9 Emeralds"),
    (ITEM_EMERALD, 9, [(EMERALD_BLOCK, 1)], "9x Emerald <- 1 Emerald Block"),
    (OBSIDIAN, 2, [(COBBLE, 4), (ITEM_COAL, 2)], "2x Obsidian <- 4 Cobble + 2 Coal"),
    (PORTAL, 1, [(OBSIDIAN, 4), (ITEM_DIAMOND, 1)], "Nether Portal <- 4 Obsidian + 1 Dia"),
    (BRICK, 2, [(CLAY, 2), (ITEM_COAL, 1)], "2x Brick <- 2 Clay + 1 Coal"),
    (GLOWSTONE, 1, [(ITEM_COAL, 1), (GLASS, 2)], "1x Glowstone <- 1 Coal + 2 Glass"),
    (TNT, 1, [(SAND, 3), (ITEM_COAL, 2)], "1x TNT <- 3 Sand + 2 Coal"),
    (WOOL_RED, 1, [(WOOL_WHITE, 1), (FLOWER_RED, 1)], "Red Wool <- Wool + Rose"),
    (WOOL_YELLOW, 1, [(WOOL_WHITE, 1), (FLOWER_YELLOW, 1)], "Yellow Wool <- Wool + Dandelion"),
    (WOOL_BLUE, 1, [(WOOL_WHITE, 1)], "Blue Wool <- White Wool"),
    (WOOL_GREEN, 1, [(WOOL_WHITE, 1), (CACTUS, 1)], "Green Wool <- Wool + Cactus"),
]


def _build_craft_meta():
    """Build (category, needs_table, grid_9tuple) for every recipe in CRAFT_RECIPES."""
    meta = []
    for res_id, _rcnt, reqs, _lbl in CRAFT_RECIPES:
        # Categorize cleanly
        if res_id in (
            TOOL_WOOD_PICK, TOOL_STONE_PICK, TOOL_IRON_PICK, TOOL_GOLD_PICK, TOOL_DIAMOND_PICK,
            TOOL_WOOD_AXE, TOOL_STONE_AXE, TOOL_IRON_AXE, TOOL_DIAMOND_AXE,
            TOOL_WOOD_SHOVEL, TOOL_STONE_SHOVEL, TOOL_IRON_SHOVEL, TOOL_DIAMOND_SHOVEL,
            ITEM_BUCKET_EMPTY, ITEM_FLINT_STEEL,
        ):
            cat = "tools"
        elif res_id in (
            TOOL_WOOD_SWORD, TOOL_STONE_SWORD, TOOL_IRON_SWORD, TOOL_GOLD_SWORD, TOOL_DIAMOND_SWORD,
            ITEM_BOW, ITEM_ARROW, ARMOR_IRON, ARMOR_GOLD, ARMOR_DIAMOND,
        ):
            cat = "gear"
        elif res_id in (CRAFT_TABLE, FURNACE, CHEST, TORCH, LADDER, BED, PORTAL, TNT):
            cat = "utility"
        else:
            cat = "blocks"

        # Exact authentic 3x3 shaped pattern (row-major 9-tuple, 0=empty)
        needs_table = True
        if res_id == PLANKS:
            log_id = reqs[0][0]
            grid = (log_id, 0, 0, 0, 0, 0, 0, 0, 0)
            needs_table = False
        elif res_id == ITEM_STICK:
            grid = (PLANKS, 0, 0, PLANKS, 0, 0, 0, 0, 0)
            needs_table = False
        elif res_id == CRAFT_TABLE:
            grid = (PLANKS, PLANKS, 0, PLANKS, PLANKS, 0, 0, 0, 0)
            needs_table = False
        elif res_id == TORCH:
            grid = (ITEM_COAL, 0, 0, ITEM_STICK, 0, 0, 0, 0, 0)
            needs_table = False
        elif res_id == FURNACE:
            grid = (COBBLE, COBBLE, COBBLE, COBBLE, 0, COBBLE, COBBLE, COBBLE, COBBLE)
        elif res_id == CHEST:
            grid = (PLANKS, PLANKS, PLANKS, PLANKS, 0, PLANKS, PLANKS, PLANKS, PLANKS)
        elif res_id == LADDER:
            grid = (ITEM_STICK, 0, ITEM_STICK, 0, ITEM_STICK, 0, ITEM_STICK, 0, ITEM_STICK)
        elif res_id == DOOR_CLOSED:
            grid = (PLANKS, PLANKS, 0, PLANKS, PLANKS, 0, PLANKS, PLANKS, 0)
        elif res_id == BED:
            grid = (WOOL_WHITE, WOOL_WHITE, 0, PLANKS, PLANKS, PLANKS, 0, 0, 0)
        elif res_id == BOOKSHELF:
            grid = (PLANKS, PLANKS, PLANKS, 0, 0, 0, PLANKS, PLANKS, PLANKS)
        elif res_id == SNOW_BLOCK:
            grid = (SNOW, SNOW, 0, SNOW, SNOW, 0, 0, 0, 0)
            needs_table = False
        elif res_id == RED_SANDSTONE:
            grid = (TERRACOTTA, TERRACOTTA, 0, 0, 0, 0, 0, 0, 0)
            needs_table = False
        elif res_id in (TOOL_WOOD_PICK, TOOL_STONE_PICK, TOOL_IRON_PICK, TOOL_GOLD_PICK, TOOL_DIAMOND_PICK):
            m = reqs[0][0]
            grid = (m, m, m, 0, ITEM_STICK, 0, 0, ITEM_STICK, 0)
        elif res_id in (TOOL_WOOD_AXE, TOOL_STONE_AXE, TOOL_IRON_AXE, TOOL_DIAMOND_AXE):
            m = reqs[0][0]
            grid = (m, m, 0, m, ITEM_STICK, 0, 0, ITEM_STICK, 0)
        elif res_id in (TOOL_WOOD_SHOVEL, TOOL_STONE_SHOVEL, TOOL_IRON_SHOVEL, TOOL_DIAMOND_SHOVEL):
            m = reqs[0][0]
            grid = (0, m, 0, 0, ITEM_STICK, 0, 0, ITEM_STICK, 0)
        elif res_id in (TOOL_WOOD_SWORD, TOOL_STONE_SWORD, TOOL_IRON_SWORD, TOOL_GOLD_SWORD, TOOL_DIAMOND_SWORD):
            m = reqs[0][0]
            grid = (0, m, 0, 0, m, 0, 0, ITEM_STICK, 0)
        elif res_id == ITEM_FLINT_STEEL:
            grid = (ITEM_IRON_INGOT, 0, 0, 0, ITEM_FLINT, 0, 0, 0, 0)
            needs_table = False
        elif res_id == ITEM_BOW:
            grid = (0, ITEM_STICK, 0, ITEM_STICK, 0, 0, 0, ITEM_STICK, 0)
        elif res_id == ITEM_ARROW:
            grid = (0, ITEM_FLINT, 0, 0, ITEM_STICK, 0, 0, ITEM_STICK, 0)
        elif res_id == ITEM_BUCKET_EMPTY:
            grid = (ITEM_IRON_INGOT, 0, ITEM_IRON_INGOT, 0, ITEM_IRON_INGOT, 0, 0, 0, 0)
        elif res_id in (ARMOR_IRON, ARMOR_GOLD, ARMOR_DIAMOND):
            m = reqs[0][0]
            grid = (m, 0, m, m, m, m, 0, 0, 0)
        elif res_id in (IRON_BLOCK, GOLD_BLOCK, DIAMOND_BLOCK, EMERALD_BLOCK):
            m = reqs[0][0]
            grid = (m, m, m, m, m, m, m, m, m)
        elif res_id == ITEM_EMERALD:
            grid = (EMERALD_BLOCK, 0, 0, 0, 0, 0, 0, 0, 0)
            needs_table = False
        elif res_id == OBSIDIAN:
            grid = (COBBLE, COBBLE, 0, COBBLE, COBBLE, 0, ITEM_COAL, ITEM_COAL, 0)
        elif res_id == PORTAL:
            grid = (OBSIDIAN, OBSIDIAN, 0, OBSIDIAN, ITEM_DIAMOND, OBSIDIAN, 0, 0, 0)
        elif res_id == BRICK:
            grid = (CLAY, CLAY, 0, ITEM_COAL, 0, 0, 0, 0, 0)
            needs_table = False
        elif res_id == GLOWSTONE:
            grid = (GLASS, ITEM_COAL, GLASS, 0, 0, 0, 0, 0, 0)
        elif res_id == TNT:
            grid = (SAND, ITEM_COAL, SAND, ITEM_COAL, SAND, 0, 0, 0, 0)
        elif res_id in (WOOL_RED, WOOL_YELLOW, WOOL_BLUE, WOOL_GREEN):
            if len(reqs) > 1:
                grid = (reqs[0][0], reqs[1][0], 0, 0, 0, 0, 0, 0, 0)
            else:
                grid = (reqs[0][0], 0, 0, 0, 0, 0, 0, 0, 0)
            needs_table = False
        else:
            slots = []
            for rb, rc in reqs:
                slots.extend([rb] * min(rc, 9 - len(slots)))
            while len(slots) < 9:
                slots.append(0)
            grid = tuple(slots[:9])
        meta.append((cat, needs_table, grid))
    return tuple(meta)


CRAFT_META = _build_craft_meta()


def get_craft_meta(ridx):
    """Return (category, needs_table, shaped_9tuple) for recipe index."""
    return CRAFT_META[ridx]


SMELT_RECIPES = [
    (IRON_ORE, ITEM_IRON_INGOT, 1, "Iron Ingot <- Iron Ore + Coal"),
    (GOLD_ORE, ITEM_GOLD_INGOT, 1, "Gold Ingot <- Gold Ore + Coal"),
    (CLAY, BRICK, 2, "2x Brick <- Clay Block + Coal"),
    (SAND, GLASS, 1, "Glass <- Sand + Coal"),
    (COBBLE, STONE, 1, "Stone <- Cobble + Coal"),
    (NETHERRACK, RED_SANDSTONE, 1, "Red Sandst <- Netherrack + Coal"),
    (ITEM_RAW_MEAT, ITEM_STEAK, 1, "Steak <- Raw Meat + Coal"),
    (WOOD, ITEM_COAL, 1, "Charcoal <- Oak Log + Coal/Wood"),
]


def item_name(iid):
    if iid in BLOCKS:
        return BLOCKS[iid]["name"]
    if iid in ITEMS:
        return ITEMS[iid]["name"]
    return "Empty"


def item_color(iid):
    if iid in BLOCKS:
        return BLOCKS[iid]["top"], BLOCKS[iid]["side"]
    if iid in ITEMS:
        c = ITEMS[iid]["color"]
        return c, (max(0, c[0] - 28), max(0, c[1] - 28), max(0, c[2] - 28))
    return (80, 80, 80), (60, 60, 60)


def item_texture_name(iid, face_idx=2):
    if iid in BLOCKS:
        b = BLOCKS[iid]
        if face_idx == 0 and "tex_top" in b:
            return b["tex_top"]
        if face_idx == 1 and "tex_bottom" in b:
            return b["tex_bottom"]
        if face_idx >= 2 and "tex_side" in b:
            return b["tex_side"]
        return b.get("tex")
    if iid in ITEMS:
        return ITEMS[iid].get("tex")
    return None


def is_placeable(iid):
    return iid in BLOCKS and iid not in (AIR, WATER, LAVA, BEDROCK)


def is_tool(iid):
    if iid not in ITEMS:
        return False
    meta = ITEMS[iid]
    if any(k in meta for k in ("pick_speed", "axe_speed", "shovel_speed", "damage", "armor")):
        return True
    return iid in (
        ITEM_BOW, ITEM_ARROW, ITEM_FLINT_STEEL,
        ITEM_BUCKET_EMPTY, ITEM_BUCKET_WATER, ITEM_BUCKET_LAVA,
    )


def item_stat_tag(iid):
    if iid in ITEMS:
        m = ITEMS[iid]
        if "pick_speed" in m:
            return f"Pick {m['pick_speed']:.0f}x"
        if "axe_speed" in m:
            return f"Axe {m['axe_speed']:.0f}x"
        if "shovel_speed" in m:
            return f"Shovel {m['shovel_speed']:.0f}x"
        if "damage" in m:
            return f"Atk +{m['damage']}"
        if "armor" in m:
            return f"Def {m['armor']}"
        if "food" in m:
            return f"Food +{m['food']}"
        if iid == ITEM_BOW:
            return "Ranged"
        if iid == ITEM_ARROW:
            return "Ammo"
        if iid in (ITEM_BUCKET_EMPTY, ITEM_BUCKET_WATER, ITEM_BUCKET_LAVA):
            return "Liquid"
        if iid == ITEM_FLINT_STEEL:
            return "Ignite"
        return "Material"
    if iid in BLOCKS:
        return "Block"
    return ""

