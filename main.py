#!/usr/bin/env python3
"""
PyCraft — Full-Scale 3D Minecraft Clone for Pydroid 3 & Desktop Python (Pure Pygame)
====================================================================================
Run this entry point in Pydroid 3 (or `python3 main.py` on desktop).
Flags:
  --horizontal Start in horizontal (landscape) mode (default)
  --vertical   Start in vertical (portrait) mode
"""

import os
import sys


def ensure_assets():
    """Auto-download external textures & sounds if the assets folder is missing."""
    root_dir = os.path.dirname(os.path.abspath(__file__))
    tex_dir = os.path.join(root_dir, "assets", "textures")
    if not os.path.isdir(tex_dir) or len(os.listdir(tex_dir)) < 10:
        try:
            from scripts.download_assets import download_all
            download_all(root_dir)
        except Exception:
            pass


def main():
    ensure_assets()
    start_vertical = ("--vertical" in sys.argv) and ("--horizontal" not in sys.argv)
    try:
        import pygame  # noqa: F401
    except ImportError:
        print("[PyCraft] Pygame is required to run PyCraft.")
        print("[PyCraft] In Pydroid 3: open Pip and install 'pygame', or run: pip install pygame")
        sys.exit(1)

    from pycraft.pygame_app import run_pygame
    run_pygame(start_vertical=start_vertical)


if __name__ == "__main__":
    main()
