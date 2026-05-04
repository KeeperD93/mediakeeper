"""Generate the PWA icon set from the source MediaKeeper logo.

The source PNG (frontend/public/assets/icons/mediakeeper.png) is a
transparent 2056x2044 logo. Chrome on Android requires square icons
in 192x192 and 512x512, plus a properly composed maskable variant
with an opaque background and a safe zone (logo confined to the
inner 80% of the canvas — the OS may crop the outer 10% on each side
to fit a circle, squircle or other launcher shape).

Run from the repo root:  python scripts/generate_pwa_icons.py
"""
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
ICONS_DIR = REPO_ROOT / "frontend" / "public" / "assets" / "icons"
SOURCE = ICONS_DIR / "mediakeeper.png"

# Theme-aligned background color: matches manifest.background_color and
# the portal dark surface. Logo composed onto this color for the
# maskable variant so launchers stop painting their own fallback.
BACKGROUND = (3, 7, 18, 255)  # #030712


def square_canvas(img: Image.Image, size: int, *, opaque: bool = False) -> Image.Image:
    """Return a square RGBA canvas of `size`px with `img` centered.

    When ``opaque`` is True, the canvas is filled with BACKGROUND and
    the logo is shrunk to 80% of the canvas to leave a safe zone for
    maskable cropping. Otherwise the canvas is fully transparent and
    the logo fills the canvas (preserving aspect ratio).
    """
    canvas = Image.new("RGBA", (size, size), BACKGROUND if opaque else (0, 0, 0, 0))

    inner = int(size * 0.8) if opaque else size
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
        ("mediakeeper-192.png", 192, False),
        ("mediakeeper-512.png", 512, False),
        ("mediakeeper-maskable-512.png", 512, True),
    ]
    for name, size, opaque in outputs:
        out = square_canvas(src, size, opaque=opaque)
        out.save(ICONS_DIR / name, format="PNG", optimize=True)
        print(f"wrote {ICONS_DIR / name} ({size}x{size}, opaque={opaque})")


if __name__ == "__main__":
    main()
