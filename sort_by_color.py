# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pillow>=11.0",
# ]
# ///
"""
Sort wallpaper images by dominant color.

Extracts the dominant hue from each image, sorts them along the color wheel
(red → orange → yellow → green → cyan → blue → purple → pink), and renames
files sequentially (01.ext, 02.ext, …).

Usage:
    uv run sort_by_color.py            # dry-run (preview only)
    uv run sort_by_color.py --apply    # actually rename files
"""

from __future__ import annotations

import colorsys
import math
import os
import shutil
import sys
from pathlib import Path

from PIL import Image

# ─── Configuration ────────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
SAMPLE_SIZE = (150, 150)  # thumbnail size for faster processing


def dominant_color(path: Path) -> tuple[float, float, float]:
    """Return the dominant (H, S, V) of *path* by averaging pixel colors.

    We down-sample the image to a thumbnail, convert every pixel to HSV, and
    compute a circular mean of hue (weighted by saturation) so that the
    wrap-around at 0°/360° is handled correctly.  The result is a tuple
    ``(hue, saturation, value)`` with hue in [0, 360) and S/V in [0, 1].
    """
    with Image.open(path) as img:
        img = img.convert("RGB")
        img.thumbnail(SAMPLE_SIZE)
        pixels = list(img.get_flattened_data())

    sin_sum = 0.0
    cos_sum = 0.0
    sat_sum = 0.0
    val_sum = 0.0
    weight_total = 0.0

    for r, g, b in pixels:
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        # Weight by saturation so achromatic pixels don't skew the hue
        w = s + 0.01  # small epsilon so grays still count a little
        angle = h * 2 * math.pi  # hue as radians for circular mean
        sin_sum += math.sin(angle) * w
        cos_sum += math.cos(angle) * w
        sat_sum += s * w
        val_sum += v * w
        weight_total += w

    mean_hue_rad = math.atan2(sin_sum, cos_sum)
    mean_hue_deg = math.degrees(mean_hue_rad) % 360
    mean_sat = sat_sum / weight_total
    mean_val = val_sum / weight_total

    return (mean_hue_deg, mean_sat, mean_val)


def sort_key(hsv: tuple[float, float, float]) -> tuple[int, float, float]:
    """Return a sort key that groups grays separately and sorts chromatic
    images by hue.

    Achromatic images (low saturation) are pushed to the end and sorted
    by brightness so the chromatic rainbow comes first.
    """
    h, s, v = hsv
    if s < 0.10:
        # Achromatic – sort by value (dark → light) after all chromatic images
        return (1, v, 0.0)
    return (0, h, -s)


def hue_label(hsv: tuple[float, float, float]) -> str:
    """Human-readable color name for terminal output."""
    h, s, v = hsv
    if s < 0.10:
        if v < 0.3:
            return "black/dark gray"
        elif v < 0.7:
            return "gray"
        else:
            return "white/light gray"
    if h < 15 or h >= 345:
        return "red"
    elif h < 40:
        return "orange"
    elif h < 70:
        return "yellow"
    elif h < 160:
        return "green"
    elif h < 200:
        return "cyan"
    elif h < 260:
        return "blue"
    elif h < 290:
        return "purple"
    else:
        return "pink/magenta"


def collect_images(directory: Path) -> list[Path]:
    return sorted(
        p
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def main() -> None:
    apply = "--apply" in sys.argv
    script_dir = Path(__file__).resolve().parent
    images = collect_images(script_dir)

    if not images:
        print("No images found.")
        return

    print(f"Found {len(images)} images. Analysing dominant colors …\n")

    # Analyse
    entries: list[tuple[Path, tuple[float, float, float]]] = []
    for img_path in images:
        try:
            hsv = dominant_color(img_path)
            entries.append((img_path, hsv))
        except Exception as exc:
            print(f"  ⚠  skipping {img_path.name}: {exc}")

    # Sort
    entries.sort(key=lambda e: sort_key(e[1]))

    # Determine zero-padded width
    width = max(2, len(str(len(entries))))

    # Build rename plan (use a temp dir to avoid collisions)
    tmp_dir = script_dir / ".sort_tmp"
    rename_plan: list[tuple[Path, Path]] = []

    for idx, (old_path, hsv) in enumerate(entries, start=1):
        new_name = f"{idx:0{width}}{old_path.suffix.lower()}"
        new_path = script_dir / new_name
        rename_plan.append((old_path, new_path))
        marker = "→" if old_path.name != new_name else "="
        label = hue_label(hsv)
        h, s, v = hsv
        print(
            f"  {old_path.name:>40s}  {marker}  {new_name:<12s}  "
            f"H={h:5.1f}°  S={s:.2f}  V={v:.2f}  [{label}]"
        )

    if not apply:
        print(
            "\n✋ Dry-run complete. Re-run with --apply to rename files."
        )
        return

    # Execute renames via a temporary directory to avoid name collisions
    tmp_dir.mkdir(exist_ok=True)
    try:
        for old_path, new_path in rename_plan:
            shutil.move(str(old_path), str(tmp_dir / new_path.name))
        for _, new_path in rename_plan:
            shutil.move(str(tmp_dir / new_path.name), str(new_path))
    finally:
        if tmp_dir.exists():
            # Clean up any stragglers
            for f in tmp_dir.iterdir():
                shutil.move(str(f), str(script_dir / f.name))
            tmp_dir.rmdir()

    print(f"\n✅ Renamed {len(rename_plan)} files.")


if __name__ == "__main__":
    main()
