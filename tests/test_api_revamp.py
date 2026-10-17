"""WP11a response contracts against isolated and live FalkorDB graphs."""
import logging

import pytest
from fastapi.testclient import TestClient

import busfactor.api.app as api
import busfactor.tools as graph_tools
from busfactor.agent.followups import build_followups
from busfactor.agent.memory import memory_graph_name
from busfactor.db import load_query


@pytest.fixture
def client(graph, monkeypatch):
    monkeypatch.setattr(api, "get_graph", lambda: graph)
    monkeypatch.setattr(graph_tools, "get_graph", lambda: graph)
    return TestClient(api.app)


def test_summary_shape_and_fixture_counts(client, monkeypatch):
    monkeypatch.setattr(graph_tools, "bus_factor_component", lambda **kwargs: {"rows": [
        {"component": "spark/test", "busFactor": 1, "topExpert": "alice", "total": 5},
        {"component": "spark/covered", "busFactor": 2, "topExpert": "bob", "total": 7},
    ]})
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["busFactorOne"] == 1
    assert data["componentsReported"] == 2
    assert data["windowDays"] == 365 and data["minCommits"] == 2 and data["minTotal"] == 5
    assert data["examples"][0]["component"] == "spark/test"
    assert {"snapshotDate", "dataWindow"} <= data.keys()


@pytest.mark.parametrize(("provider", "api_key", "expected"), [
    ("anthropic", "secret", True),
    ("anthropic", "", False),
    ("scripted", "", True),
    ("other", "secret", False),
])
def test_health_reports_chat_availability(client, monkeypatch, provider, api_key, expected):
    monkeypatch.setenv("AGENT_PROVIDER", provider)
    monkeypatch.setenv("ANTHROPIC_API_KEY", api_key)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["chatEnabled"] is expected


def test_people_search_prefix_name_and_limit(client):
    response = client.get("/api/people?q=ali&limit=10")
    assert response.status_code == 200
    assert response.json()["people"][0]["login"] == "alice"
    person = response.json()["people"][0]
    assert person["name"] == "Alice" and person["recentCommits"] == 1
    assert {"lastSeen", "recentCommits"} <= person.keys()
    assert client.get("/api/people?q=ali&limit=99").status_code == 200


def test_suggestions_are_named_and_have_direct_tool_params(monkeypatch):
    monkeypatch.setattr(api, "_read_rows", lambda name, params, graph=None: (
        [{"login": "alice", "name": "Alice"}] if name == "17_people_search" else
        [{"rejected": "Old RFC", "chosenInstead": "New RFC"}]))
    monkeypatch.setattr(graph_tools, "bus_factor_component", lambda **kwargs: {"rows": [
        {"component": "spark/core", "busFactor": 1, "topExpert": "alice", "total": 20}]})
    data = api.suggestions()["suggestions"]
    assert len(data) == 4
    assert all(item["question"] and item["tool"] and isinstance(item["params"], dict) for item in data)
    assert data[0]["tool"] == "departure" and data[0]["params"]["login"] == "alice"
    assert data[1]["tool"] == "successor" and data[1]["params"]["component"] == "spark/core"
    assert data[2]["params"]["slug"] == "managed-commits"


@pytest.mark.parametrize(("tool", "params", "rows", "expected"), [
    ("departure_impact", {"login": "alice"}, [{"component": "spark/core", "risk": "NO OTHER AUTHOR"}],
     "Who could take over spark/core if alice left?"),
    ("decision_share", {}, [{"decision": "Catalog Tables"}], "Who else worked on Catalog Tables?"),
    ("simulate_departure", {"login": "alice"}, [{"cutOff": ["bob"]}],
     "Who would lose their link to the main collaboration network if alice left?"),
    ("decision_trace", {}, [{"decisionTitle": "Catalog Tables"}], "Who took part in Catalog Tables?"),
    ("why_not", {}, [{"chosenInstead": "Catalog Tables", "changesSinceDecision": 2}],
     "Which files changed since Catalog Tables was accepted?"),
])
def test_followup_template_by_tool(tool, params, rows, expected):
    assert build_followups([{"tool": tool, "params": params, "rows": rows}]) == [expected]


def test_followups_skip_unsupported_rows_deduplicate_and_cap():
    calls = [{"tool": "departure_impact", "params": {"login": "alice"}, "rows": [
        {"component": "allowed", "risk": "ONE OTHER AUTHOR"}, {"component": "not-risky", "risk": "COVERED"},
        {"component": "allowed", "risk": "NO OTHER AUTHOR"}]},
        {"tool": "departure_impact", "params": {"login": "alice"}, "rows": [
            {"component": "c2", "risk": "NO OTHER AUTHOR"}, {"component": "c3", "risk": "NO OTHER AUTHOR"}]}]
    result = build_followups(calls)
    assert len(result) == 2
    assert all("not-risky" not in item for item in result)
    assert build_followups([{"tool": "why_not", "params": {}, "rows": [
        {"chosenInstead": "No drift", "changesSinceDecision": 0}]}]) == []


def test_followups_round_robin_limit_per_tool_and_skip_asked_question():
    calls = [
        {"tool": "departure_impact", "params": {"login": "murali-db"}, "rows": [
            {"component": "spark", "risk": "ONE OTHER AUTHOR", "login": "murali-db", "name": "Murali Ramanujam"},
            {"component": "kernel", "risk": "NO OTHER AUTHOR", "login": "murali-db", "name": "Murali Ramanujam"},
            {"component": "flink", "risk": "NO OTHER AUTHOR", "login": "murali-db", "name": "Murali Ramanujam"},
        ]},
        {"tool": "decision_share", "params": {}, "rows": [
            {"decision": "Catalog Tables"}, {"decision": "Protocol V3"},
        ]},
    ]
    result = build_followups(calls, question="Who could take over spark if Murali Ramanujam (@murali-db) left?")
    assert result == [
        "Who else worked on Catalog Tables?",
        "Who could take over kernel if Murali Ramanujam (@murali-db) left?",
        "Who else worked on Protocol V3?",
        "Who could take over flink if Murali Ramanujam (@murali-db) left?",
    ]


def test_unknown_person_is_404_before_simulation(client, monkeypatch):
    called = []
    monkeypatch.setattr(graph_tools, "simulate_departure", lambda login: called.append(login))
    response = client.get("/api/departure/not-in-graph")
    assert response.status_code == 404
    assert response.json()["detail"] == "No active person with login 'not-in-graph' in the graph."
    assert called == []


def test_departure_summary_fields(client):
    data = client.get("/api/departure/alice").json()
    assert data["summary"]["name"] == "Alice"
    assert {"noOtherAuthor", "noOtherAuthorOrReviewer", "oneOtherAuthor", "orphanedFiles", "cutOff", "mainGroupBefore",
            "mainGroupAfter", "bridgeRank"} <= data["summary"].keys()


def test_focused_departure_graph_omits_commit_and_file_nodes():
    graph = {
        "simulation": {"graph": {"nodes": [
            {"id": "person", "label": "Person", "key": "alice", "props": {"login": "alice"}},
            {"id": "commit", "label": "Commit"}, {"id": "file", "label": "File"},
            {"id": "component", "label": "Component", "key": "spark/core", "props": {"name": "spark/core"}},
        ], "edges": [
            {"source": "person", "target": "component", "type": "KNOWS"},
            {"source": "person", "target": "commit", "type": "AUTHORED"},
            {"source": "commit", "target": "file", "type": "TOUCHED"},
        ]}},
        "impact": {"graph": {"nodes": [
            {"id": "reviewer", "label": "Person", "key": "bob", "props": {"login": "bob"}},
            {"id": "pr", "label": "PR", "props": {"number": 7}},
        ], "edges": [
            {"source": "reviewer", "target": "pr", "type": "REVIEWED"},
        ]}},
        "files": {"graph": {"nodes": [], "edges": []}},
        "decision_share": {"graph": {"nodes": [], "edges": []}, "rows": []},
        "successor": {"graph": {"nodes": [], "edges": []}, "rows": []},
    }
    focus = api._focused_departure_graph("alice", graph, [
        {"component": "spark/core", "risk": "NO OTHER AUTHOR", "theirCommits": 8, "reviewers": ["bob"]},
    ])
    assert all(node["label"] in {"Person", "Component", "Decision"} for node in focus["nodes"])
    assert all(edge["type"] != "REVIEWED" for edge in focus["edges"])
    ids = {node["id"] for node in focus["nodes"]}
    assert all(edge["source"] in ids and edge["target"] in ids for edge in focus["edges"])


def test_visitor_id_validation(client):
    assert memory_graph_name("v_" + "a" * 32) == "mem_v_" + "a" * 32
    for invalid in ("bad visitor", "v_" + "A" * 32, "v_" + "a" * 31):
        assert client.delete(f"/api/memory/{invalid}").status_code == 400


def test_delete_removes_only_visitor_memory_and_claims(client, monkeypatch):
    visitor = "v_" + "b" * 32
    calls = []
    class Connection:
        def execute_command(self, *args): calls.append(("delete", args))
    class TeamGraph:
        def query(self, query, params):
            calls.append(("claims", params))
            return type("Result", (), {"result_set": [[3]]})()
    class FakeClient:
        connection = Connection()
        def select_graph(self, name):
            assert name == "mem_team"
            return TeamGraph()
    monkeypatch.setattr(api, "get_client", lambda: FakeClient())
    response = client.delete(f"/api/memory/{visitor}")
    assert response.status_code == 200
    assert response.json() == {"deleted": True, "teamClaimsRemoved": 3}
    assert calls == [("delete", ("GRAPH.DELETE", f"mem_{visitor}")),
                     ("claims", {"agent": f"chat:{visitor}"})]


def test_team_claim_delete_query_preserves_other_visitors(graph):
    graph.query("""
        CREATE (a:Agent {name:'chat:v_testone'})-[:WROTE]->(:Observation {id:'o1',kind:'user_claim'}),
               (b:Agent {name:'chat:v_testtwo'})-[:WROTE]->(:Observation {id:'o2',kind:'user_claim'})
    """)
    result = graph.query(load_query("17b_team_delete_visitor_claims"), {"agent": "chat:v_testone"})
    assert result.result_set[0][0] == 1
    remaining = graph.ro_query("MATCH (a:Agent)-[:WROTE]->(o:Observation) RETURN a.name,o.id")
    assert remaining.result_set == [["chat:v_testtwo", "o2"]]


def test_tool_labels_present(client):
    tools = client.get("/api/tools").json()["tools"]
    assert all(item.get("label") for item in tools)
    assert all(graph_tools.TOOL_LABELS[item["name"]] == item["label"] for item in tools)


def test_busfactor_stream_logging_is_single_and_non_propagating():
    logger = api.configure_busfactor_logging()
    api.configure_busfactor_logging()
    tagged = [handler for handler in logger.handlers
              if getattr(handler, "_busfactor_api_handler", False)]
    assert len(tagged) == 1
    assert isinstance(tagged[0], logging.StreamHandler)
    assert tagged[0].formatter._fmt == "%(levelname)s %(name)s %(message)s"
    assert logger.propagate is False


@pytest.mark.integration
def test_live_people_m_prefix_ranks_murali_first():
    from busfactor.db import get_graph
    graph = get_graph()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(api, "get_graph", lambda: graph)
    try:
        with TestClient(api.app) as live_client:
            people = live_client.get("/api/people?q=m&limit=5").json()["people"]
        assert people and people[0]["login"] == "murali-db"
    finally:
        monkeypatch.undo()


@pytest.mark.integration
def test_live_summary_and_suggestions_are_graph_backed():
    from busfactor.db import get_graph
    graph = get_graph()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(api, "get_graph", lambda: graph)
    monkeypatch.setattr(graph_tools, "get_graph", lambda: graph)
    try:
        with TestClient(api.app) as live_client:
            summary = live_client.get("/api/summary").json()
            suggestions = live_client.get("/api/suggestions").json()["suggestions"]
        assert abs(summary["busFactorOne"] - 25) <= 5
        assert abs(summary["componentsReported"] - 69) <= 5
        assert len(suggestions) == 4
    finally:
        monkeypatch.undo()


def test_focus_graph_keeps_capped_decision_paths_and_collapsed_reviewer_edges():
    empty = {"graph": {"nodes": [], "edges": []}, "rows": []}
    results = {
        "simulation": {"graph": {"nodes": [
            {"id": "person", "label": "Person", "key": "alice", "props": {"login": "alice"}},
            {"id": "carol", "label": "Person", "key": "carol", "props": {"login": "carol"}},
        ], "edges": []}, "rows": [{}]},
        "impact": {"graph": {"nodes": [
            {"id": "area", "label": "Component", "key": "flink/kernel", "props": {"name": "flink/kernel"}},
        ], "edges": []}},
        "files": empty,
        "decision_share": {"graph": {"nodes": [
            {"id": "dec", "label": "Decision", "key": "d", "props": {"title": "Decision D", "slug": "d"}},
        ], "edges": []}, "rows": [{"decision": "Decision D", "slug": "d", "prs": [
            {"number": n, "title": f"PR {n}", "confidence": "high" if n == 1 else "low",
             "via": "issue-ref" if n == 1 else "title-keyword"} for n in (1, 2, 3, 4, 5)]}]},
        "successor": empty,
    }
    focus = api._focused_departure_graph("alice", results, [
        {"component": "flink/kernel", "risk": "NO OTHER AUTHOR", "theirCommits": 4,
         "reviewerPRs": [{"login": "bob", "prs": 4}, {"login": "dan", "prs": 1}]},
    ])
    labels = [node["label"] for node in focus["nodes"]]
    assert labels.count("PR") == 3 and "Commit" not in labels and "File" not in labels
    implements = [edge for edge in focus["edges"] if edge["type"] == "IMPLEMENTS"]
    assert [edge["props"]["confidence"] for edge in implements] == ["high", "low", "low"]
    assert sum(edge["type"] == "OPENED" and edge["source"] == "person" for edge in focus["edges"]) == 3
    reviewed = {edge["source"]: edge["props"] for edge in focus["edges"] if edge["type"] == "REVIEWED_IN"}
    assert reviewed["focus-person-bob"] == {"prs": 4, "collapsed": True, "summary": "reviewed 4 PRs here"}
    assert reviewed["focus-person-dan"]["summary"] == "reviewed 1 PR here"
    # carol has no link in the focus graph, so she is dropped.
    assert "carol" not in {node["id"] for node in focus["nodes"]}
