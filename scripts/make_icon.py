#!/usr/bin/env python3
"""Build AppIcon.icns from assets/app-icon.png."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "assets" / "app-icon.png"


def main():
    dest = ROOT / "dist" / "AppIcon.icns"
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = Image.open(MASTER).convert("RGBA")
    if src.size != (1024, 1024):
        src = src.resize((1024, 1024), Image.Resampling.LANCZOS)
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "AppIcon.iconset"
        iconset.mkdir()
        for size in sizes:
            src.resize((size, size), Image.Resampling.LANCZOS).save(iconset / f"icon_{size}x{size}.png")
            if size <= 512:
                src.resize((size * 2, size * 2), Image.Resampling.LANCZOS).save(iconset / f"icon_{size}x{size}@2x.png")
        subprocess.check_call(["iconutil", "-c", "icns", "-o", str(dest), str(iconset)])
    print(dest)


if __name__ == "__main__":
    main()
