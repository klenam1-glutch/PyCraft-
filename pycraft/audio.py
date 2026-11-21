"""Universal WAV/OGG sound bank with Android/Pydroid 3 mixer pre-init and synth fallback."""

import io
import math
import os
import random
import struct
import wave

from pycraft.constants import get_assets_dir

SOUND_FILES = (
    "break", "break_stone", "break_wood", "place",
    "step", "hit", "boom", "ignite", "chest", "glass",
)


class SoundBank:
    __slots__ = ("enabled", "sounds", "_rain_channel")

    def __init__(self):
        self.enabled = True
        self.sounds = {}
        self._rain_channel = None

    @staticmethod
    def pre_init_pygame(pygame):
        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
        except Exception:
            pass

    def init_pygame(self, pygame):
        try:
            if not pygame.mixer.get_init():
                try:
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                except Exception:
                    pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
        except Exception:
            self.enabled = False
            return

        mixer_info = pygame.mixer.get_init()
        sr = mixer_info[0] if mixer_info else 44100
        channels = mixer_info[2] if mixer_info else 2

        snd_dir = os.path.join(get_assets_dir(), "sounds")
        for name in SOUND_FILES:
            loaded = None
            for ext in (".wav", ".ogg"):
                fpath = os.path.join(snd_dir, f"{name}{ext}")
                if os.path.exists(fpath):
                    try:
                        loaded = pygame.mixer.Sound(fpath)
                        break
                    except Exception:
                        loaded = None
            if loaded is None:
                if name in ("break", "break_stone", "break_wood"):
                    loaded = self._make_synth(pygame, sr, channels, 180, 0.09, noise=0.55, decay=18)
                elif name == "place":
                    loaded = self._make_synth(pygame, sr, channels, 340, 0.06, noise=0.15, decay=24)
                elif name == "boom":
                    loaded = self._make_synth(pygame, sr, channels, 68, 0.42, noise=0.85, decay=4.5)
                elif name == "step":
                    loaded = self._make_synth(pygame, sr, channels, 120, 0.05, noise=0.65, decay=28)
                else:
                    loaded = self._make_synth(pygame, sr, channels, 240, 0.08, noise=0.35, decay=16)
            if loaded is not None:
                loaded.set_volume(0.85)
                self.sounds[name] = loaded

        try:
            self.sounds["rain_loop"] = self._make_rain_loop(pygame, 22050, channels)
            self.sounds["thunder"] = self._make_thunder(pygame, 22050, channels)
        except Exception:
            pass

    def _pack_wav(self, pygame, sr, channels, samples):
        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(bytes(samples))
        bio.seek(0)
        return pygame.mixer.Sound(bio)

    def _make_rain_loop(self, pygame, sr, channels):
        n = int(sr * 1.1)
        buf = bytearray()
        lp = 0.0
        for i in range(n):
            wn = random.random() * 2.0 - 1.0
            lp = lp * 0.72 + wn * 0.28
            # Subtle droplet patter modulation + loop edge cross-taper
            patter = 0.65 if (i % 733) < 12 else 0.30
            s = max(-1.0, min(1.0, lp * 0.55 + wn * 0.22 * patter))
            val = int(s * 6800)
            if channels == 2:
                buf.extend(struct.pack("<hh", val, val))
            else:
                buf.extend(struct.pack("<h", val))
        return self._pack_wav(pygame, sr, channels, buf)

    def _make_thunder(self, pygame, sr, channels):
        n = int(sr * 0.85)
        buf = bytearray()
        lp = 0.0
        for i in range(n):
            t = i / sr
            crack = math.exp(-t * 18.0) * 0.55
            rumble = math.exp(-t * 2.6) * (0.65 + 0.35 * math.sin(t * 22.0))
            wn = random.random() * 2.0 - 1.0
            lp = lp * 0.86 + wn * 0.14
            low = math.sin(math.tau * (52.0 - t * 18.0) * t) * 0.45
            s = max(-1.0, min(1.0, (lp * 1.2 + low) * rumble + wn * crack))
            val = int(s * 22000)
            if channels == 2:
                buf.extend(struct.pack("<hh", val, val))
            else:
                buf.extend(struct.pack("<h", val))
        return self._pack_wav(pygame, sr, channels, buf)

    def _make_synth(self, pygame, sr, channels, freq, dur, noise=0.3, decay=12.0):
        n = int(sr * dur)
        buf = bytearray()
        for i in range(n):
            t = i / sr
            env = math.exp(-t * decay)
            tone = math.sin(math.tau * freq * t * (1.0 - t * 0.35))
            rnd = (random.random() * 2.0 - 1.0) * noise
            sample = max(-1.0, min(1.0, (tone * (1.0 - noise) + rnd) * env))
            val = int(sample * 15000)
            if channels == 2:
                buf.extend(struct.pack("<hh", val, val))
            else:
                buf.extend(struct.pack("<h", val))
        return self._pack_wav(pygame, sr, channels, buf)

    def update_rain_ambience(self, intensity, in_shelter=False):
        rain_snd = self.sounds.get("rain_loop")
        if not rain_snd:
            return
        target_vol = (intensity * (0.14 if in_shelter else 0.40)) if (self.enabled and intensity > 0.03) else 0.0
        try:
            if target_vol <= 0.01:
                if self._rain_channel and self._rain_channel.get_busy():
                    self._rain_channel.stop()
                return
            if self._rain_channel is None or not self._rain_channel.get_busy():
                self._rain_channel = rain_snd.play(loops=-1)
            if self._rain_channel:
                self._rain_channel.set_volume(target_vol)
        except Exception:
            pass

    def play(self, key, volume=0.85):
        if not self.enabled:
            return
        snd = self.sounds.get(key) or self.sounds.get("break")
        if snd:
            try:
                ch = snd.play()
                if ch:
                    ch.set_volume(volume)
            except Exception:
                pass
