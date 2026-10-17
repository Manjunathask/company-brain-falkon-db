"""Incremental refresh fixture coverage plus an isolated team-memory graph integration test."""
from datetime import datetime, timezone
import json

import pytest

from busfactor import refresh
from busfactor.agent.loop import _first_user_message
from busfactor.db import load_query
from busfactor.team_memory import TeamMemory


def _commit(sha, ts, subject, email="alice@example.com", name="Alice", path="kernel/api.scala"):
    return f"\x1e{sha}\x1f{ts}\x1f{subject}\x1f{email}\x1f{name}\n1\t0\t{path}\n"


def test_refresh_commit_watermark_and_fixture_pr_pages():
    old = _commit("old", 900, "old change")
    fresh = _commit("fresh", 1100, "[Kernel] new change (#7)")
    commits = refresh.parse_new_commits(old + fresh, 1_000_000, ["kernel/api.scala"])
    assert [row["sha"] for row in commits] == ["fresh"]
    assert commits[0]["files"][0]["exists"] is True
    assert commits[0]["area"] == "kernel"

    pages = [
        {"nodes": [{"number": 7, "title": "fresh", "createdAt": "2026-10-16T00:00:00Z",
                    "updatedAt": "2026-10-16T02:00:00Z", "author": {"login": "alice"},
                    "reviews": {"nodes": []}}], "pageInfo": {"hasNextPage": True, "endCursor": "next"}},
        {"nodes": [{"number": 6, "title": "known", "createdAt": "2026-10-15T00:00:00Z",
                    "updatedAt": "2026-10-16T01:00:00Z", "author": {"login": "bob"},
                    "reviews": {"nodes": []}}], "pageInfo": {"hasNextPage": True, "endCursor": "known"}},
    ]
    calls = []
    def fetch(cursor, page):
        calls.append((cursor, page))
        return pages[page]
    watermark = int(datetime(2026, 10, 16, 1, 30, tzinfo=timezone.utc).timestamp() * 1000)
    rows = refresh.collect_updated_prs(fetch, watermark)
    assert [row["number"] for row in rows] == [7]
    assert calls == [(None, 0), ("next", 1)]


class _Result:
    def __init__(self, columns, rows):
        self.header = [(None, name) for name in columns]
        self.result_set = rows
        self.relationships_created = 0


class _FixtureGraph:
    def __init__(self):
        self.query_calls = []
        self.risk_reads = 0
        self.active_reads = 0
    def ro_query(self, query, params=None):
        if "newestCommit" in query:
            return _Result(["newestCommit", "newestPR"], [[1_000_000, 1_000_000]])
        if "MATCH (component:Component)" in query:
            self.risk_reads += 1
            return _Result(["component", "recentAuthors"], [["kernel/api", 0]]
                           if self.risk_reads == 1 else [["kernel/api", 2]])
        if "Person:Active" in query:
            self.active_reads += 1
            return _Result(["p.login"], [["alice"]] if self.active_reads == 1 else [])
        if "IMPLEMENTS" in query:
            return _Result(["pr.number", "d.slug", "d.title"], [[7, "fixture-decision", "Fixture decision"]])
        raise AssertionError(query)
    def query(self, query, params=None):
        self.query_calls.append((query, params or {}))
        return _Result([], [])


class _FixtureTeam:
    def __init__(self): self.observations = []; self.refresh = None
    def write_observation(self, **values):
        self.observations.append(values)
        return {"id": f"obs-{len(self.observations)}"}
    def record_refresh(self, **values): self.refresh = values


def test_refresh_runner_respects_watermarks_loads_only_new_and_writes_risk_observations(tmp_path, monkeypatch, capsys):
    graph, team = _FixtureGraph(), _FixtureTeam()
    monkeypatch.setattr(refresh, "RAW", tmp_path)
    def active_people(_graph):
        graph.active_reads += 1
        return {"alice"} if graph.active_reads == 1 else set()
    monkeypatch.setattr(refresh, "_active_people", active_people)
    monkeypatch.setattr(refresh.load, "_run_rows", lambda g, name, rows, label: g.query(load_query(name), {"rows": rows}))
    monkeypatch.setattr(refresh.link_decisions, "run", lambda _graph: None)
    monkeypatch.setattr(refresh.derive, "run_derive", lambda *_args, **_kwargs: None)
    pr_pages = [{"nodes": [{"number": 7, "title": "decision", "createdAt": "2026-10-16T00:00:00Z",
                             "updatedAt": "2026-10-16T02:00:00Z", "author": {"login": "alice"},
                             "reviews": {"nodes": []}}],
                 "pageInfo": {"hasNextPage": False}}]
    calls = []
    def fetch(cursor, page): calls.append(page); return pr_pages[page]
    result = refresh.run_refresh(graph=graph, repo=tmp_path, commit_output=_commit("old", 900, "old") +
                                _commit("new", 2000, "[Kernel] change (#7)", path="kernel/src/main/scala/io/delta/kernel/api/Api.scala"),
                                head_paths=["kernel/src/main/scala/io/delta/kernel/api/Api.scala"],
                                pr_page_fetcher=fetch, team_memory=team)
    assert result["newCommits"] == 1
    assert result["newPRs"] == 1
    assert result["riskChanges"] == [("kernel/api", "0", "2+")]
    assert team.observations[0]["text"] == "Component kernel/api recent authors changed from 0 to 2+."
    assert result["becameInactive"] == ["alice"]
    assert len(team.observations) == 3  # risk change, inactive person, decision activity
    assert team.refresh["new_commits"] == 1 and team.refresh["new_prs"] == 1
    assert any("MERGE (k:Commit" in query and len(params.get("rows", [])) == 1 for query, params in graph.query_calls)
    assert any("MERGE (pr:PR" in query and len(params.get("rows", [])) == 1 for query, params in graph.query_calls)
    output = capsys.readouterr().out
    assert "New commits: 1" in output and "kernel/api=1" in output


def test_changed_since_first_message_names_time_and_authors():
    stamp = int(datetime(2026, 10, 16, 18, 2, tzinfo=timezone.utc).timestamp() * 1000)
    content = _first_user_message("what changed?", "2026-10-16", [{
        "entity": "component:kernel/kernel-api", "lastAsked": stamp,
        "changedSinceLastAsked": [{"commitCount": 3, "commits": [{"author": "allisonport-db"}]}],
    }])
    local_stamp = datetime.fromtimestamp(stamp / 1000, timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    assert f"Since you last asked about component:kernel/kernel-api ({local_stamp}): 3 new commits by allisonport-db" in content


@pytest.mark.integration
def test_team_correction_cross_user_and_team_graph_integration():
    # The live integration fixture is supplied by the test module so both memory graphs are disposable.
    from falkordb import FalkorDB
    import os
    from redis.exceptions import RedisError, ResponseError
    client = FalkorDB(host=os.getenv("FALKORDB_HOST", "127.0.0.1"), port=int(os.getenv("FALKORDB_PORT", "6379")),
                      password=os.getenv("FALKORDB_PASSWORD") or None)
    names = ["mem_wp9_alice", "mem_wp9_bob", "mem_wp9_team"]
    try:
        client.connection.ping()
    except (RedisError, OSError, ConnectionError) as exc:
        pytest.skip(f"FalkorDB is unreachable: {exc}")
    try:
        for name in names:
            try: client.connection.execute_command("GRAPH.DELETE", name)
            except ResponseError: pass
        team = TeamMemory(client.select_graph(names[2]))
        alice = __import__("busfactor.agent.memory", fromlist=["Memory"]).Memory("wp9_alice", client.select_graph(names[0]), team)
        bob = __import__("busfactor.agent.memory", fromlist=["Memory"]).Memory("wp9_bob", client.select_graph(names[1]), team)
        assert team.recall() == []
        alice.store_correction("component:kernel/api", "Alice owns this area", "alice", ts=100)
        recalled = bob.recall(delta_graph=client.select_graph("delta"))
        claim = next(row for row in recalled if row["entity"] == "component:kernel/api")["teamClaims"][0]
        assert claim["text"] == "Alice owns this area" and claim["userProvided"] is True
        assert team.snapshot()["observations"][0]["agent"] == "chat:wp9_alice"
    finally:
        for name in names:
            try: client.connection.execute_command("GRAPH.DELETE", name)
            except ResponseError: pass
        client.close()


def test_old_refresh_risk_text_is_shown_as_recent_author_counts():
    from busfactor.team_memory import display_text
    assert (display_text("Component spark/v2/tablemanager risk changed from AT RISK to COVERED.")
            == "Component spark/v2/tablemanager recent authors changed from 1 to 2+.")
    assert (display_text("Component flink/kernel risk changed from unknown to ORPHANED.")
            == "Component flink/kernel recent authors changed from unknown to 0.")
    assert display_text("alice is no longer Active in the current activity window.") == \
        "alice is no longer Active in the current activity window."
    assert display_text(None) is None
