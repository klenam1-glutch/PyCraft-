"""World persistence (JSON save/load across Overworld + Nether) and new game initialization."""

import json
import os

from pycraft.constants import get_save_path
from pycraft.inventory import Inventory
from pycraft.physics import Player
from pycraft.world import World


def save_game(world, player, time_of_day):
    path = get_save_path()
    data = {
        "seed": world.seed,
        "dimension": world.dimension,
        "time_of_day": time_of_day,
        "player": {
            "x": player.x, "y": player.y, "z": player.z,
            "yaw": player.yaw, "pitch": player.pitch,
            "flying": player.flying, "creative": player.creative,
            "health": player.health, "hunger": player.hunger,
            "armor": player.armor, "xp": player.xp,
            "spawn": [player.spawn_x, player.spawn_y, player.spawn_z],
            "inv_data": player.inv.to_dict(),
        },
        "chest": {str(k): v for k, v in world.chest_storage.items()},
        "modified": [[x, y, z, bid] for (x, y, z), bid in world.modified_dims["overworld"].items()],
        "modified_nether": [[x, y, z, bid] for (x, y, z), bid in world.modified_dims["nether"].items()],
    }
    with open(path, "w") as f:
        json.dump(data, f)
    return path


def load_game():
    path = get_save_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        world = World(seed=data.get("seed"), dimension=data.get("dimension", "overworld"))
        for x, y, z, bid in data.get("modified", []):
            world.modified_dims["overworld"][(x, y, z)] = bid
        for x, y, z, bid in data.get("modified_nether", []):
            world.modified_dims["nether"][(x, y, z)] = bid
        for k, v in data.get("chest", {}).items():
            world.chest_storage[int(k)] = v
        p_data = data.get("player", {})
        creative = p_data.get("creative", False)
        player = Player(
            x=p_data.get("x", 0.5), y=p_data.get("y", 10.0), z=p_data.get("z", 0.5),
            creative=creative,
        )
        player.yaw = p_data.get("yaw", 0.4)
        player.pitch = p_data.get("pitch", -0.15)
        player.flying = p_data.get("flying", creative)
        player.health = p_data.get("health", 20)
        player.hunger = p_data.get("hunger", 20)
        player.armor = p_data.get("armor", 0)
        player.xp = p_data.get("xp", 0)
        sp = p_data.get("spawn")
        if isinstance(sp, list) and len(sp) == 3:
            player.spawn_x, player.spawn_y, player.spawn_z = sp[0], sp[1], sp[2]
        if "inv_data" in p_data:
            player.inv = Inventory.from_dict(p_data["inv_data"], creative=creative)
        else:
            player.inv = Inventory.from_dict(p_data, creative=creative)
        world.ensure_chunks_around(player.x, player.z, 20, max_gen_per_frame=64)
        return world, player, data.get("time_of_day", 0.22)
    except Exception:
        return None


def create_new_game(creative=False):
    world = World()
    world.ensure_chunks_around(0.5, 0.5, 20, max_gen_per_frame=64)
    sy = world.get_surface_y(0, 0)
    player = Player(0.5, sy + 0.1, 0.5, creative=creative)
    return world, player, 0.22
