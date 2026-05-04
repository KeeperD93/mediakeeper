"""Generate the PWA icon set from the source MediaKeeper logo.

The source PNG (frontend/public/assets/icons/mediakeeper.png) is a
transparent 2056x2044 logo. Chrome on Android requires square icons
in 192x192 and 512x512, plus a maskable variant.

All three icons are composed onto an opaque #030712 canvas matching
the manifest background_color. Pixel/AOSP launchers ignore the PWA
``purpose: maskable`` hint and paint a generic white square behind
non-opaque icons, so making the standard icons opaque too is the
only way to guarantee a dark background across launchers.

Safe zones:
- maskable: 80% (the OS may crop the outer 10% on each side to fit
  a circle, squircle or other launcher shape).
- standard 192/512: 90% (no cropping risk, but a 5% margin around
  the logo keeps it from touching the launcher's rounded corners).

Run from the repo root:  python scripts/generate_pwa_icons.py
"""
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
ICONS_DIR = REPO_ROOT / "frontend" / "public" / "assets" / "icons"
SOURCE = ICONS_DIR / "mediakeeper.png"

BACKGROUND = (3, 7, 18, 255)  # #030712 — matches manifest.background_color


def square_canvas(img: Image.Image, size: int, *, safe_zone: float) -> Image.Image:
    """Return an opaque square RGBA canvas of ``size`` px with ``img`` centered.

    ``safe_zone`` is the fraction of the canvas the logo is allowed to fill
    (e.g. 0.80 leaves a 10% margin on each side).
    """
    canvas = Image.new("RGBA", (size, size), BACKGROUND)

    inner = int(size * safe_zone)
    aspect = img.width / img.height
    if aspect >= 1:
        target_w = inner
        target_h = round(inner / aspect)
    else:
        target_h = inner
        target_w = round(inner * aspect)

    resized = img.resize((target_w, target_h), Image.LANCZOS)
    canvas.paste(resized, ((size - target_w) // 2, (size - target_h) // 2), resized)
    return canvas


def main() -> None:
    src = Image.open(SOURCE).convert("RGBA")

    outputs = [
        ("mediakeeper-192.png", 192, 0.90),
        ("mediakeeper-512.png", 512, 0.90),
        ("mediakeeper-maskable-512.png", 512, 0.80),
    ]
    for name, size, safe_zone in outputs:
        out = square_canvas(src, size, safe_zone=safe_zone)
        out.save(ICONS_DIR / name, format="PNG", optimize=True)
        print(f"wrote {ICONS_DIR / name} ({size}x{size}, safe_zone={safe_zone})")


if __name__ == "__main__":
    main()
