"""HTTP contract tests over the isolated FalkorDB fixture graph."""
import json

import pytest
from fastapi.testclient import TestClient

import busfactor.api.app as api
import busfactor.tools as graph_tools

pytestmark = pytest.mark.integration


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
