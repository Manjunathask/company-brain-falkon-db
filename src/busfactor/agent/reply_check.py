"""Flag names absent from this turn's context; never rewrite an answer or infer facts."""
from __future__ import annotations

import re

TOKEN = r"[\w./-]"
NUMBER = re.compile(
    r"(?:https?://github\.com/[^\s/]+/[^\s/]+/(?:pull|issues)/|"
    r"\b(?:PR|issue)\s*#?\s*|(?<!\w)#)(\d{3,})(?!\w)", re.IGNORECASE)
MENTION = re.compile(r"(?<![\w@./-])@([\w-]+)(?![\w/-])")


def _contains(text: str, name: str) -> bool:
    return bool(name and re.search(rf"(?<!{TOKEN}){re.escape(name)}(?!{TOKEN})", text, re.IGNORECASE))


def check_reply(answer: str, seen: str, names: list[dict]) -> dict:
    """Count distinct named references and report those absent from the supplied evidence text."""
    seen = seen.lower()
    found = {}

    def add(kind, name, supported, display=None):
        found.setdefault((kind, name.lower()), {"kind": kind, "text": display or name, "supported": supported})

    for match in NUMBER.finditer(answer):
        number = match[1]
        # "#n" rather than "PR #n": the same pattern matches issue numbers.
        add("pr", number, bool(re.search(rf"(?<!\w){re.escape(number)}(?!\w)", seen)), f"#{number}")
    for match in MENTION.finditer(answer):
        add("person", match[1], _contains(seen, match[1]))
    components = {row["name"].lower() for row in names if row["kind"] == "component"}
    for row in names:
        kind, name = row["kind"], row["name"]
        if kind == "person" and len(name) < 4:
            continue
        if _contains(answer, name):
            supported = _contains(seen, name)
            if kind == "decision":
                supported = supported or _contains(seen, row.get("alias") or "")
            add(kind, name, supported)
    for match in re.finditer(r"`([^`\n]+)`", answer):
        name = match[1].strip()
        if "/" in name and not re.match(r"(?:[a-z][a-z0-9+.-]*://|www\.)", name, re.IGNORECASE):
            kind = "component" if name.lower() in components else "path"
            add(kind, name, _contains(seen, name))
    return {"checked": len(found), "unmatched": [
        {"kind": item["kind"], "text": item["text"]} for item in found.values() if not item["supported"]]}
