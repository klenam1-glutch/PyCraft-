"""3D DDA raycasting, AABB player physics, armor, drowning, ladders, ice, lava, and portals."""

import math

from pycraft.constants import AIR, CACTUS, ICE, LADDER, LAVA, WATER
from pycraft.inventory import Inventory
from pycraft.mobs import MOB_STATS


def raycast_block(world, ox, oy, oz, dx, dy, dz, max_dist=5.5):
    x = math.floor(ox)
    y = math.floor(oy)
    z = math.floor(oz)

    step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
    step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
    step_z = 1 if dz > 0 else (-1 if dz < 0 else 0)

    t_delta_x = abs(1.0 / dx) if dx != 0 else 1e9
    t_delta_y = abs(1.0 / dy) if dy != 0 else 1e9
    t_delta_z = abs(1.0 / dz) if dz != 0 else 1e9

    t_max_x = ((x + 1.0 - ox) * t_delta_x) if dx > 0 else ((ox - x) * t_delta_x if dx < 0 else 1e9)
    t_max_y = ((y + 1.0 - oy) * t_delta_y) if dy > 0 else ((oy - y) * t_delta_y if dy < 0 else 1e9)
    t_max_z = ((z + 1.0 - oz) * t_delta_z) if dz > 0 else ((oz - z) * t_delta_z if dz < 0 else 1e9)

    prev = None
    dist = 0.0
    while dist <= max_dist:
        bid = world.get_block(x, y, z)
        if bid != AIR and bid != WATER and bid != LAVA:
            return (x, y, z), prev, dist
        prev = (x, y, z)
        if t_max_x < t_max_y:
            if t_max_x < t_max_z:
                dist = t_max_x
                x += step_x
                t_max_x += t_delta_x
            else:
                dist = t_max_z
                z += step_z
                t_max_z += t_delta_z
        else:
            if t_max_y < t_max_z:
                dist = t_max_y
                y += step_y
                t_max_y += t_delta_y
            else:
                dist = t_max_z
                z += step_z
                t_max_z += t_delta_z
    return None, None, 999.0


def raycast_mob(world, ox, oy, oz, dx, dy, dz, max_dist=4.2):
    best_mob = None
    best_dist = max_dist
    for m in world.mobs:
        st = MOB_STATS[m.kind]
        mx = m.x - ox
        my = (m.y + st["h"] * 0.5) - oy
        mz = m.z - oz
        proj = mx * dx + my * dy + mz * dz
        if 0.2 <= proj <= best_dist:
            cx = ox + dx * proj
            cy = oy + dy * proj
            cz = oz + dz * proj
            if abs(cx - m.x) <= st["w"] * 0.75 and abs(cz - m.z) <= st["w"] * 0.75 and m.y - 0.1 <= cy <= m.y + st["h"] + 0.2:
                best_dist = proj
                best_mob = m
    return best_mob, best_dist


class Player:
    __slots__ = (
        "x", "y", "z", "vx", "vy", "vz", "yaw", "pitch",
        "on_ground", "in_water", "head_in_water", "in_lava", "on_ladder",
        "flying", "_creative",
        "health", "max_health", "hunger", "air", "armor",
        "hunger_timer", "regen_timer", "air_timer", "hazard_cd", "hurt_flash",
        "xp", "fall_start_y", "walk_bob", "swing_timer", "inv",
        "spawn_x", "spawn_y", "spawn_z", "sprinting",
    )

    def __init__(self, x=0.5, y=10.0, z=0.5, creative=False):
        self.x = x
        self.y = y
        self.z = z
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.yaw = 0.4
        self.pitch = -0.15
        self.on_ground = False
        self.in_water = False
        self.head_in_water = False
        self.in_lava = False
        self.on_ladder = False
        self.flying = creative
        self._creative = creative
        self.health = 20
        self.max_health = 20
        self.hunger = 20
        self.air = 20
        self.armor = 0
        self.hunger_timer = 0.0
        self.regen_timer = 0.0
        self.air_timer = 0.0
        self.hazard_cd = 0.0
        self.hurt_flash = 0.0
        self.xp = 0
        self.fall_start_y = y
        self.walk_bob = 0.0
        self.swing_timer = 0.0
        self.inv = Inventory(creative=creative)
        self.spawn_x = x
        self.spawn_y = y
        self.spawn_z = z
        self.sprinting = False

    @property
    def creative(self):
        return self._creative

    @creative.setter
    def creative(self, val):
        self._creative = bool(val)
        self.inv.creative = self._creative

    @property
    def eye_y(self):
        return self.y + 1.58

    @property
    def selected_item(self):
        return self.inv.selected_item

    def add_item(self, iid, cnt=1, record_collected=True):
        self.inv.add_item(iid, cnt, record_collected=record_collected)

    def take_damage(self, amount, sound_bank=None):
        if self._creative or amount <= 0:
            return
        mitigated = max(1, int(round(amount * (1.0 - min(0.75, self.armor * 0.035)))))
        self.health = max(0, self.health - mitigated)
        self.hurt_flash = 0.35
        if sound_bank:
            sound_bank.play("hit")

    def look_dir(self):
        cp = math.cos(self.pitch)
        return (
            math.sin(self.yaw) * cp,
            math.sin(self.pitch),
            math.cos(self.yaw) * cp,
        )

    def _collides_at(self, world, nx, ny, nz):
        r = 0.28
        h = 1.75
        for bx in range(math.floor(nx - r), math.floor(nx + r) + 1):
            for by in range(math.floor(ny), math.floor(ny + h) + 1):
                for bz in range(math.floor(nz - r), math.floor(nz + r) + 1):
                    if world.is_solid(bx, by, bz):
                        return True
        return False

    def overlaps_block(self, bx, by, bz):
        r = 0.28
        h = 1.75
        return (
            self.x + r > bx and self.x - r < bx + 1.0
            and self.y + h > by and self.y < by + 1.0
            and self.z + r > bz and self.z - r < bz + 1.0
        )

    def update(self, world, dt, move_fwd, move_right, jump, descend=False, sprint=False, sound_bank=None):
        dt = min(dt, 0.05)
        if self.swing_timer > 0:
            self.swing_timer = max(0.0, self.swing_timer - dt)
        if self.hurt_flash > 0:
            self.hurt_flash = max(0.0, self.hurt_flash - dt)
        if self.hazard_cd > 0:
            self.hazard_cd = max(0.0, self.hazard_cd - dt)

        fx = math.sin(self.yaw)
        fz = math.cos(self.yaw)
        rx = math.cos(self.yaw)
        rz = -math.sin(self.yaw)

        wish_x = fx * move_fwd + rx * move_right
        wish_z = fz * move_fwd + rz * move_right
        mag = math.hypot(wish_x, wish_z)
        if mag > 1.0:
            wish_x /= mag
            wish_z /= mag

        bx_f, by_f, bz_f = math.floor(self.x), math.floor(self.y + 0.2), math.floor(self.z)
        feet_bid = world.get_block(bx_f, by_f, bz_f)
        head_bid = world.get_block(bx_f, math.floor(self.eye_y), bz_f)
        below_bid = world.get_block(bx_f, math.floor(self.y - 0.1), bz_f)

        self.in_water = (feet_bid == WATER)
        self.head_in_water = (head_bid == WATER)
        self.in_lava = (feet_bid == LAVA or head_bid == LAVA)
        self.on_ladder = (feet_bid == LADDER or head_bid == LADDER)

        can_sprint = sprint and mag > 0.2 and (self.creative or self.hunger > 4)
        self.sprinting = can_sprint
        speed = 4.6 * (1.45 if can_sprint else 1.0)
        if self.flying:
            speed *= 1.65
        elif self.in_lava:
            speed *= 0.42
        elif self.in_water:
            speed *= 0.62
        elif below_bid == ICE and self.on_ground:
            speed *= 1.38

        if below_bid == ICE and self.on_ground and not self.flying:
            self.vx = self.vx * 0.90 + wish_x * speed * 0.12
            self.vz = self.vz * 0.90 + wish_z * speed * 0.12
        else:
            self.vx = wish_x * speed
            self.vz = wish_z * speed

        if mag > 0.1 and (self.on_ground or self.flying or self.on_ladder):
            self.walk_bob += dt * (11.5 if can_sprint else 8.0)

        if self.flying:
            self.vy = 6.5 if jump else (-6.5 if descend else 0.0)
            self.fall_start_y = self.y
        elif self.on_ladder:
            self.vy = 4.2 if (jump or move_fwd > 0.2) else (-3.2 if descend else 0.0)
            self.fall_start_y = self.y
        elif self.in_water or self.in_lava:
            self.vy -= 7.0 * dt
            if jump:
                self.vy = 3.9
            self.vy = max(-4.5, min(4.5, self.vy))
            self.fall_start_y = self.y
        else:
            self.vy -= 22.0 * dt
            self.vy = max(-24.0, self.vy)
            if jump and self.on_ground:
                self.vy = 7.9
                self.on_ground = False

        nx = self.x + self.vx * dt
        if not self._collides_at(world, nx, self.y, self.z):
            self.x = nx
        else:
            self.vx = 0.0

        nz = self.z + self.vz * dt
        if not self._collides_at(world, self.x, self.y, nz):
            self.z = nz
        else:
            self.vz = 0.0

        ny = self.y + self.vy * dt
        if not self._collides_at(world, self.x, ny, self.z):
            if self.vy < 0 and self.on_ground:
                self.fall_start_y = self.y
            self.y = ny
            self.on_ground = False
        else:
            if self.vy < 0:
                if not self.creative and not self.flying and not self.in_water and not self.on_ladder:
                    fall_dist = self.fall_start_y - self.y
                    if fall_dist > 3.6:
                        self.take_damage(int(fall_dist - 3.0), sound_bank)
                snap_y = math.floor(ny) + 1.001
                if not self._collides_at(world, self.x, snap_y, self.z):
                    self.y = snap_y
                self.on_ground = True
                self.fall_start_y = self.y
            self.vy = 0.0

        # Survival vitals: oxygen, lava/cactus hazards, hunger & regen
        if not self.creative:
            if self.head_in_water:
                self.air_timer += dt
                if self.air_timer >= 0.75:
                    self.air_timer = 0.0
                    if self.air > 0:
                        self.air -= 2
                    else:
                        self.take_damage(2, sound_bank)
            else:
                self.air = 20
                self.air_timer = 0.0

            if self.in_lava and self.hazard_cd <= 0.0:
                self.take_damage(4, sound_bank)
                self.hazard_cd = 0.65
            elif (below_bid == CACTUS or feet_bid == CACTUS) and self.hazard_cd <= 0.0:
                self.take_damage(1, sound_bank)
                self.hazard_cd = 0.75

            drain_rate = 0.025 + (0.045 if (mag > 0.2 and can_sprint) else 0.0)
            self.hunger_timer += dt * drain_rate
            if self.hunger_timer >= 1.0:
                self.hunger_timer = 0.0
                if self.hunger > 0:
                    self.hunger -= 1
                elif self.health > 1:
                    self.health -= 1
            if self.hunger >= 16 and self.health < self.max_health:
                self.regen_timer += dt
                if self.regen_timer >= 3.0:
                    self.regen_timer = 0.0
                    self.health = min(self.max_health, self.health + 1)

        if self.y < -6.0:
            self.y = world.get_surface_y(math.floor(self.x), math.floor(self.z)) + 1.0
            self.vy = 0.0
