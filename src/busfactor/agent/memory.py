"""Per-user memory graphs. Cross-graph joins are performed here using stable Entity.key values."""
from __future__ import annotations

from datetime import datetime, timezone
import re

from busfactor.db import get_client, load_query

ENTITY_PREFIXES = {"Person": "person", "Component": "component", "Module": "module", "Decision": "decision"}


def memory_graph_name(user: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,39}", user):
        raise ValueError("user must be a GitHub login or a short alphanumeric test name")
    return f"mem_{user.lower()}"


def entity_keys(graph: dict) -> list[str]:
    """Map supported Delta graph nodes to memory keys in one place."""
    keys = set()
    for node in graph.get("nodes", []):
        prefix = ENTITY_PREFIXES.get(node.get("label"))
        key = node.get("key")
        if prefix and key is not None:
            keys.add(f"{prefix}:{key}")
    return sorted(keys)


class Memory:
    def __init__(self, user: str, graph=None):
        self.name = memory_graph_name(user)
        if graph is None:
            graph = get_client().select_graph(self.name)
            self.client = get_client()
        else:
            self.client = None
        self.graph = graph

    def _run(self, name: str, params: dict) -> list[dict]:
        result = self.graph.query(load_query(name), params)
        columns = [head[1] for head in result.header]
        return [dict(zip(columns, row)) for row in result.result_set]

    def recall(self, keys: list[str] | None = None, *, delta_graph=None, now_ms: int | None = None) -> list[dict]:
        rows = self._run("14c_mem_recall", {"keys": keys or [], "limit": 5})
        if delta_graph is None:
            from busfactor.db import get_graph
            delta_graph = get_graph()
        changed = []
        for row in rows:
            key, since = row.get("entity"), row.get("lastAsked")
            if key and since:
                prefix, sep, raw = key.partition(":")
                if sep and prefix in {"person", "component", "module", "decision"}:
                    result = delta_graph.ro_query(load_query("14d_changed_since"),
                                                  {"kind": prefix, "key": raw, "since": int(since)})
                    cols = [h[1] for h in result.header]
                    row["changedSinceLastAsked"] = [dict(zip(cols, r)) for r in result.result_set]
        return rows

    def record_episode(self, session_id: str, text: str, answer: str, tool_names: list[str], keys: list[str], ts: int | None = None) -> dict:
        stamp = ts or int(datetime.now(timezone.utc).timestamp() * 1000)
        return self._run("14_mem_record_episode", {"sessionId": session_id, "text": text, "ts": stamp,
                                                     "answer": answer, "tools": tool_names, "entityKeys": keys})[0]

    def store_correction(self, key: str, text: str, source: str = "user", ts: int | None = None) -> dict:
        if not any(key.startswith(prefix + ":") and len(key) > len(prefix) + 1
                   for prefix in ENTITY_PREFIXES.values()):
            raise ValueError("key must use person:, component:, module:, or decision:")
        stamp = ts or int(datetime.now(timezone.utc).timestamp() * 1000)
        row = self._run("14b_mem_store_correction", {"key": key, "text": text, "ts": stamp, "source": source})[0]
        return {"tool": "remember_correction", "params": {"key": key, "text": text, "source": source},
                "cypher": load_query("14b_mem_store_correction"), "rows": [row], "graph": {"nodes": [], "edges": []}}

    def snapshot(self) -> dict:
        return {"episodes": self._run("14c_mem_recall", {"keys": [], "limit": 1000})}

