#!/usr/bin/env python3
"""
Downloads open-source 16x16 voxel textures and sound effects from
luanti-org/minetest_game (CC BY-SA 3.0 / CC0) into ./assets/
"""

import os
import shutil
import subprocess
import urllib.request

BASE_RAW = "https://raw.githubusercontent.com/luanti-org/minetest_game/master/"

TEXTURES = {
    "grass_top.png": "mods/default/textures/default_grass.png",
    "grass_side.png": "mods/default/textures/default_grass_side.png",
    "dirt.png": "mods/default/textures/default_dirt.png",
    "stone.png": "mods/default/textures/default_stone.png",
    "cobble.png": "mods/default/textures/default_cobble.png",
    "wood_side.png": "mods/default/textures/default_tree.png",
    "wood_top.png": "mods/default/textures/default_tree_top.png",
    "planks.png": "mods/default/textures/default_wood.png",
    "leaves.png": "mods/default/textures/default_leaves_simple.png",
    "sand.png": "mods/default/textures/default_sand.png",
    "sandstone.png": "mods/default/textures/default_sandstone.png",
    "water.png": "mods/default/textures/default_water.png",
    "glass.png": "mods/default/textures/default_glass.png",
    "brick.png": "mods/default/textures/default_brick.png",
    "coal_ore.png": "mods/default/textures/default_mineral_coal.png",
    "iron_ore.png": "mods/default/textures/default_mineral_iron.png",
    "gold_ore.png": "mods/default/textures/default_mineral_gold.png",
    "diamond_ore.png": "mods/default/textures/default_mineral_diamond.png",
    "glowstone.png": "mods/default/textures/default_meselamp.png",
    "bedrock.png": "mods/default/textures/default_obsidian.png",
    "snow.png": "mods/default/textures/default_snow.png",
    "tnt_side.png": "mods/tnt/textures/tnt_side.png",
    "tnt_top.png": "mods/tnt/textures/tnt_top.png",
    "craft_top.png": "mods/default/textures/default_chest_top.png",
    "craft_side.png": "mods/default/textures/default_chest_side.png",
    "furnace_front.png": "mods/default/textures/default_furnace_front.png",
    "furnace_front_active.png": "mods/default/textures/default_furnace_front_active.png",
    "furnace_side.png": "mods/default/textures/default_furnace_side.png",
    "chest_front.png": "mods/default/textures/default_chest_front.png",
    "cactus_side.png": "mods/default/textures/default_cactus_side.png",
    "cactus_top.png": "mods/default/textures/default_cactus_top.png",
    "torch.png": "mods/default/textures/default_torch_on_floor.png",
    "stick.png": "mods/default/textures/default_stick.png",
    "coal.png": "mods/default/textures/default_coal_lump.png",
    "iron_ingot.png": "mods/default/textures/default_steel_ingot.png",
    "gold_ingot.png": "mods/default/textures/default_gold_ingot.png",
    "diamond.png": "mods/default/textures/default_diamond.png",
    "apple.png": "mods/default/textures/default_apple.png",
    "bread.png": "mods/farming/textures/farming_bread.png",
    "wood_pick.png": "mods/default/textures/default_tool_woodpick.png",
    "stone_pick.png": "mods/default/textures/default_tool_stonepick.png",
    "iron_pick.png": "mods/default/textures/default_tool_steelpick.png",
    "diamond_pick.png": "mods/default/textures/default_tool_diamondpick.png",
    "wood_sword.png": "mods/default/textures/default_tool_woodsword.png",
    "stone_sword.png": "mods/default/textures/default_tool_stonesword.png",
    "iron_sword.png": "mods/default/textures/default_tool_steelsword.png",
    "diamond_sword.png": "mods/default/textures/default_tool_diamondsword.png",
    "crack.png": "mods/default/textures/crack_anylength.png",
    "obsidian.png": "mods/default/textures/default_obsidian.png",
    "mossycobble.png": "mods/default/textures/default_mossycobble.png",
    "bookshelf.png": "mods/default/textures/default_bookshelf.png",
    "lava.png": "mods/default/textures/default_lava.png",
    "gravel.png": "mods/default/textures/default_gravel.png",
    "ice.png": "mods/default/textures/default_ice.png",
    "gold_block.png": "mods/default/textures/default_gold_block.png",
    "iron_block.png": "mods/default/textures/default_steel_block.png",
    "diamond_block.png": "mods/default/textures/default_diamond_block.png",
    "wool_white.png": "mods/wool/textures/wool_white.png",
    "wool_red.png": "mods/wool/textures/wool_red.png",
    "wool_blue.png": "mods/wool/textures/wool_blue.png",
    "wool_yellow.png": "mods/wool/textures/wool_yellow.png",
    "ladder.png": "mods/default/textures/default_ladder_wood.png",
    "door.png": "mods/doors/textures/doors_item_wood.png",
    "bed.png": "mods/beds/textures/beds_bed.png",
    "wood_axe.png": "mods/default/textures/default_tool_woodaxe.png",
    "iron_axe.png": "mods/default/textures/default_tool_steelaxe.png",
    "wood_shovel.png": "mods/default/textures/default_tool_woodshovel.png",
    "iron_shovel.png": "mods/default/textures/default_tool_steelshovel.png",
    "pine_wood.png": "mods/default/textures/default_pine_tree.png",
    "pine_wood_top.png": "mods/default/textures/default_pine_tree_top.png",
    "pine_leaves.png": "mods/default/textures/default_pine_needles.png",
    "birch_wood.png": "mods/default/textures/default_aspen_tree.png",
    "birch_wood_top.png": "mods/default/textures/default_aspen_tree_top.png",
    "birch_leaves.png": "mods/default/textures/default_aspen_leaves.png",
    "red_sandstone.png": "mods/default/textures/default_desert_stone.png",
    "terracotta.png": "mods/default/textures/default_desert_sandstone.png",
    "clay.png": "mods/default/textures/default_clay.png",
    "emerald_ore.png": "mods/default/textures/default_mineral_mese.png",
    "emerald_block.png": "mods/default/textures/default_mese_block.png",
    "emerald.png": "mods/default/textures/default_mese_crystal.png",
    "flower_red.png": "mods/flowers/textures/flowers_rose.png",
    "flower_yellow.png": "mods/flowers/textures/flowers_dandelion_yellow.png",
    "netherrack.png": "mods/default/textures/default_desert_cobble.png",
    "stone_axe.png": "mods/default/textures/default_tool_stoneaxe.png",
    "diamond_axe.png": "mods/default/textures/default_tool_diamondaxe.png",
    "stone_shovel.png": "mods/default/textures/default_tool_stoneshovel.png",
    "diamond_shovel.png": "mods/default/textures/default_tool_diamondshovel.png",
    "bucket_empty.png": "mods/bucket/textures/bucket.png",
    "bucket_water.png": "mods/bucket/textures/bucket_water.png",
    "bucket_lava.png": "mods/bucket/textures/bucket_lava.png",
    "flint.png": "mods/default/textures/default_flint.png",
}

SOUNDS = {
    "break": "mods/default/sounds/default_dig_crumbly.ogg",
    "break_stone": "mods/default/sounds/default_dig_cracky.1.ogg",
    "break_wood": "mods/default/sounds/default_dig_choppy.1.ogg",
    "place": "mods/default/sounds/default_place_node_hard.1.ogg",
    "step": "mods/default/sounds/default_grass_footstep.1.ogg",
    "hit": "mods/default/sounds/player_damage.ogg",
    "boom": "mods/tnt/sounds/tnt_explode.ogg",
    "ignite": "mods/tnt/sounds/tnt_ignite.ogg",
    "chest": "mods/default/sounds/default_chest_open.ogg",
    "glass": "mods/default/sounds/default_break_glass.1.ogg",
}


def download_all(root_dir=None):
    if root_dir is None:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tex_dir = os.path.join(root_dir, "assets", "textures")
    snd_dir = os.path.join(root_dir, "assets", "sounds")
    os.makedirs(tex_dir, exist_ok=True)
    os.makedirs(snd_dir, exist_ok=True)

    count = 0
    for local_name, rel_url in TEXTURES.items():
        dst = os.path.join(tex_dir, local_name)
        if not os.path.exists(dst):
            urllib.request.urlretrieve(BASE_RAW + rel_url, dst)
        count += 1

    ffmpeg_bin = shutil.which("ffmpeg")
    for stem, rel_url in SOUNDS.items():
        wav_dst = os.path.join(snd_dir, stem + ".wav")
        ogg_dst = os.path.join(snd_dir, stem + ".ogg")
        if not os.path.exists(wav_dst) and not os.path.exists(ogg_dst):
            urllib.request.urlretrieve(BASE_RAW + rel_url, ogg_dst)
            if ffmpeg_bin:
                subprocess.run(
                    [ffmpeg_bin, "-y", "-loglevel", "error", "-i", ogg_dst, "-ar", "44100", "-ac", "2", "-sample_fmt", "s16", wav_dst],
                    check=True,
                )
                os.remove(ogg_dst)
        count += 1

    lic_path = os.path.join(root_dir, "assets", "LICENSE.txt")
    with open(lic_path, "w") as f:
        f.write(
            "PyCraft External Assets\n"
            "Textures & sounds downloaded from luanti-org/minetest_game\n"
            "https://github.com/luanti-org/minetest_game (CC BY-SA 3.0 / CC0)\n"
        )
    print(f"Downloaded/verified {count} assets in {os.path.join(root_dir, 'assets')}")


if __name__ == "__main__":
    download_all()
