"""HTTP contract tests over the isolated FalkorDB fixture graph."""
import json
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

import busfactor.api.app as api
import busfactor.tools as graph_tools

pytestmark = pytest.mark.integration

# Keep this contract in sync with the departure renderer and WP11a response shape.
DEPARTURE_FIELDS = {
    "simulation": {"rows", "login", "mainGroupBefore", "mainGroupAfter", "cutOff", "betweennessRank"},
    "impact": {"rows", "component", "risk", "expertsLeft", "theirCommits", "remaining"},
    "files": {"rows", "component", "orphanedFiles", "theirFiles", "examplePaths"},
    "decision_share": {"rows", "decision", "theirPRs", "totalPRs", "share", "otherOpeners", "login", "prs"},
    "successor": {"rows", "successor", "sharedFiles", "outOf", "theirCommits"},
    "graph": {"nodes", "edges"},
    "focus_graph": {"nodes", "edges"},
    "successor_component": set(),
    "summary": {"name", "orphaned", "atRisk", "orphanedFiles", "cutOff",
                "mainGroupBefore", "mainGroupAfter", "bridgeRank"},
}


@pytest.fixture
def client(graph, monkeypatch):
    monkeypatch.setattr(api, "get_graph", lambda: graph)
    monkeypatch.setattr(graph_tools, "get_graph", lambda: graph)
    monkeypatch.setenv("FALKORDB_GRAPH", "bf_api_test")
    return TestClient(api.app)


def test_health_and_tools_contract(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True
    assert health.json()["nodes"] > 0
    assert health.json()["edges"] > 0
    tools = client.get("/api/tools").json()["tools"]
    assert any(tool["name"] == "find_entity" and "input_schema" in tool for tool in tools)


def test_team_endpoint_returns_observations_and_refresh_runs(client, monkeypatch):
    monkeypatch.setattr(api, "TeamMemory", lambda: type("Team", (), {"snapshot": lambda self: {
        "observations": [{"agent": "watcher", "text": "risk changed", "ts": 10}],
        "refreshRuns": [{"newCommits": 1, "newPRs": 0, "ts": 10}],
    }})())
    response = client.get("/api/team")
    assert response.status_code == 200
    assert response.json()["observations"][0]["agent"] == "watcher"
    assert response.json()["refreshRuns"][0]["newCommits"] == 1


def test_memory_endpoint_keeps_complete_recall_for_ui(client, monkeypatch):
    rows = [{"entity": f"component:area/{index}", "lastAsked": index} for index in range(12)]
    class Store:
        def __init__(self, user): pass
        def snapshot(self): return {"episodes": []}
        def recall(self, **kwargs): return rows
    monkeypatch.setattr(api, "Memory", Store)
    response = client.get("/api/memory/reviewer_live")
    assert response.status_code == 200
    assert len(response.json()["recall"]) == 12


def test_static_assets_are_not_cached(client):
    assert "no-cache" in client.get("/").headers["cache-control"]
    assert "no-cache" in client.get("/app.js").headers["cache-control"]


def test_frontend_graph_cap_and_layout_are_explicit():
    from pathlib import Path
    graph_js = Path(__file__).resolve().parents[1] / "web" / "graph.js"
    source = graph_js.read_text(encoding="utf-8")
    assert "export function capConnectedGraph" in source
    assert "edges.filter(edge => kept.has(edge.source) && kept.has(edge.target))" in source
    assert 'name: "concentric"' in source
    assert 'name: "breadthfirst"' in source
    assert 'name: "cose"' in source


def test_index_loads_versioned_es_modules():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    index = (root / "web" / "index.html").read_text(encoding="utf-8")
    app = (root / "web" / "app.js").read_text(encoding="utf-8")
    assert '<script type="module" src="/app.js?v=' in index
    assert '"./graph.js?v=' in app
    assert '"./people-combobox.js?v=' in app


def test_graph_cap_javascript_unit():
    from pathlib import Path
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    script = Path(__file__).resolve().parent / "js" / "test_graph_cap.mjs"
    subprocess.run([node, str(script)], check=True, capture_output=True, text=True)


def test_direct_tool_endpoint_returns_cypher_rows_and_graph(client):
    response = client.post("/api/tools/find_entity", json={"params":{"text":"alice"}})
    assert response.status_code == 200
    result = response.json()
    assert result["cypher"]
    assert isinstance(result["rows"], list)
    assert isinstance(result["graph"]["nodes"], list)
    assert result["rows"][0]["key"] == "alice"


def test_departure_endpoint_combines_headline_queries(client):
    result = client.get("/api/departure/alice")
    assert result.status_code == 200
    data = result.json()
    assert {"simulation", "impact", "files", "decision_share", "successor", "graph"} <= set(data)
    assert data["simulation"]["rows"][0]["login"] == "alice"
    assert isinstance(data["graph"]["nodes"], list)
    assert isinstance(data["focus_graph"]["nodes"], list)


def test_departure_payload_matches_app_field_contract(graph, monkeypatch):
    from busfactor.api import app as api_module
    monkeypatch.setattr(api_module, "get_graph", lambda: graph)
    monkeypatch.setattr(api_module.graph_tools, "get_graph", lambda: graph)
    client = TestClient(api_module.app)

    empty_graph = {"nodes": [], "edges": []}
    monkeypatch.setattr(api_module.graph_tools, "simulate_departure", lambda login: {
        "rows": [{"login": login, "mainGroupBefore": 4, "mainGroupAfter": 3,
                  "cutOff": ["cutoff"], "betweennessRank": 1}], "graph": empty_graph})
    monkeypatch.setattr(api_module.graph_tools, "departure_impact", lambda login: {
        "rows": [
            {"component": "unit/core", "risk": "AT RISK", "expertsLeft": 1,
             "theirCommits": 12, "remaining": ["expert"]},
            {"component": "unit/rare", "risk": "ORPHANED", "expertsLeft": 0,
             "theirCommits": 4, "remaining": []},
        ],
        "graph": {"nodes": [
            {"id": 1, "label": "Person", "key": login, "props": {"login": login, "name": "Departing"}},
            {"id": 2, "label": "Component", "key": "unit/core", "props": {"name": "unit/core"}},
            {"id": 3, "label": "Person", "key": "expert", "props": {"login": "expert", "name": "Expert"}},
        ], "edges": [{"source": 1, "target": 2, "type": "KNOWS", "props": {}},
                    {"source": 3, "target": 2, "type": "KNOWS", "props": {}}]}})
    monkeypatch.setattr(api_module.graph_tools, "departure_files", lambda login: {
        "rows": [{"component": "unit/core", "orphanedFiles": 2, "theirFiles": 5,
                  "examplePaths": ["unit/core/A.scala"]}], "graph": empty_graph})
    monkeypatch.setattr(api_module.graph_tools, "decision_share", lambda login: {
        "rows": [{"decision": "Decision A", "theirPRs": 2, "totalPRs": 4, "share": 0.5,
                      "otherOpeners": [{"login": "opener", "prs": 2}]}], "graph": empty_graph})
    monkeypatch.setattr(api_module.graph_tools, "successor", lambda login, component: {
        "rows": [{"successor": "expert", "sharedFiles": 3, "outOf": 5, "theirCommits": 7}],
        "graph": {"nodes": [{"id": 4, "label": "Person", "key": "expert",
                              "props": {"login": "expert", "name": "Expert"}}], "edges": []}})
    graph.query(
        "CREATE (:Person:Active {login:'departing',name:'Departing',bot:false})")

    response = client.get("/api/departure/departing")
    assert response.status_code == 200
    data = response.json()
    assert DEPARTURE_FIELDS.keys() <= data.keys()
    for section, names in DEPARTURE_FIELDS.items():
        if section == "successor_component":
            continue
        if "rows" in names:
            assert "rows" in data[section]
            nested = {"login", "prs"} if section == "decision_share" else set()
            assert (names - {"rows"} - nested) <= data[section]["rows"][0].keys()
            if section == "decision_share":
                assert all(nested <= opener.keys() for row in data[section]["rows"]
                           for opener in row["otherOpeners"])
        else:
            assert names <= data[section].keys()
    assert data["successor_component"] == "unit/core"
    assert data["successor"]["rows"][0]["theirCommits"] == 7
    assert any(node.get("risk") == "AT RISK" for node in data["focus_graph"]["nodes"])
    assert data["summary"] == {
        "name": "Departing", "orphaned": 1, "atRisk": 1, "orphanedFiles": 2,
        "cutOff": 1, "mainGroupBefore": 4, "mainGroupAfter": 3, "bridgeRank": 1,
    }


def test_ask_uses_scripted_provider_and_returns_memory_recall(client, monkeypatch):
    monkeypatch.setenv("AGENT_PROVIDER", "scripted")
    monkeypatch.setenv("AGENT_SCRIPT", json.dumps([{"stop":"tool_use","tool_calls":[
        {"id":"find-1","name":"find_entity","input":{"text":"alice"}}]},
        {"stop":"end","text":"Alice is present in the fixture graph."}]))
    response = client.post("/api/ask", json={"question":"Who is Alice?","user":"api-test","sessionId":"api-session"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Alice is present in the fixture graph."
    assert data["tool_calls"][0]["tool"] == "find_entity"
    assert data["tool_calls"][0]["cypher"]
    assert data["graph"]["nodes"]
    assert "memory_recall" in data
