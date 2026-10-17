"""Handover packet (WP14): candidate evidence, team-memory exclusions, questions, markdown and 'what changed'."""
import os

import pytest
from falkordb import FalkorDB
from redis.exceptions import RedisError, ResponseError

from busfactor import handover
from busfactor.team_memory import TeamMemory

GRAPH, TEAM = "bf_handover_test", "bf_handover_team"
NOW = 1_790_000_000_000  # before the real clock, so "activity since a saved packet" only counts what a test adds
SINCE = NOW - 1_000_000_000


def _delete(client, name):
    try:
        client.connection.execute_command("GRAPH.DELETE", name)
    except ResponseError:
        pass


@pytest.fixture
def graphs():
    try:
        client = FalkorDB(host=os.getenv("FALKORDB_HOST", "127.0.0.1"), port=int(os.getenv("FALKORDB_PORT", "6379")),
                          password=os.getenv("FALKORDB_PASSWORD") or None)
        client.connection.ping()
    except (RedisError, OSError, ConnectionError) as exc:
        pytest.skip(f"FalkorDB is unreachable: {exc}")
    for name in (GRAPH, TEAM):
        _delete(client, name)
    g = client.select_graph(GRAPH)
    # gone wrote 3 commits over files A, B, C in two PRs; rev reviewed both PRs and wrote 2 commits to file A
    # (so file and commit counts must not multiply the review count); auth wrote 1 commit to file B.
    g.query("""
        CREATE (gone:Person:Active {login:'gone', name:'Gone Person', bot:false}),
               (rev:Person:Active {login:'rev', name:'Rev', bot:false}),
               (auth:Person:Active {login:'auth', name:'Auth', bot:false}),
               (area:Component {name:'flink/kernel'}),
               (fa:File {path:'flink/A.java', exists:true})-[:IN_COMPONENT]->(area),
               (fb:File {path:'flink/B.java', exists:true})-[:IN_COMPONENT]->(area),
               (fc:File {path:'flink/C.java', exists:true})-[:IN_COMPONENT]->(area),
               (p1:PR {number:1, title:'Add A and B', mergedAt:$now}),
               (p2:PR {number:2, title:'Add C', mergedAt:$now}),
               (d:Decision {slug:'dv', title:'Deletion Vectors', status:'accepted'}),
               (issue:Issue {number:900}), (doc:File {path:'protocol_rfcs/dv.md', exists:true}),
               (d)-[:TRACKED_IN]->(issue), (d)-[:DOCUMENTED_IN]->(doc),
               (p1)-[:IMPLEMENTS {confidence:'low', via:'title-keyword'}]->(d),
               (gone)-[:OPENED]->(p1), (gone)-[:OPENED]->(p2),
               (rev)-[:REVIEWED {at:$now}]->(p1), (rev)-[:REVIEWED {at:$now}]->(p2),
               (rev)-[:PARTICIPATED_IN {confidence:'high', via:'pr'}]->(d),
               (gone)-[:KNOWS {commits:3, lastTouched:$now}]->(area)
        WITH gone, rev, auth, fa, fb, fc, p1, p2
        UNWIND [{p:gone, sha:'g1', files:[fa, fb], pr:p1}, {p:gone, sha:'g2', files:[fa], pr:p1},
                {p:gone, sha:'g3', files:[fc], pr:p2}, {p:rev, sha:'r1', files:[fa], pr:null},
                {p:rev, sha:'r2', files:[fa], pr:null}, {p:auth, sha:'a1', files:[fb], pr:null}] AS row
        CREATE (c:Commit {sha:row.sha, ts:$now})
        WITH row, c
        MATCH (person:Person {login:row.p.login})
        CREATE (person)-[:AUTHORED]->(c)
        WITH row, c
        UNWIND row.files AS file
        MATCH (f:File {path:file.path})
        CREATE (c)-[:TOUCHED]->(f)
        WITH DISTINCT row, c
        OPTIONAL MATCH (pr:PR {number:row.pr.number})
        FOREACH (_ IN CASE WHEN pr IS NULL THEN [] ELSE [1] END | CREATE (c)-[:PART_OF]->(pr))
        """, {"now": NOW})
    team = TeamMemory(graph=client.select_graph(TEAM))
    yield g, team
    for name in (GRAPH, TEAM):
        _delete(client, name)
    client.close()


def _packet(g, team):
    return handover.build_packet("gone", "flink/kernel", name="Gone Person", graph=g, team=team, since=SINCE)


@pytest.mark.integration
def test_candidate_columns_are_separate_and_do_not_multiply(graphs):
    g, team = graphs
    packet = _packet(g, team)
    rev = next(row for row in packet["candidates"] if row["login"] == "rev")
    assert (rev["reviewedTheirPRs"], rev["theirPRCount"], rev["sharedFiles"], rev["outOf"], rev["areaCommits"],
            rev["areaReviews"]) == (2, 2, 1, 3, 2, 2)
    assert rev["sharedDecisions"] == ["Deletion Vectors"]
    assert packet["successor"]["login"] == "rev"
    assert packet["successor"]["why"].startswith("Reviewed 2 of Gone Person's 2 PRs here; edited 1 of the 3 files")
    auth = next(row for row in packet["candidates"] if row["login"] == "auth")
    assert (auth["reviewedTheirPRs"], auth["sharedFiles"], auth["areaCommits"]) == (0, 1, 1)
    assert "flink/C.java" in rev["toLearn"] and "flink/A.java" not in rev["toLearn"]


@pytest.mark.integration
def test_questions_markdown_and_sources(graphs):
    g, team = graphs
    packet = _packet(g, team)
    texts = [item["text"] for item in packet["ask"]]
    assert "Was PR #1 part of Deletion Vectors? (title-keyword guess)" in texts
    assert all(item["from"] for item in packet["ask"])
    markdown = packet["markdown"]
    for pr in packet["read"]:
        assert f"{handover.GITHUB}/pull/{pr['number']}" in markdown
    assert f"{handover.GITHUB}/issues/900" in markdown and f"{handover.GITHUB}/blob/master/protocol_rfcs/dv.md" in markdown
    assert handover.CAVEAT in markdown
    assert {node["label"] for node in packet["graph"]["nodes"]} <= {"Person", "PR", "Decision", "Component"}


@pytest.mark.integration
def test_unavailable_candidate_is_skipped_and_the_change_is_explained(graphs):
    g, team = graphs
    handover.save_packet("gone", "flink/kernel", "rev", agent="chat:v_test", source="test", team=team)
    handover.mark_availability("rev", "unavailable", "on leave", agent="chat:v_test", source="test", team=team)
    packet = _packet(g, team)
    assert packet["successor"]["login"] == "auth"
    assert [(item["login"], item["reason"]) for item in packet["skipped"]] == [("rev", "on leave")]
    changed = packet["changed"]
    assert changed["previousCandidate"] == "rev" and changed["candidate"] == "auth" and not changed["same"]
    assert changed["reasons"][0].startswith("rev was marked unavailable") and "(unverified note)" in changed["reasons"][0]
    assert "What changed:" in packet["markdown"]
    # The newest note wins.
    handover.mark_availability("rev", "available", "", agent="chat:v_test", source="test", team=team)
    assert _packet(g, team)["successor"]["login"] == "rev"


def test_questions_are_unique_and_capped():
    candidate = {"login": "rev", "toLearn": [f"f{i}" for i in range(5)]}
    decisions = [{"title": f"D{i}", "leavingParticipated": True, "otherActiveCount": 0} for i in range(4)]
    asked = handover.questions("Gone", ["f0", "f1", "f0"], decisions, [], candidate)
    texts = [item["text"] for item in asked]
    assert len(texts) == handover.MAX_QUESTIONS == len(set(texts))
    assert "Can you walk rev through f0?" not in texts  # already asked about f0 as a file question


def test_availability_status_is_checked():
    with pytest.raises(ValueError):
        handover.mark_availability("rev", "maybe", "", agent="chat:v_test", source="test", team=object())
