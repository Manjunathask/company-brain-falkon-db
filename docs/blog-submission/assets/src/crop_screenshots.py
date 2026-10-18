"""Crop the raw app captures (2x pixel density) into the article's screenshots. Crops only: nothing is drawn or edited.

Usage: python crop_screenshots.py <folder with raw captures>
The raw captures are copied unchanged to screenshots/originals/.
"""
import pathlib, shutil, sys
from PIL import Image

RAW = pathlib.Path(sys.argv[1])
ASSETS = pathlib.Path(__file__).resolve().parents[1]
OUT = ASSETS / "screenshots"
ORIG = OUT / "originals"
ORIG.mkdir(parents=True, exist_ok=True)

# (source capture, output name, crop box in image pixels: left, top, right, bottom)
CROPS = [
    ("01_landing_viewport.png", "s1-landing-headline.png", (320, 240, 1500, 1770)),
    ("03b_evidence_expanded_viewport.png", "s2-departure-no-other-author.png", (340, 180, 2540, 1720)),
    ("04_handover_before_full.png", "s3-handover-successor.png", (0, 0, 1740, 1720)),
    ("04_handover_before_full.png", "s4-handover-decisions-questions.png", (0, 1735, 1740, 3215)),
    ("05_handover_after_full.png", "s5-handover-after-note.png", (0, 0, 1740, 1490)),
    ("08_ask_answer_top.png", "s6-agent-reads-team-note.png", (350, 0, 1470, 1724)),
    ("09_ask_how_i_know.png", "s7-how-i-know-trace.png", (340, 20, 1480, 370)),
]
for src, name, box in CROPS:
    shutil.copy2(RAW / src, ORIG / src)
    img = Image.open(RAW / src).convert("RGB").crop(box)
    img.save(OUT / name, optimize=True)
    print(f"{name}: {img.width}x{img.height}, {(OUT / name).stat().st_size // 1024} KB")
