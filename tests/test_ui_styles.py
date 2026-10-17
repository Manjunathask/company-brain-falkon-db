"""Regression checks for the desktop evidence panel flex sizing."""
from pathlib import Path
import re


def test_evidence_canvas_cannot_shrink_below_its_visible_height():
    css = (Path(__file__).resolve().parents[1] / "web" / "style.css").read_text(
        encoding="utf-8",
    )
    desktop_start = re.search(r"@media\s*\(min-width:\s*1024px\)", css)
    assert desktop_start
    desktop = css[desktop_start.start():]
    canvas = re.search(r"\.evidence\s+\.graph-canvas\s*\{(?P<rules>[^}]*)\}", desktop)
    assert canvas
    assert re.search(r"flex\s*:\s*0\s+0\s+auto\s*;", canvas["rules"])
    assert re.search(r"min-height\s*:\s*320px\s*;", canvas["rules"])

    evidence_text = re.search(
        r"\.evidence\s+\.evidence-text\s*\{(?P<rules>[^}]*)\}", desktop,
    )
    assert evidence_text
    assert re.search(r"min-height\s*:\s*0\s*;", evidence_text["rules"])
    assert re.search(r"overflow\s*:\s*auto\s*;", evidence_text["rules"])
