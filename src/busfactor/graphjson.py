"""Convert FalkorDB node and relationship values into UI evidence dictionaries."""
from __future__ import annotations

from typing import Any


def node_dict(node: Any) -> dict | None:
    if node is None:
        return None
    props = getattr(node, "properties", {}) or {}
    labels = getattr(node, "labels", ()) or ()
    label = sorted(labels)[0] if labels else "Node"
    identity = getattr(node, "id", None)
    key_name = {"Person": "login", "Module": "name", "Component": "name", "Decision": "slug", "File": "path", "PR": "number", "Issue": "number", "Commit": "sha"}.get(label)
    return {"id": identity, "label": label, "key": props.get(key_name) if key_name else None, "props": dict(props)}


def rel_dict(rel: Any) -> dict | None:
    if rel is None:
        return None
    props = getattr(rel, "properties", {}) or {}
    start = getattr(rel, "src_node", None)
    end = getattr(rel, "dest_node", None)
    return {
        "source": getattr(start, "id", start),
        "target": getattr(end, "id", end),
        "type": getattr(rel, "relation", getattr(rel, "type", "RELATED")),
        "props": dict(props),
    }
