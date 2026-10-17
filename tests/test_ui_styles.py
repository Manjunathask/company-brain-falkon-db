"""Regression checks for the desktop evidence panel flex sizing."""
from pathlib import Path
import re
from html.parser import HTMLParser


class ViewChildren(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.children = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        parent = self.stack[-1] if self.stack else None
        if parent in {"leave-view", "ask-view"}:
            self.children.setdefault(parent, []).append((tag, attrs.get("class", "")))
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(attrs.get("id"))

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()


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


def test_each_view_has_one_left_wrapper_and_evidence_sibling():
    root = Path(__file__).resolve().parents[1]
    parser = ViewChildren()
    parser.feed((root / "web" / "index.html").read_text(encoding="utf-8"))
    for view, wrapper in (("leave-view", "leave-column"), ("ask-view", "ask-column")):
        children = parser.children[view]
        assert len(children) == 2
        assert children[0][0] == "div" and wrapper in children[0][1].split()
        assert children[1][0] == "evidencepanel"
