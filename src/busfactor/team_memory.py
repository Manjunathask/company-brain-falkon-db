"""Shared, deterministic team observations stored only in the mem_team graph."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
import re

from busfactor.db import get_client, load_query

# Shared team memory graph; tests and UI checks can point it at a throwaway graph.
TEAM_GRAPH = os.getenv("BUSFACTOR_TEAM_GRAPH", "mem_team")
LABELS = {"user_claim": "Unverified visitor claim", "availability": "Unverified availability note",
          "handover": "Saved handover plan"}

# Refresh observations written before 17 Oct used departure risk codes ("orphaned", "at risk").
# Stored text is never edited; it is shown as a recent-author count instead.
_OLD_RISK_SENTENCE = re.compile(r"^Component (\S+) risk changed from (.+?) to (.+?)\.$")
_AUTHOR_COUNT = {"orphaned": "0", "no other author": "0", "at risk": "1", "one other author": "1", "covered": "2+"}


def observation_label(kind: str | None) -> str:
    """Say where a shared observation came from: a visitor's note, a saved handover, or a repository refresh."""
    return LABELS.get(kind or "", "From repository refresh")


def display_text(text: str | None) -> str | None:
    """Rewrite an old-style refresh risk sentence in recent-author terms; leave other text unchanged."""
    match = _OLD_RISK_SENTENCE.match(text or "")
    if not match:
        return text
    component, old, new = match.groups()
    old, new = (_AUTHOR_COUNT.get(value.lower(), value) for value in (old, new))
    return f"Component {component} recent authors changed from {old} to {new}."


class TeamMemory:
    def __init__(self, graph=None):
        self.graph = graph or get_client().select_graph(TEAM_GRAPH)

    def _run(self, name: str, params: dict) -> list[dict]:
        result = self.graph.query(load_query(name), params)
        columns = [header[1] for header in result.header]
        return [dict(zip(columns, row)) for row in result.result_set]

    @staticmethod
    def observation_id(agent: str, text: str, ts: int, kind: str, key: str) -> str:
        raw = f"{agent}\0{text}\0{ts}\0{kind}\0{key}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def write_observation(self, *, agent: str, text: str, ts: int | None = None,
                          kind: str, source: str, key: str) -> dict:
        stamp = ts or int(datetime.now(timezone.utc).timestamp() * 1000)
        observation_id = self.observation_id(agent, text, stamp, kind, key)
        return self._run("16_team_write_observation", {
            "id": observation_id, "agent": agent, "text": text, "ts": stamp,
            "kind": kind, "source": source, "key": key,
        })[0]

    def recall(self, keys: list[str] | None = None) -> list[dict]:
        return [{**row, "text": display_text(row.get("text"))}
                for row in self._run("16b_team_recall", {"keys": keys or []})]

    def record_refresh(self, *, ts: int, new_commits: int, new_prs: int,
                       observation_ids: list[str]) -> dict:
        run_id = f"refresh:{ts}"
        rows = self._run("16c_team_record_refresh", {
            "id": run_id, "ts": ts, "newCommits": new_commits, "newPRs": new_prs,
            "observationIds": observation_ids,
        })
        return rows[0] if rows else {"id": run_id, "ts": ts, "newCommits": new_commits,
                                      "newPRs": new_prs, "observations": 0}

    def write_availability(self, *, agent: str, login: str, status: str, reason: str, source: str,
                           ts: int | None = None) -> dict:
        stamp = ts or int(datetime.now(timezone.utc).timestamp() * 1000)
        key = f"person:{login}"
        text = f"{login} is {status} for handover work: {reason}".rstrip(": ")
        return self._run("16e_team_write_availability", {
            "id": self.observation_id(agent, text, stamp, "availability", key), "agent": agent, "key": key,
            "status": status, "reason": reason, "text": text, "ts": stamp, "source": source,
        })[0]

    def availability(self) -> dict[str, dict]:
        """Latest availability note per login."""
        return {row["entity"][len("person:"):]: row for row in self._run("16f_team_availability", {})
                if str(row.get("entity", "")).startswith("person:")}

    def write_handover(self, *, agent: str, login: str, component: str, candidate: str | None, source: str,
                       ts: int | None = None) -> dict:
        stamp = ts or int(datetime.now(timezone.utc).timestamp() * 1000)
        key = f"component:{component}"
        text = f"Handover plan for {component} if {login} leaves: suggested successor {candidate or 'none'}."
        return self._run("16g_team_write_handover", {
            "id": self.observation_id(agent, text, stamp, "handover", key), "agent": agent, "key": key,
            "person": login, "candidate": candidate, "text": text, "ts": stamp, "source": source,
        })[0]

    def last_handover(self, login: str, component: str) -> dict | None:
        rows = self._run("16h_team_last_handover", {"key": f"component:{component}", "person": login})
        return rows[0] if rows else None

    def snapshot(self, limit: int = 50) -> dict:
        row = self._run("16d_team_list", {"limit": limit})[0]
        row["observations"] = [{**item, "text": display_text(item.get("text")), "label": observation_label(item.get("kind"))}
                               for item in
                               sorted(row.get("observations") or [], key=lambda item: item.get("ts") or 0, reverse=True)[:limit]]
        row["refreshRuns"] = [{**run, "observations": [display_text(text) for text in run.get("observations") or []]}
                              for run in sorted(row.get("refreshRuns") or [], key=lambda item: item.get("ts") or 0, reverse=True)[:limit]]
        return row
