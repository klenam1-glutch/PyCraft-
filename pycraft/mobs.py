"""3D living mob entities (Spider, Zombie, Creeper, Skeleton, Pig, Cow, Sheep) and Arrow projectiles."""

import math
import random

from pycraft.constants import (
    AIR, ITEM_ARROW, ITEM_BREAD, ITEM_COAL, ITEM_IRON_INGOT, ITEM_RAW_MEAT, ITEM_STICK, LAVA, TNT,
)

MOB_STATS = {
    "pig": {"hostile": False, "hp": 10, "speed": 1.6, "body": (242, 162, 174), "head": (248, 174, 186), "leg": (222, 144, 156), "w": 0.65, "h": 0.85, "drop": ITEM_RAW_MEAT},
    "cow": {"hostile": False, "hp": 12, "speed": 1.4, "body": (92, 68, 52), "head": (118, 92, 74), "leg": (74, 54, 42), "w": 0.72, "h": 1.15, "drop": ITEM_RAW_MEAT},
    "sheep": {"hostile": False, "hp": 8, "speed": 1.5, "body": (236, 238, 242), "head": (214, 198, 182), "leg": (188, 172, 158), "w": 0.68, "h": 1.05, "drop": ITEM_RAW_MEAT},
    "zombie": {"hostile": True, "hp": 18, "speed": 2.35, "body": (54, 134, 168), "head": (82, 148, 72), "leg": (56, 72, 138), "w": 0.62, "h": 1.75, "drop": ITEM_IRON_INGOT, "dmg": 3},
    "creeper": {"hostile": True, "hp": 16, "speed": 2.45, "body": (68, 164, 62), "head": (78, 182, 72), "leg": (54, 136, 48), "w": 0.60, "h": 1.65, "drop": ITEM_COAL, "dmg": 0},
    "skeleton": {"hostile": True, "hp": 15, "speed": 2.25, "body": (212, 214, 218), "head": (228, 230, 234), "leg": (186, 188, 192), "w": 0.58, "h": 1.75, "drop": ITEM_ARROW, "dmg": 3},
    "spider": {"hostile": True, "hp": 14, "speed": 3.05, "body": (44, 38, 42), "head": (34, 28, 32), "leg": (28, 24, 28), "w": 0.85, "h": 0.65, "drop": ITEM_BREAD, "dmg": 2},
}


class Arrow:
    __slots__ = ("x", "y", "z", "vx", "vy", "vz", "ttl")

    def __init__(self, x, y, z, vx, vy, vz):
        self.x = x
        self.y = y
        self.z = z
        self.vx = vx
        self.vy = vy
        self.vz = vz
        self.ttl = 2.6


class Mob:
    __slots__ = ("kind", "x", "y", "z", "vy", "yaw", "hp", "max_hp", "hurt_timer", "ai_timer", "atk_cd", "fuse", "walk_phase", "on_ground")

    def __init__(self, kind, x, y, z):
        self.kind = kind
        st = MOB_STATS[kind]
        self.x = x
        self.y = y
        self.z = z
        self.vy = 0.0
        self.yaw = random.random() * math.tau
        self.hp = st["hp"]
        self.max_hp = st["hp"]
        self.hurt_timer = 0.0
        self.ai_timer = random.random() * 2.5
        self.atk_cd = 0.0
        self.fuse = -1.0
        self.walk_phase = random.random() * math.tau
        self.on_ground = False

    def update(self, world, player, dt, is_day, sound_bank):
        st = MOB_STATS[self.kind]
        if self.hurt_timer > 0:
            self.hurt_timer -= dt
        if self.atk_cd > 0:
            self.atk_cd -= dt

        dx = player.x - self.x
        dz = player.z - self.z
        dist_xz = math.hypot(dx, dz)

        if is_day and world.dimension == "overworld" and self.kind in ("zombie", "skeleton") and random.random() < dt * 0.45:
            self.hp -= 1
            self.hurt_timer = 0.25

        if world.get_block(int(math.floor(self.x)), int(math.floor(self.y)), int(math.floor(self.z))) == LAVA:
            self.hp -= dt * 8.0
            self.hurt_timer = 0.25

        if self.kind == "creeper":
            if dist_xz < 2.6 and abs(player.y - self.y) < 2.2 and not player.creative:
                if self.fuse < 0:
                    self.fuse = 1.35
                    sound_bank.play("ignite")
                else:
                    self.fuse -= dt
                    if self.fuse <= 0:
                        world.explode(int(math.floor(self.x)), int(math.floor(self.y)), int(math.floor(self.z)), 2.8)
                        sound_bank.play("boom")
                        if dist_xz < 4.5 and not player.creative:
                            raw_dmg = max(2, int(12 * (1.0 - dist_xz / 4.8)))
                            player.take_damage(raw_dmg, sound_bank)
                        self.hp = 0
                        return
            elif dist_xz > 4.2:
                self.fuse = -1.0

        move_spd = 0.0
        if st["hostile"] and not player.creative and dist_xz < 15.0:
            self.yaw = math.atan2(dx, dz)
            if dist_xz > 1.25:
                move_spd = st["speed"]
            elif self.kind != "creeper" and self.atk_cd <= 0 and abs(player.y - self.y) < 2.0:
                player.take_damage(st.get("dmg", 2), sound_bank)
                self.atk_cd = 1.0
        else:
            self.ai_timer -= dt
            if self.ai_timer <= 0:
                self.ai_timer = 1.5 + random.random() * 3.0
                if random.random() < 0.65:
                    self.yaw += (random.random() - 0.5) * 2.4
            if self.ai_timer > 0.8:
                move_spd = st["speed"] * (1.5 if self.hurt_timer > 0 else 0.75)

        if move_spd > 0:
            self.walk_phase += dt * move_spd * 4.5
            nx = self.x + math.sin(self.yaw) * move_spd * dt
            nz = self.z + math.cos(self.yaw) * move_spd * dt
            bx, by, bz = int(math.floor(nx)), int(math.floor(self.y)), int(math.floor(nz))
            blocked_low = world.is_solid(bx, by, bz)
            blocked_high = world.is_solid(bx, by + 1, bz)
            if not blocked_low and not blocked_high:
                self.x = nx
                self.z = nz
            elif blocked_low and not blocked_high and not world.is_solid(bx, by + 2, bz):
                if self.on_ground:
                    self.vy = 6.8
                    self.on_ground = False
            else:
                self.yaw += 1.6

        self.vy -= 20.0 * dt
        self.vy = max(-20.0, self.vy)
        ny = self.y + self.vy * dt
        by_check = int(math.floor(ny))
        bx0, bz0 = int(math.floor(self.x)), int(math.floor(self.z))
        if self.vy < 0 and world.is_solid(bx0, by_check, bz0):
            self.y = by_check + 1.001
            self.vy = 0.0
            self.on_ground = True
        elif self.vy > 0 and world.is_solid(bx0, int(math.floor(ny + st["h"])), bz0):
            self.vy = 0.0
        else:
            self.y = ny
            self.on_ground = False
