"""Shared, deterministic team observations stored only in the mem_team graph."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib

from busfactor.db import get_client, load_query


class TeamMemory:
    def __init__(self, graph=None):
        self.graph = graph or get_client().select_graph("mem_team")

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
        return self._run("16b_team_recall", {"keys": keys or []})

    def record_refresh(self, *, ts: int, new_commits: int, new_prs: int,
                       observation_ids: list[str]) -> dict:
        run_id = f"refresh:{ts}"
        rows = self._run("16c_team_record_refresh", {
            "id": run_id, "ts": ts, "newCommits": new_commits, "newPRs": new_prs,
            "observationIds": observation_ids,
        })
        return rows[0] if rows else {"id": run_id, "ts": ts, "newCommits": new_commits,
                                      "newPRs": new_prs, "observations": 0}

    def snapshot(self, limit: int = 50) -> dict:
        row = self._run("16d_team_list", {"limit": limit})[0]
        row["observations"] = sorted(row.get("observations") or [], key=lambda item: item.get("ts") or 0, reverse=True)[:limit]
        row["refreshRuns"] = sorted(row.get("refreshRuns") or [], key=lambda item: item.get("ts") or 0, reverse=True)[:limit]
        return row
