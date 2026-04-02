#!/usr/bin/env python3
"""
Genera testbench/icon.png (512×512, RGB).

Por defecto: vector puro sobre azul Airbus #00205B (sin estrellas, sin cuadros, sin PNG raster ruidoso).

Uso opcional del maestro raster:
  python3 generate_icon.py --from-assets
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 512
AIRBUS_NAVY = (0, 32, 91)  # #00205B
ZOOM = 1.26
WHITE = (235, 238, 245)
WING_SHADE = (165, 185, 210)
COCKPIT = (210, 218, 230)
GREEN = (34, 197, 94)


def render_vector_icon(dst: Path) -> None:
    """Delta / transbordador estilizado, fondo completamente liso."""
    img = Image.new("RGB", (SIZE, SIZE), AIRBUS_NAVY)
    dr = ImageDraw.Draw(img)

    # Silueta principal (más grande, centrada)
    dr.polygon(
        [
            (256, 68),
            (108, 378),
            (188, 338),
            (256, 198),
            (324, 338),
            (404, 378),
        ],
        fill=WHITE,
    )
    # Acentos alares (sin textura tipo estrella)
    dr.polygon([(256, 95), (145, 318), (215, 322), (256, 205)], fill=WING_SHADE)
    dr.polygon([(256, 95), (367, 318), (297, 322), (256, 205)], fill=WING_SHADE)
    # Línea fuselaje / cabina
    dr.polygon([(256, 108), (232, 268), (256, 248), (280, 268)], fill=COCKPIT)

    # Badge V&V
    dr.rounded_rectangle([300, 300, 488, 488], radius=36, fill=GREEN)
    dr.line([(340, 372), (384, 418), (448, 338)], fill=(252, 252, 252), width=22, joint="curve")

    img.save(dst, format="PNG", optimize=True)


def render_from_source(src: Path, dst: Path) -> None:
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    nw = max(int(round(w * ZOOM)), SIZE)
    nh = max(int(round(h * ZOOM)), SIZE)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, (nw - SIZE) // 2)
    top = max(0, (nh - SIZE) // 2)
    im = im.crop((left, top, left + SIZE, top + SIZE))
    base = Image.new("RGB", (SIZE, SIZE), AIRBUS_NAVY)
    base.paste(im, (0, 0), mask=im.split()[3])
    drb = ImageDraw.Draw(base)
    e = 2
    b = AIRBUS_NAVY
    drb.rectangle([0, 0, SIZE, e], fill=b)
    drb.rectangle([0, SIZE - e, SIZE, SIZE], fill=b)
    drb.rectangle([0, 0, e, SIZE], fill=b)
    drb.rectangle([SIZE - e, 0, SIZE, SIZE], fill=b)
    base.save(dst, format="PNG", optimize=True)


def main() -> None:
    ddir = Path(__file__).resolve().parent
    src = ddir / "assets" / "icon_source.png"
    dst = ddir / "icon.png"
    use_assets = "--from-assets" in sys.argv

    if use_assets and src.is_file():
        render_from_source(src, dst)
    else:
        render_vector_icon(dst)
    print(dst)


if __name__ == "__main__":
    main()
