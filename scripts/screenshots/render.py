"""Render the pictures of the README cards (docs/images) with headless Chrome.

Needs Pillow and Chrome (or Chromium). Run from anywhere:

    python scripts/screenshots/render.py

The cards are those of custom_components/synology_srm_plus/www, shown with the
neutral sample data of preview.html. Only the pictures of the cards that carry
sample data of their own are made here: router-card, router-card-details and
clients-card.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "docs" / "images"
CANDIDATES = [
    "google-chrome", "chromium", "chrome",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_chrome() -> str:
    for candidate in CANDIDATES:
        found = shutil.which(candidate) or (candidate if Path(candidate).exists() else None)
        if found:
            return found
    sys.exit("Chrome or Chromium not found")


def run(chrome: str, card: str, *flags: str) -> str:
    url = (HERE / "preview.html").as_uri() + f"?card={card}"
    profile = tempfile.mkdtemp(prefix="srm-shot-")
    try:
        done = subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
             f"--user-data-dir={profile}", "--allow-file-access-from-files", "--virtual-time-budget=3000", *flags, url],
            capture_output=True, text=True, timeout=120, check=False,
        )
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    return done.stdout


def measure(chrome: str, card: str) -> tuple[int, dict[str, int]]:
    dom = run(chrome, card, "--dump-dom")
    height = int(re.search(r'data-h="(\d+)"', dom).group(1))
    sections = json.loads(html.unescape(re.search(r'data-sections="([^"]*)"', dom).group(1)))
    return height, {title: y for title, y in sections}


def shoot(chrome: str, card: str, width: int, height: int, target: Path) -> Image.Image:
    run(chrome, card, f"--screenshot={target}", f"--window-size={width},{height}")
    return Image.open(target).convert("RGB")


def main() -> None:
    chrome = find_chrome()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        height, sections = measure(chrome, "router")
        full = shoot(chrome, "router", 490, height + 16, tmp_path / "router.png")
        cut = max(sections.get("Network", height // 2) - 8, 1)
        full.crop((0, 0, 490, cut)).save(OUT / "router-card.png")
        full.crop((0, cut, 490, height)).save(OUT / "router-card-details.png")

        height, _ = measure(chrome, "clients")
        shoot(chrome, "clients", 540, height + 16, tmp_path / "clients.png").crop((0, 0, 540, height)).save(OUT / "clients-card.png")
    for name in ("router-card", "router-card-details", "clients-card"):
        print(name, Image.open(OUT / f"{name}.png").size)


if __name__ == "__main__":
    main()
