"""Core engine constants, 57 Minecraft block IDs, tools/armor/items, and face geometry."""

import os

# World & Rendering Constants (MAX_Y=32 fits 5-bit packed Y in Chunk faces cleanly)
CHUNK_SIZE = 8
MAX_Y = 32
WATER_LEVEL = 6
NEAR_PLANE = 0.14

# Block IDs (0..63 fit in 6-bit packed face field)
AIR = 0
GRASS = 1
DIRT = 2
STONE = 3
COBBLE = 4
WOOD = 5
PLANKS = 6
LEAVES = 7
SAND = 8
WATER = 9
GLASS = 10
BRICK = 11
COAL_ORE = 12
IRON_ORE = 13
GOLD_ORE = 14
DIAMOND_ORE = 15
GLOWSTONE = 16
BEDROCK = 17
SNOW = 18
TNT = 19
CRAFT_TABLE = 20
FURNACE = 21
CHEST = 22
SANDSTONE = 23
CACTUS = 24
TORCH = 25

OBSIDIAN = 26
MOSSY_COBBLE = 27
BOOKSHELF = 28
LAVA = 29
GRAVEL = 30
ICE = 31
GOLD_BLOCK = 32
IRON_BLOCK = 33
DIAMOND_BLOCK = 34
WOOL_WHITE = 35
WOOL_RED = 36
WOOL_BLUE = 37
WOOL_YELLOW = 38
LADDER = 39
DOOR_CLOSED = 40
DOOR_OPEN = 41
BED = 42
PORTAL = 43

PINE_WOOD = 44
PINE_LEAVES = 45
BIRCH_WOOD = 46
BIRCH_LEAVES = 47
RED_SANDSTONE = 48
TERRACOTTA = 49
CLAY = 50
EMERALD_ORE = 51
EMERALD_BLOCK = 52
FLOWER_RED = 53
FLOWER_YELLOW = 54
NETHERRACK = 55
SNOW_BLOCK = 56
WOOL_GREEN = 57

# Non-placeable Item IDs (>= 100)
ITEM_STICK = 101
ITEM_COAL = 102
ITEM_IRON_INGOT = 103
ITEM_GOLD_INGOT = 104
ITEM_DIAMOND = 105
ITEM_APPLE = 106
ITEM_RAW_MEAT = 107
ITEM_STEAK = 108
ITEM_BREAD = 109
ITEM_EMERALD = 110
ITEM_FLINT = 111

TOOL_WOOD_PICK = 120
TOOL_STONE_PICK = 121
TOOL_IRON_PICK = 122
TOOL_DIAMOND_PICK = 123
TOOL_WOOD_AXE = 124
TOOL_IRON_AXE = 125
TOOL_WOOD_SHOVEL = 126
TOOL_IRON_SHOVEL = 127
TOOL_STONE_AXE = 128
TOOL_DIAMOND_AXE = 129

TOOL_WOOD_SWORD = 130
TOOL_STONE_SWORD = 131
TOOL_IRON_SWORD = 132
TOOL_DIAMOND_SWORD = 133
TOOL_STONE_SHOVEL = 134
TOOL_DIAMOND_SHOVEL = 135
TOOL_GOLD_PICK = 136
TOOL_GOLD_SWORD = 137

ITEM_BOW = 140
ITEM_ARROW = 141
ITEM_BUCKET_EMPTY = 142
ITEM_BUCKET_WATER = 143
ITEM_BUCKET_LAVA = 144
ITEM_FLINT_STEEL = 145

ARMOR_IRON = 150
ARMOR_DIAMOND = 151
ARMOR_GOLD = 152

# 6 cube faces: (dx, dy, dz, shade_mult, corner_offsets)
FACES = (
    (0, 1, 0, 1.00, ((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1))),   # 0: +Y Top
    (0, -1, 0, 0.56, ((0, 0, 0), (0, 0, 1), (1, 0, 1), (1, 0, 0))),  # 1: -Y Bottom
    (1, 0, 0, 0.84, ((1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0))),   # 2: +X East
    (-1, 0, 0, 0.74, ((0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1))),  # 3: -X West
    (0, 0, 1, 0.90, ((0, 0, 1), (0, 1, 1), (1, 1, 1), (1, 0, 1))),   # 4: +Z North
    (0, 0, -1, 0.68, ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0))),  # 5: -Z South
)


def is_android():
    return (
        "ANDROID_ARGUMENT" in os.environ
        or "ANDROID_ROOT" in os.environ
        or os.path.exists("/data/data/ru.iiec.pydroid3")
    )


def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_assets_dir():
    return os.path.join(get_project_root(), "assets")


def get_save_path():
    root = get_project_root()
    try:
        test = os.path.join(root, ".pycraft_write_test")
        with open(test, "w") as f:
            f.write("ok")
        os.remove(test)
        return os.path.join(root, "minecraft_world.json")
    except Exception:
        return os.path.join(os.path.expanduser("~"), "minecraft_world.json")
