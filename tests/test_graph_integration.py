"""Exercise the real Cypher files against a disposable FalkorDB graph."""

import os

import pytest
from falkordb import FalkorDB
from redis.exceptions import RedisError, ResponseError

from busfactor.db import create_indexes, load_query
from busfactor.ingest.codeowners import parse_codeowners, rows_for_loading


pytestmark = pytest.mark.integration
GRAPH_NAME = "bf_test"
SINCE = 1_700_000_000_000
RECENT = 1_800_000_000_000


def _delete_graph(client: FalkorDB) -> None:
    try:
        client.connection.execute_command("GRAPH.DELETE", GRAPH_NAME)
    except ResponseError:
        # FalkorDB reports an error if the disposable graph does not exist yet.
        pass


@pytest.fixture(scope="module")
def graph():
    try:
        client = FalkorDB(
            host=os.getenv("FALKORDB_HOST", "localhost"),
            port=int(os.getenv("FALKORDB_PORT", "6379")),
            password=os.getenv("FALKORDB_PASSWORD") or None,
        )
        client.connection.ping()
    except (RedisError, OSError, ConnectionError) as exc:
        pytest.skip(f"FalkorDB is unreachable: {exc}")

    _delete_graph(client)
    try:
        yield client.select_graph(GRAPH_NAME)
    finally:
        _delete_graph(client)
        client.close()


def _run(graph, name: str, params: dict | None = None):
    return graph.query(load_query(name), params or {})


def _count(graph, pattern: str) -> int:
    return graph.query(f"MATCH {pattern} RETURN count(*)").result_set[0][0]


def _run_derives(graph) -> None:
    _run(graph, "03_derive_knows")
    _run(graph, "03b_derive_last_seen", {"since": SINCE})
    _run(graph, "04_derive_works_with", {
        "since": SINCE,
        "minShared": 3,
        "maxFileCommits": 4,
    })
    _run(graph, "04b_derive_participated_pr")
    _run(graph, "04c_derive_participated_issue")


def test_load_and_derive_queries_end_to_end(graph):
    # Running the production index helper twice verifies its duplicate-index handling.
    create_indexes(graph)
    create_indexes(graph)

    commits = [
        {
            "author": "alice", "authorEmail": "alice-one@example.com", "authorHandle": "Alice",
            "authorBot": False, "authorName": "Alice", "sha": "c-alice-1", "ts": RECENT,
            "subject": "[Spark] files (#101)", "area": "spark", "pr": 101,
            "files": [
                {"path": "spark/A.scala", "module": "spark", "added": 7, "deleted": 2},
                {"path": "spark/B.scala", "module": "spark", "added": 4, "deleted": 1},
                {"path": "build.sbt", "module": "root", "added": 1, "deleted": 0},
            ],
        },
        {
            "author": "alice", "authorEmail": "alice-two@example.com", "authorHandle": "Alice",
            "authorBot": False, "authorName": "Alice", "sha": "c-alice-2", "ts": RECENT - 100,
            "subject": "[Spark] another file", "area": "spark", "pr": 102,
            "files": [
                {"path": "spark/C.scala", "module": "spark", "added": 9, "deleted": 3},
                {"path": "build.sbt", "module": "root", "added": 0, "deleted": 1},
            ],
        },
        {
            "author": "bob", "authorEmail": "bob@example.com", "authorHandle": "Bob",
            "authorBot": False, "authorName": "Bob", "sha": "c-bob", "ts": RECENT - 200,
            "subject": "[Spark] shared files (#101)", "area": "spark", "pr": 101,
            "files": [
                {"path": "spark/A.scala", "module": "spark", "added": 2, "deleted": 0},
                {"path": "spark/B.scala", "module": "spark", "added": 3, "deleted": 1},
                {"path": "spark/C.scala", "module": "spark", "added": 5, "deleted": 2},
                {"path": "build.sbt", "module": "root", "added": 1, "deleted": 1},
            ],
        },
        {
            "author": "charlie", "authorEmail": "charlie@example.com", "authorHandle": "Charlie",
            "authorBot": False, "authorName": "Charlie", "sha": "c-charlie", "ts": RECENT - 300,
            "subject": "[Spark] two shared files", "area": "spark", "pr": 909,
            "files": [
                {"path": "spark/A.scala", "module": "spark", "added": 1, "deleted": 1},
                {"path": "spark/B.scala", "module": "spark", "added": 1, "deleted": 0},
                {"path": "build.sbt", "module": "root", "added": 0, "deleted": 2},
            ],
        },
        {
            "author": "helper[bot]", "authorEmail": "bot@example.com", "authorHandle": "helper[bot]",
            "authorBot": True, "authorName": "helper[bot]", "sha": "c-bot", "ts": RECENT - 400,
            "subject": "[Spark] bot commit", "area": "spark", "pr": 101,
            "files": [
                {"path": "spark/A.scala", "module": "spark", "added": 1, "deleted": 0},
                {"path": "spark/B.scala", "module": "spark", "added": 1, "deleted": 0},
                {"path": "build.sbt", "module": "root", "added": 1, "deleted": 0},
            ],
        },
    ]
    _run(graph, "01_load_commits", {"rows": commits})
    # Replay confirms email collection and loaded nodes/edges are idempotent.
    _run(graph, "01_load_commits", {"rows": commits})
    assert _count(graph, "(p:Person)") == 4
    assert _count(graph, "(c:Commit)") == 5
    assert _count(graph, "(f:File)") == 4
    assert _count(graph, "(m:Module)") == 2
    assert _count(graph, "()-[t:TOUCHED]->()") == 15
    alice = graph.query("MATCH (p:Person {login:'alice'}) RETURN p.emails, p.bot").result_set[0]
    assert set(alice[0]) == {"alice-one@example.com", "alice-two@example.com"}
    assert alice[1] is False
    touched = graph.query(
        "MATCH (:Commit {sha:'c-alice-1'})-[t:TOUCHED]->(:File {path:'spark/A.scala'}) "
        "RETURN t.added, t.deleted"
    ).result_set[0]
    assert touched == [7, 2]
    assert graph.query("MATCH (p:Person {login:'helper[bot]'}) RETURN p.bot").result_set[0][0] is True

    prs = [{
        "number": 101, "title": "Example PR", "state": "MERGED", "createdAt": RECENT - 50,
        "mergedAt": RECENT, "body": "RFC details", "author": "ghost", "authorHandle": "ghost",
        "authorBot": True,
        "reviewers": [
            {"login": "revieweronly", "handle": "ReviewerOnly", "bot": False, "at": RECENT - 10},
            {"login": "revieweronly", "handle": "ReviewerOnly", "bot": False, "at": RECENT},
            {"login": "reviewbot[bot]", "handle": "reviewbot[bot]", "bot": True, "at": RECENT - 5},
        ],
    }]
    _run(graph, "01c_load_prs", {"rows": prs})
    assert _count(graph, "(:Person {login:'ghost'})-[:OPENED]->(:PR {number:101})") == 1
    review = graph.query(
        "MATCH (:Person {login:'revieweronly'})-[r:REVIEWED]->(:PR {number:101}) RETURN r.at"
    ).result_set[0][0]
    assert review == RECENT
    assert graph.query("MATCH (p:Person {login:'ghost'}) RETURN p.bot").result_set[0][0] is True
    assert graph.query("MATCH (p:Person {login:'reviewbot[bot]'}) RETURN p.bot").result_set[0][0] is True

    _run(graph, "01b_link_part_of")
    parts = graph.query(
        "MATCH (c:Commit)-[:PART_OF]->(pr:PR) RETURN c.sha, pr.number ORDER BY c.sha"
    ).result_set
    assert parts == [["c-alice-1", 101], ["c-bob", 101], ["c-bot", 101]]

    issues = [{
        "number": 500, "title": "RFC issue", "state": "OPEN", "createdAt": RECENT - 100,
        "author": "issueopener", "authorHandle": "IssueOpener", "authorBot": False,
        "commenters": [
            {"login": "issuecommenter", "handle": "IssueCommenter", "bot": False, "at": RECENT - 20},
        ],
    }]
    _run(graph, "01d_load_issues", {"rows": issues})
    comment_at = graph.query(
        "MATCH (:Person {login:'issuecommenter'})-[r:COMMENTED]->(:Issue {number:500}) RETURN r.at"
    ).result_set[0][0]
    assert comment_at == RECENT - 20
    _run(graph, "01e_link_references", {"rows": [
        {"pr": 101, "issue": 500}, {"pr": 101, "issue": 9999},
    ]})
    refs = graph.query("MATCH (:PR {number:101})-[:REFERENCES]->(i:Issue) RETURN i.number").result_set
    assert refs == [[500]]

    decisions = [
        {"slug": "managed-commits", "title": "Managed Commits", "status": "rejected", "proposedOn": None,
         "decidedOn": RECENT - 100, "issue": 500, "path": "protocol_rfcs/managed-commits.md", "module": "protocol_rfcs"},
        {"slug": "catalog-managed", "title": "Catalog-Managed Tables", "status": "accepted", "proposedOn": None,
         "decidedOn": RECENT - 50, "issue": 501, "path": "protocol_rfcs/catalog-managed.md", "module": "protocol_rfcs"},
    ]
    _run(graph, "02_load_decisions", {"rows": decisions})
    _run(graph, "02b_superseded_by")
    _run(graph, "02c_load_codeowners", {"rows": rows_for_loading(parse_codeowners("/spark/ @MiXeDOwner\n"))})
    assert _count(graph, "(:Decision {slug:'managed-commits'})-[:TRACKED_IN]->(:Issue {number:500})") == 1
    assert _count(graph, "(:Decision {slug:'catalog-managed'})-[:DOCUMENTED_IN]->(:File {path:'protocol_rfcs/catalog-managed.md'})") == 1
    assert _count(graph, "(:File {path:'protocol_rfcs/catalog-managed.md'})-[:IN_MODULE]->(:Module {name:'protocol_rfcs'})") == 1
    superseded = graph.query(
        "MATCH (:Decision {slug:'managed-commits'})-[r:SUPERSEDED_BY]->(:Decision {slug:'catalog-managed'}) "
        "RETURN r.source"
    ).result_set[0][0]
    assert superseded == "PR #4382"
    owner = graph.query(
        "MATCH (p:Person {login:'mixedowner'})-[r:DECLARED_OWNER]->(:Module {name:'spark'}) "
        "RETURN p.handle, r.pattern"
    ).result_set[0]
    assert owner == ["MiXeDOwner", "/spark/"]

    _run(graph, "01c_load_prs", {"rows": [{
        "number": 102, "title": "Support coordinated commits", "state": "MERGED",
        "createdAt": RECENT - 40, "mergedAt": RECENT - 30, "body": "",
        "author": "alice", "authorHandle": "Alice", "authorBot": False, "reviewers": [],
    }]})
    graph.query(
        "MATCH (c:Commit {sha:'c-alice-1'}) "
        "MERGE (f:File {path:'protocol_rfcs/accepted/managed-commits.md'}) "
        "MERGE (c)-[:TOUCHED]->(f)"
    )
    _run(graph, "04d_derive_implements_issue_ref")
    _run(graph, "04e_derive_implements_rfc_doc")
    _run(graph, "04f_load_implements_keyword", {"rows": [
        {"pr": 101, "slug": "managed-commits", "pattern": r"\bcoordinated commits?\b"},
        {"pr": 102, "slug": "managed-commits", "pattern": r"\bcoordinated commits?\b"},
        {"pr": 102, "slug": "catalog-managed", "pattern": r"\bcatalog[- ]managed\b"},
    ]})
    implementations = graph.query(
        "MATCH (:PR {number:101})-[r:IMPLEMENTS]->(:Decision {slug:'managed-commits'}) "
        "RETURN r.via, r.confidence, r.sources"
    ).result_set[0]
    assert implementations[0] == "issue-ref"
    assert implementations[1] == "high"
    assert set(implementations[2]) == {"issue-ref", "rfc-doc", "title-keyword"}
    assert _count(graph, "(:PR {number:102})-[:IMPLEMENTS {via:'title-keyword', confidence:'low'}]->(:Decision {slug:'managed-commits'})") == 1
    assert _count(graph, "(:PR {number:102})-[:IMPLEMENTS {via:'title-keyword', confidence:'low'}]->(:Decision {slug:'catalog-managed'})") == 1

    # Replay all evidence sources and verify no duplicates or confidence downgrade.
    _run(graph, "04d_derive_implements_issue_ref")
    _run(graph, "04e_derive_implements_rfc_doc")
    _run(graph, "04f_load_implements_keyword", {"rows": [
        {"pr": 101, "slug": "managed-commits", "pattern": r"\bcoordinated commits?\b"},
        {"pr": 102, "slug": "managed-commits", "pattern": r"\bcoordinated commits?\b"},
        {"pr": 102, "slug": "catalog-managed", "pattern": r"\bcatalog[- ]managed\b"},
    ]})
    assert _count(graph, "(:PR)-[:IMPLEMENTS]->(:Decision)") == 3
    replayed = graph.query(
        "MATCH (:PR {number:101})-[r:IMPLEMENTS]->(:Decision {slug:'managed-commits'}) "
        "RETURN r.via, r.confidence, r.sources"
    ).result_set[0]
    assert replayed == implementations

    _run(graph, "04b_derive_participated_pr")
    _run(graph, "04c_derive_participated_issue")
    participant_confidence = graph.query(
        "MATCH (:Person {login:'alice'})-[r:PARTICIPATED_IN]->(:Decision {slug:'catalog-managed'}) "
        "RETURN r.confidence"
    ).result_set[0][0]
    assert participant_confidence == "low"

    _run_derives(graph)
    knows = graph.query(
        "MATCH (:Person {login:'alice'})-[k:KNOWS]->(:Module {name:'spark'}) RETURN k.commits"
    ).result_set[0][0]
    assert knows == 2  # c-alice-1 touches two Spark files but is one distinct commit.
    active_reviewer = graph.query(
        "MATCH (p:Person {login:'revieweronly'}) RETURN p.lastSeen, p.lastCommit, p:Active"
    ).result_set[0]
    assert active_reviewer == [RECENT, None, True]
    assert _count(graph, "(:Person {login:'helper[bot]'})-[:KNOWS]->()") == 0
    assert _count(graph, "(:Person {login:'helper[bot]'})-[:WORKS_WITH]-()") == 0
    assert _count(graph, "(p:Person {login:'helper[bot]'}) WHERE p:Active") == 0
    works = graph.query(
        "MATCH (a:Person)-[w:WORKS_WITH]->(b:Person) RETURN a.login, b.login, w.sharedFiles"
    ).result_set
    assert len(works) == 1
    assert set(works[0][:2]) == {"alice", "bob"}
    assert works[0][2] == 3

    before = graph.query(
        "MATCH ()-[r]->() RETURN type(r), count(r) ORDER BY type(r)"
    ).result_set
    _run_derives(graph)
    after = graph.query(
        "MATCH ()-[r]->() RETURN type(r), count(r) ORDER BY type(r)"
    ).result_set
    assert after == before
