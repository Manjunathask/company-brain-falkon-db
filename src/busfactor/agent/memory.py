"""Per-user memory graphs. Cross-graph joins are performed here using stable Entity.key values."""
from __future__ import annotations

from datetime import datetime, timezone
import re
from threading import RLock

from busfactor.db import get_client, load_query

ENTITY_PREFIXES = {"Person": "person", "Component": "component", "Module": "module", "Decision": "decision"}
_DELETED_VISITORS: set[str] = set()
_DELETE_LOCK = RLock()


def mark_visitor_deleted(user: str) -> None:
    with _DELETE_LOCK:
        _DELETED_VISITORS.add(user)


def record_episode_if_live(memory, user: str, *args) -> bool:
    """Best-effort in-process guard against an in-flight ask recreating deleted history."""
    with _DELETE_LOCK:
        if user in _DELETED_VISITORS:
            return False
        memory.record_episode(*args)
        return True


def memory_graph_name(user: str) -> str:
    if not (re.fullmatch(r"[A-Za-z0-9_-]{1,39}", user) or re.fullmatch(r"v_[0-9a-f]{32}", user)):
        raise ValueError("user must be a GitHub login or a short alphanumeric test name")
    return f"mem_{user.lower()}"


def entity_keys(graph: dict) -> list[str]:
    """Map supported Delta graph nodes to memory keys in one place."""
    keys = set()
    for node in graph.get("nodes", []):
        prefix = ENTITY_PREFIXES.get(node.get("label"))
        key = node.get("key")
        if prefix and key is not None:
            if prefix == "component" and str(key).endswith("/(test-resources)"):
                continue
            keys.add(f"{prefix}:{key}")
    return sorted(keys)


class Memory:
    def __init__(self, user: str, graph=None, team_memory=None):
        self.name = memory_graph_name(user)
        if graph is None:
            graph = get_client().select_graph(self.name)
            self.client = get_client()
        else:
            self.client = None
        self.graph = graph
        self.team_memory = team_memory

    def _run(self, name: str, params: dict) -> list[dict]:
        result = self.graph.query(load_query(name), params)
        columns = [head[1] for head in result.header]
        return [dict(zip(columns, row)) for row in result.result_set]

    def recall(self, keys: list[str] | None = None, *, delta_graph=None, now_ms: int | None = None) -> list[dict]:
        rows = self._run("14c_mem_recall", {"keys": keys or [], "limit": 10000})
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
        # A correction is shared as a user-provided claim; recall it by entity key
        # even when the current user's private graph has no matching episode.
        from busfactor.team_memory import TeamMemory, observation_label
        related_keys = keys or [row["entity"] for row in rows if row.get("entity")]
        team_rows = (self.team_memory or TeamMemory()).recall(related_keys)
        by_key = {}
        for item in team_rows:
            if item.get("kind") == "user_claim" and item.get("entity"):
                by_key.setdefault(item["entity"], []).append({
                    "text": item.get("text"), "source": item.get("source"), "ts": item.get("ts"),
                    "userProvided": True, "label": observation_label(item.get("kind")),
                })
        for row in rows:
            if row.get("entity") in by_key:
                row["teamClaims"] = by_key[row["entity"]]
        known = {row.get("entity") for row in rows}
        for key, claims in by_key.items():
            if key not in known:
                rows.append({"entity": key, "lastAsked": None, "earlierQuestions": [],
                             "corrections": [], "teamClaims": claims, "changedSinceLastAsked": []})
        return rows

    def recall_for_prompt(self, question: str, question_keys: list[str] | None = None,
                          *, delta_graph=None, limit: int = 8) -> list[dict]:
        """Return a compact, question-relevant slice; recall() remains complete for the API."""
        rows = [row for row in self.recall(delta_graph=delta_graph)
                if not (str(row.get("entity") or "").startswith("component:") and
                        str(row.get("entity") or "").endswith("/(test-resources)"))]
        question_folded = question.casefold()
        question_tokens = set(re.findall(r"[a-z0-9_-]+", question_folded))
        exact = set(question_keys or [])

        def rank(row):
            entity = str(row.get("entity") or "")
            raw = entity.partition(":")[2].casefold()
            tokens = set(re.findall(r"[a-z0-9_-]+", raw))
            matches = entity in exact or (raw and raw in question_folded) or bool((tokens - {"core", "files"}) & question_tokens)
            return (int(matches), int(row.get("lastAsked") or 0))

        selected = sorted(rows, key=rank, reverse=True)[:limit]
        compact = []
        for row in selected:
            item = dict(row)
            changes = item.get("changedSinceLastAsked") or []
            changes = [change for change in changes
                       if int(change.get("commitCount") or 0) > 0 or int(change.get("prCount") or 0) > 0]
            if changes:
                item["changedSinceLastAsked"] = changes
            else:
                item.pop("changedSinceLastAsked", None)
            item = {key: value for key, value in item.items() if value not in (None, [], {}, "")}
            compact.append(item)
        return compact

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
        from busfactor.team_memory import TeamMemory
        (self.team_memory or TeamMemory()).write_observation(agent=f"chat:{self.name[4:]}", text=text, ts=stamp,
                                                             kind="user_claim", source=source, key=key)
        return {"tool": "remember_correction", "params": {"key": key, "text": text, "source": source},
                "cypher": load_query("14b_mem_store_correction"), "rows": [row], "graph": {"nodes": [], "edges": []}}

    def snapshot(self) -> dict:
        return {"episodes": self._run("14c_mem_recall", {"keys": [], "limit": 1000})}

