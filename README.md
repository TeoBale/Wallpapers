# 🎨 Wallpapers

A curated collection of desktop wallpapers, sorted by dominant color along the
color wheel so they flow as a visual gradient.

## Color Sorting

Images are numbered sequentially and ordered by hue:

🔴 Red → 🟠 Orange → 🟡 Yellow → 🟢 Green → 🩵 Cyan → 🔵 Blue → 🟣 Purple → 💜 Pink — with achromatic (grays) at the end.

### Re-sorting

A [`sort_by_color.py`](sort_by_color.py) script is included to re-analyse and
re-sort all images. It requires [uv](https://docs.astral.sh/uv/) — no manual
dependency installation needed.

```bash
# Preview the new ordering (dry-run, nothing is renamed)
uv run sort_by_color.py

# Apply the renaming
uv run sort_by_color.py --apply
```

### How it works

1. Each image is down-sampled to a thumbnail for speed
2. Pixel hues are averaged using a **circular mean** (weighted by saturation) to
   correctly handle the 0°/360° wrap-around
3. Images are sorted by hue, with low-saturation (gray/black/white) images
   pushed to the end
4. Files are renamed sequentially (`01.ext`, `02.ext`, …) via a temp directory
   to avoid collisions
