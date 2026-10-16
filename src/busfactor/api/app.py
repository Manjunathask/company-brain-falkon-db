"""Small HTTP wrapper around the inspectable FalkorDB tools and agent."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from busfactor import tools as graph_tools
from busfactor.agent.loop import _validate, ask, tool_specs
from busfactor.agent.memory import Memory
from busfactor.db import get_graph, load_query


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    user: str = Field(min_length=1)
    sessionId: str | None = None


class ToolRequest(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(title="Bus Factor API", version="1.0")


@app.middleware("http")
async def prevent_stale_static_assets(request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or not request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


def _columns(result) -> list[str]:
    return [header[1] for header in result.header]


def _merge_graph(target: dict, part: dict) -> None:
    nodes = {node.get("id"): node for node in target["nodes"]}
    for node in part.get("nodes", []):
        nodes.setdefault(node.get("id"), node)
    target["nodes"] = list(nodes.values())
    edges = {(edge.get("source"), edge.get("type"), edge.get("target")): edge
             for edge in target["edges"]}
    for edge in part.get("edges", []):
        edges.setdefault((edge.get("source"), edge.get("type"), edge.get("target")), edge)
    target["edges"] = list(edges.values())


def _focused_departure_graph(login: str, results: dict, components: list[dict]) -> dict:
    """Keep only the departure person, exposed components, decision, cut-off, and successor evidence."""
    sources = [results[name].get("graph", {}) for name in
               ("simulation", "impact", "files", "decision_share", "successor")]
    nodes_by_id = {}
    edges_by_key = {}
    for source in sources:
        for node in source.get("nodes", []):
            nodes_by_id[node.get("id")] = node
        for edge in source.get("edges", []):
            edges_by_key[(edge.get("source"), edge.get("type"), edge.get("target"))] = edge

    def login_of(node):
        return node.get("props", {}).get("login") or (node.get("key") if node.get("label") == "Person" else None)

    def component_of(node):
        return node.get("props", {}).get("name") or (node.get("key") if node.get("label") == "Component" else None)

    selected = {}
    person = next((n for n in nodes_by_id.values()
                   if n.get("label") == "Person" and login_of(n) == login), None)
    if person is None:
        person = {"id": f"focus-person-{login}", "label": "Person", "key": login,
                  "props": {"login": login, "name": login}, "focusRole": "departing"}
    else:
        person = {**person, "focusRole": "departing"}
    selected[person["id"]] = person

    risk_rows = sorted((row for row in components if row.get("risk") in {"ORPHANED", "AT RISK"}),
                       key=lambda row: (-int(row.get("theirCommits") or 0), row.get("component", "")))[:10]
    selected_component_names = set()
    for row in risk_rows:
        name = row.get("component")
        if not name:
            continue
        selected_component_names.add(name)
        component = next((n for n in nodes_by_id.values()
                          if n.get("label") == "Component" and component_of(n) == name), None)
        if component is None:
            component = {"id": f"focus-component-{name}", "label": "Component", "key": name,
                         "props": {"name": name}}
        component = {**component, "risk": row.get("risk"), "theirCommits": row.get("theirCommits")}
        selected[component["id"]] = component
        if row.get("risk") == "AT RISK":
            for expert in row.get("remaining", []):
                expert_node = next((n for n in nodes_by_id.values()
                                    if n.get("label") == "Person" and login_of(n) == expert), None)
                if expert_node:
                    selected[expert_node["id"]] = expert_node

    simulation_row = (results.get("simulation", {}).get("rows") or [{}])[0]
    cutoff_logins = set(simulation_row.get("cutOff") or [])
    for node in nodes_by_id.values():
        if node.get("label") == "Person" and login_of(node) in cutoff_logins:
            selected[node["id"]] = node

    decision_titles = {row.get("decision") for row in results.get("decision_share", {}).get("rows", [])}
    opener_logins = {opener.get("login") for row in results.get("decision_share", {}).get("rows", [])
                     for opener in row.get("otherOpeners", [])}
    for node in nodes_by_id.values():
        if node.get("label") == "Decision" and node.get("props", {}).get("title") in decision_titles:
            selected[node["id"]] = node
        elif node.get("label") == "Person" and login_of(node) in opener_logins:
            selected[node["id"]] = node

    successor_logins = {row.get("successor") for row in results.get("successor", {}).get("rows", [])}
    for node in nodes_by_id.values():
        if node.get("label") == "Person" and login_of(node) in successor_logins:
            selected[node["id"]] = node

    # Keep only short evidence paths connecting the selected identities and areas.
    retained_edges = {}
    retained_nodes = dict(selected)
    for edge in edges_by_key.values():
        source = nodes_by_id.get(edge.get("source"))
        target = nodes_by_id.get(edge.get("target"))
        if source is None or target is None:
            continue
        source_id, target_id = source.get("id"), target.get("id")
        source_login, target_login = login_of(source), login_of(target)
        source_component, target_component = component_of(source), component_of(target)
        rel_type = edge.get("type")
        keep = False
        if rel_type == "WORKS_WITH" and (
            (source_login == login and target_login in cutoff_logins) or
            (target_login == login and source_login in cutoff_logins)
        ):
            keep = True
        elif rel_type == "KNOWS" and (
            (source_login == login and target_component in selected_component_names) or
            (target_login == login and source_component in selected_component_names) or
            (source_login in {expert for row in risk_rows for expert in row.get("remaining", [])}
             and target_component in selected_component_names) or
            (target_login in {expert for row in risk_rows for expert in row.get("remaining", [])}
             and source_component in selected_component_names)
        ):
            keep = True
        elif rel_type in {"OPENED", "IMPLEMENTS"} and (
            source_login == login or target_login == login or
            source_login in opener_logins or target_login in opener_logins or
            (source.get("label") == "Decision" and source.get("props", {}).get("title") in decision_titles) or
            (target.get("label") == "Decision" and target.get("props", {}).get("title") in decision_titles)
        ):
            keep = True
        elif source_component in selected_component_names or target_component in selected_component_names:
            # Successor tool paths contain the shared file/commit evidence for the chosen area.
            if source_login == login or target_login == login or source_login in successor_logins or target_login in successor_logins:
                keep = True
        if keep:
            retained_edges[(edge.get("source"), edge.get("type"), edge.get("target"))] = edge
            retained_nodes.setdefault(source_id, source)
            retained_nodes.setdefault(target_id, target)

    # The successor query is already scoped to the selected component and ranked candidates.
    successor_graph = results.get("successor", {}).get("graph", {})
    for node in successor_graph.get("nodes", []):
        retained_nodes.setdefault(node.get("id"), node)
    for edge in successor_graph.get("edges", []):
        retained_edges[(edge.get("source"), edge.get("type"), edge.get("target"))] = edge

    return {"nodes": list(retained_nodes.values()), "edges": list(retained_edges.values())}


@app.get("/api/health")
def health():
    try:
        graph = get_graph()
        result = graph.ro_query(load_query("00_counts"), {})
        row = dict(zip(_columns(result), result.result_set[0]))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"FalkorDB unavailable: {exc}") from exc
    provider = os.getenv("AGENT_PROVIDER", "anthropic").lower()
    model = os.getenv("AGENT_MODEL", "claude-sonnet-5-5") if provider == "anthropic" else provider
    return {"ok": True, "graph": os.getenv("FALKORDB_GRAPH", "delta"),
            "nodes": row["nodes"], "edges": row["relationships"], "agent_model": model}


@app.post("/api/ask")
def ask_endpoint(body: AskRequest):
    try:
        return ask(body.question, body.user, body.sessionId)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/tools")
def list_tools():
    return {"tools": [spec for spec in tool_specs() if spec["name"] in graph_tools.TOOLS]}


@app.post("/api/tools/{name}")
def run_tool(name: str, body: ToolRequest):
    if name not in graph_tools.TOOLS:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")
    params, error = _validate(name, body.params)
    if error:
        raise HTTPException(status_code=422, detail=error)
    try:
        return graph_tools.TOOLS[name](**params)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/departure/{login}")
def departure(login: str):
    try:
        results = {"simulation": graph_tools.simulate_departure(login),
                   "impact": graph_tools.departure_impact(login),
                   "files": graph_tools.departure_files(login),
                   "decision_share": graph_tools.decision_share(login)}
        exposed = [row for row in results["impact"]["rows"] if row.get("risk") in {"ORPHANED", "AT RISK"}]
        chosen = max(exposed, key=lambda row: (int(row.get("theirCommits") or 0), row.get("component", "")), default=None)
        results["successor_component"] = chosen.get("component") if chosen else None
        results["top_orphaned_component"] = results["successor_component"]
        results["successor"] = (graph_tools.successor(login, chosen["component"])
                                if chosen else {"rows": [], "graph": {"nodes": [], "edges": []},
                                                "cypher": "", "params": {}, "tool": "successor"})
        evidence = {"nodes": [], "edges": []}
        for key in ("simulation", "impact", "files", "decision_share", "successor"):
            _merge_graph(evidence, results[key].get("graph", {}))
        results["graph"] = evidence
        results["focus_graph"] = _focused_departure_graph(login, results, results["impact"].get("rows", []))
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/memory/{user}")
def memory(user: str):
    try:
        store = Memory(user)
        return {**store.snapshot(), "recall": store.recall(delta_graph=get_graph())}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


WEB_DIR = Path(__file__).resolve().parents[3] / "web"
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
