"""Build the article's figures: generate the data-driven hero SVG, then render every assets/*.svg to a 2x PNG.

Run with a Python that has playwright and pillow installed (no project dependency is added):
    python -m uv run --no-project --with playwright --with pillow python build_visuals.py
Playwright drives the locally installed Microsoft Edge (channel="msedge"), so no browser download is needed.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
from collections import defaultdict

ASSETS = pathlib.Path(__file__).resolve().parents[1]
SRC = ASSETS / "src"
FONTS = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700"
         "&family=JetBrains+Mono:wght@400;500&display=swap")
FONT_IMPORT = f"@import url('{FONTS.replace('&', '&amp;')}');"


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def make_hero() -> pathlib.Path:
    """Radial map of the 69 reportable code areas and the person who wrote most of each one's recent commits."""
    data = json.loads((SRC / "hero-data.json").read_text(encoding="utf-8"))
    areas = sorted(data["areas"], key=lambda a: (a["component"].split("/")[0], a["component"]))
    W, H = 1600, 840
    cx, cy, r_area = 1135, 420, 330
    n = len(areas)
    angle = {}
    for i, area in enumerate(areas):
        angle[area["component"]] = -math.pi / 2 + 2 * math.pi * i / n

    # People: every top author, placed at the circular mean of the areas they top.
    held = defaultdict(list)
    for area in areas:
        held[area["topExpert"]].append(area)
    people = []
    for login, mine in held.items():
        sx = sum(math.cos(angle[a["component"]]) for a in mine)
        sy = sum(math.sin(angle[a["component"]]) for a in mine)
        ones = sum(1 for a in mine if a["busFactor"] == 1)
        people.append({"login": login, "theta": math.atan2(sy, sx), "areas": len(mine), "ones": ones})
    # Spread people that would overlap: relax angles around the circle.
    people.sort(key=lambda p: p["theta"])
    min_gap = 2 * math.pi / (len(people) * 1.25)
    for _ in range(200):
        moved = False
        for i in range(len(people)):
            a, b = people[i], people[(i + 1) % len(people)]
            gap = (b["theta"] - a["theta"]) % (2 * math.pi)
            if gap < min_gap:
                push = (min_gap - gap) / 2
                a["theta"] -= push
                b["theta"] += push
                moved = True
        if not moved:
            break
    for p in people:
        radius = 150 if p["ones"] >= 2 else 205 if p["ones"] == 1 else 245
        p["x"], p["y"] = cx + radius * math.cos(p["theta"]), cy + radius * math.sin(p["theta"])
        p["r"] = 7 + 4.5 * p["ones"] if p["ones"] else 6
    where = {p["login"]: p for p in people}

    lines, squares, dots = [], [], []
    for area in areas:
        t = angle[area["component"]]
        ax, ay = cx + r_area * math.cos(t), cy + r_area * math.sin(t)
        p = where[area["topExpert"]]
        one = area["busFactor"] == 1
        # Gentle curve towards the centre so lines read as a fan, not a hairball.
        mx, my = cx + (r_area * 0.55) * math.cos(t), cy + (r_area * 0.55) * math.sin(t)
        cls = "link one" if one else "link many"
        lines.append(f'<path class="{cls}" d="M{ax:.1f},{ay:.1f} Q{mx:.1f},{my:.1f} {p["x"]:.1f},{p["y"]:.1f}"/>')
        size = 15
        rot = math.degrees(t)
        squares.append(
            f'<rect class="{"area one" if one else "area many"}" x="{ax - size / 2:.1f}" y="{ay - size / 2:.1f}" '
            f'width="{size}" height="{size}" rx="3" transform="rotate({rot:.1f} {ax:.1f} {ay:.1f})">'
            f'<title>{esc(area["component"])}: bus factor {area["busFactor"]}</title></rect>')
    for p in people:
        cls = "person one" if p["ones"] else "person many"
        dots.append(f'<circle class="{cls}" cx="{p["x"]:.1f}" cy="{p["y"]:.1f}" r="{p["r"]:.1f}"/>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img"
  aria-labelledby="t d">
  <title id="t">Knowledge concentration in Delta Lake</title>
  <desc id="d">A radial map of the 69 code areas in delta-io/delta with enough recent activity to measure. Each square is
  a code area, each circle a person, and a line joins each area to the person who wrote most of its commits in the
  last 12 months. The 25 areas where one person wrote at least half of those commits are highlighted.</desc>
  <style>
    {FONT_IMPORT}
    .bg {{ fill: #12151C; }}
    .ring {{ fill: none; stroke: #232836; stroke-width: 1.5; }}
    .link {{ fill: none; stroke-linecap: round; }}
    .link.one {{ stroke: #F26B3A; stroke-width: 2.2; opacity: .85; }}
    .link.many {{ stroke: #5B6478; stroke-width: 1.2; opacity: .55; }}
    .area.one {{ fill: #F26B3A; }}
    .area.many {{ fill: #12151C; stroke: #7C869B; stroke-width: 1.6; }}
    .person.one {{ fill: #FFB38F; stroke: #12151C; stroke-width: 2; }}
    .person.many {{ fill: #12151C; stroke: #9AA3B5; stroke-width: 1.6; }}
    .kicker {{ font: 600 19px Inter, 'Segoe UI', sans-serif; letter-spacing: .14em; fill: #7FD1C6; }}
    .title {{ font: 700 54px Inter, 'Segoe UI', sans-serif; fill: #F5F2EC; letter-spacing: -.01em; }}
    .title .hot {{ fill: #FF8A5B; }}
    .body {{ font: 400 23px Inter, 'Segoe UI', sans-serif; fill: #AEB6C6; }}
    .legend {{ font: 500 20px Inter, 'Segoe UI', sans-serif; fill: #D6DAE3; }}
    .foot {{ font: 400 17px 'JetBrains Mono', Consolas, monospace; fill: #6F798D; }}
  </style>
  <rect class="bg" width="{W}" height="{H}"/>
  <circle class="ring" cx="{cx}" cy="{cy}" r="{r_area}"/>
  <g>{''.join(lines)}</g>
  <g>{''.join(squares)}</g>
  <g>{''.join(dots)}</g>
  <text class="kicker" x="96" y="196">DELTA LAKE · LAST 12 MONTHS</text>
  <text class="title" x="96" y="276"><tspan class="hot">25 of 69</tspan> active code</text>
  <text class="title" x="96" y="342">areas have one person</text>
  <text class="title" x="96" y="408">behind at least half of</text>
  <text class="title" x="96" y="474">their recent commits.</text>
  <text class="body" x="96" y="540">Each square is a code area; each circle, a person.</text>
  <text class="body" x="96" y="574">A line joins an area to its most active recent author.</text>
  <rect x="98" y="622" width="15" height="15" rx="3" fill="#F26B3A"/>
  <text class="legend" x="126" y="637">one person wrote at least half</text>
  <rect x="98" y="660" width="15" height="15" rx="3" fill="#12151C" stroke="#7C869B" stroke-width="1.6"/>
  <text class="legend" x="126" y="675">more people share the work</text>
  <text class="foot" x="96" y="760">Source: public delta-io/delta history · 05b_bus_factor_component.cypher · {data['checked_at'][:10]}</text>
</svg>
"""
    path = ASSETS / "01-hero-knowledge-concentration.svg"
    path.write_text(svg, encoding="utf-8")
    return path


def render(svgs: list[pathlib.Path], scale: int = 2) -> None:
    """Render each SVG inline (so web fonts apply) and save a PNG next to it, then optimise the PNG."""
    from playwright.sync_api import sync_playwright
    from PIL import Image

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(device_scale_factor=scale, viewport={"width": 1700, "height": 1200})
        for svg_path in svgs:
            markup = svg_path.read_text(encoding="utf-8")
            page.set_content(f'<html><head><link rel="stylesheet" href="{FONTS}"></head>'
                             f'<body style="margin:0;background:#fff">{markup}</body></html>')
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(400)
            png = svg_path.with_suffix(".png")
            page.locator("svg").first.screenshot(path=str(png))
            img = Image.open(png).convert("RGB")
            img.save(png, optimize=True)
            print(f"{png.name}: {img.width}x{img.height}, {png.stat().st_size // 1024} KB")
        browser.close()


if __name__ == "__main__":
    targets = sys.argv[1:]
    if not targets or "hero" in targets:
        make_hero()
    names = [t for t in targets if t != "hero"]
    svgs = sorted(ASSETS.glob("*.svg")) if not names else [ASSETS / n for n in names]
    if not names and targets == ["hero"]:
        svgs = [ASSETS / "01-hero-knowledge-concentration.svg"]
    render(svgs)
