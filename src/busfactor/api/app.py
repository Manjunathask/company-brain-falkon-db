"""Small HTTP wrapper around the inspectable FalkorDB tools and agent."""
from __future__ import annotations

import os
import re
import logging
from datetime import date
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from busfactor import tools as graph_tools
from busfactor.agent.loop import _validate, ask, tool_specs
from busfactor.agent.memory import Memory, mark_visitor_deleted
from busfactor.db import get_client, get_graph, load_query
from busfactor.team_memory import TeamMemory


def configure_busfactor_logging() -> logging.Logger:
    """Send busfactor INFO records to the server stream exactly once."""
    logger = logging.getLogger("busfactor")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(getattr(handler, "_busfactor_api_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
        handler._busfactor_api_handler = True
        logger.addHandler(handler)
    return logger


configure_busfactor_logging()


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

    risk_rows = sorted((row for row in components if row.get("risk") in {"NO OTHER AUTHOR", "ONE OTHER AUTHOR"}),
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
        if row.get("risk") == "ONE OTHER AUTHOR":
            for expert in row.get("remaining", []):
                expert_node = next((n for n in nodes_by_id.values()
                                    if n.get("label") == "Person" and login_of(n) == expert), None)
                if expert_node:
                    selected[expert_node["id"]] = expert_node

    simulation_row = (results.get("simulation", {}).get("rows") or [{}])[0]
    cutoff_logins = set(simulation_row.get("cutOff") or [])
    for node in nodes_by_id.values():
        if node.get("label") == "Person" and login_of(node) in cutoff_logins:
            selected[node["id"]] = {**node, "focusRole": "cut-off"}

    decision_titles = {row.get("decision") for row in results.get("decision_share", {}).get("rows", [])}
    opener_logins = {opener.get("login") for row in results.get("decision_share", {}).get("rows", [])
                     for opener in row.get("otherOpeners", [])}
    for node in nodes_by_id.values():
        if node.get("label") == "Decision" and node.get("props", {}).get("title") in decision_titles:
            selected[node["id"]] = {**node, "focusRole": "departure-decision"}
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

    # Reviewer PRs stay out of the focus graph (they turned it into a ring of PR labels);
    # reviewers are listed on the area cards and drawn in "Show full evidence".
    readable_nodes = {node_id: node for node_id, node in retained_nodes.items()
                      if node.get("label") in {"Person", "Component", "Decision"}}
    readable_edges = [edge for edge in retained_edges.values()
                      if edge.get("source") in readable_nodes and edge.get("target") in readable_nodes]
    return {"nodes": list(readable_nodes.values()), "edges": readable_edges}


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
            "nodes": row["nodes"], "edges": row["relationships"], "agent_model": model,
            "chatEnabled": provider == "scripted" or
            (provider == "anthropic" and bool(os.getenv("ANTHROPIC_API_KEY")))}


@app.post("/api/ask")
def ask_endpoint(body: AskRequest):
    if os.getenv("AGENT_PROVIDER", "anthropic").lower() == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="Agent chat is disabled. Set ANTHROPIC_API_KEY to enable /api/ask.")
    try:
        return ask(body.question, body.user, body.sessionId)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/tools")
def list_tools():
    return {"tools": [{**spec, "label": graph_tools.TOOL_LABELS.get(spec["name"], spec["name"])}
                       for spec in tool_specs() if spec["name"] in graph_tools.TOOLS]}


@app.post("/api/tools/{name}")
def run_tool(name: str, body: ToolRequest):
    if name not in graph_tools.TOOLS:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")
    params, error = _validate(name, body.params)
    if error:
        raise HTTPException(status_code=422, detail=error)
    try:
        return {**graph_tools.TOOLS[name](**params), "label": graph_tools.TOOL_LABELS.get(name, name)}
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/departure/{login}")
def departure(login: str):
    try:
        person_result = get_graph().ro_query(
            "MATCH (p:Person:Active {login:$login}) WHERE coalesce(p.bot,false)=false "
            "RETURN p.name AS name", {"login": login})
        if not person_result.result_set:
            raise HTTPException(status_code=404, detail=f"No active person with login '{login}' in the graph.")
        person_name = person_result.result_set[0][0] or login
        results = {"simulation": graph_tools.simulate_departure(login),
                   "impact": graph_tools.departure_impact(login),
                   "files": graph_tools.departure_files(login),
                   "decision_share": graph_tools.decision_share(login)}
        exposed = [row for row in results["impact"]["rows"] if row.get("risk") in {"NO OTHER AUTHOR", "ONE OTHER AUTHOR"}]
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
        simulation_row = (results["simulation"].get("rows") or [{}])[0]
        impact_rows = results["impact"].get("rows", [])
        file_rows = results["files"].get("rows", [])
        results["summary"] = {
            "name": person_name,
            "noOtherAuthor": sum(row.get("risk") == "NO OTHER AUTHOR" for row in impact_rows),
            "noOtherAuthorOrReviewer": sum(row.get("risk") == "NO OTHER AUTHOR"
                                            and row.get("reviewerCount", 0) == 0 for row in impact_rows),
            "oneOtherAuthor": sum(row.get("risk") == "ONE OTHER AUTHOR" for row in impact_rows),
            "orphanedFiles": sum(int(row.get("orphanedFiles") or 0) for row in file_rows),
            "cutOff": len(simulation_row.get("cutOff") or []),
            "mainGroupBefore": simulation_row.get("mainGroupBefore"),
            "mainGroupAfter": simulation_row.get("mainGroupAfter"),
            "bridgeRank": simulation_row.get("betweennessRank"),
        }
        return results
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _read_rows(query_name: str, params: dict, graph=None) -> list[dict]:
    graph = graph or get_graph()
    result = graph.ro_query(load_query(query_name), params)
    columns = [header[1] for header in result.header]
    return [dict(zip(columns, row)) for row in result.result_set]


@app.get("/api/summary")
def summary():
    result = graph_tools.bus_factor_component(_include_graph=False)
    rows = result.get("rows", [])
    reportable = [row for row in rows if row.get("component") is not None]
    manifest = Path(__file__).resolve().parents[3] / "data" / "snapshot" / "manifest.json"
    try:
        snapshot_date = json.loads(manifest.read_text(encoding="utf-8"))["exported_at"][:10]
    except (OSError, ValueError, KeyError, TypeError):
        snapshot_date = date.today().isoformat()
    return {
        "busFactorOne": sum(row.get("busFactor") == 1 for row in reportable),
        "componentsReported": len(reportable),
        "windowDays": 365,
        "minCommits": graph_tools.DEFAULTS["minCommits"],
        "minTotal": graph_tools.DEFAULTS["minTotal"],
        "examples": [{"component": row["component"], "topExpert": row["topExpert"], "total": row["total"]}
                     for row in sorted((r for r in reportable if r.get("busFactor") == 1),
                                       key=lambda r: (-int(r.get("total") or 0), r["component"]))[:3]],
        "snapshotDate": snapshot_date,
        "dataWindow": "2 years loaded; risk counts commits from the last 12 months; a person needs 2+ such commits in an area",
    }


@app.get("/api/people")
def people(q: str = "", limit: int = 10):
    limit = max(1, min(25, int(limit)))
    since = graph_tools.DEFAULTS["since"]
    rows = _read_rows("17_people_search", {"q": q.strip(), "since": since, "limit": limit})
    return {"people": [{key: row.get(key) for key in ("login", "name", "recentCommits", "lastSeen")}
                        for row in rows]}


@app.get("/api/suggestions")
def suggestions():
    ranked_people = _read_rows("17_people_search", {"q": "", "since": graph_tools.DEFAULTS["since"], "limit": 1})
    components = graph_tools.bus_factor_component().get("rows", [])
    risky = sorted((row for row in components if row.get("component") and row.get("busFactor") == 1),
                   key=lambda row: (-int(row.get("total") or 0), row["component"]))
    old = _read_rows("10b_why_not", {"slug": "managed-commits"})
    starters = []
    if ranked_people:
        person = ranked_people[0]
        login, name = person["login"], person.get("name") or person["login"]
        starters.append({"id": "departure", "question": f"What does the project lose if {name} (@{login}) leaves?",
                         "tool": "departure", "params": {"login": login}})
    if risky:
        component = risky[0]
        starters.append({"id": "successor", "question": f"Who could take over {component['component']} if {component['topExpert']} left?",
                         "tool": "successor", "params": {"login": component["topExpert"], "component": component["component"]}})
    if old and old[0].get("chosenInstead"):
        starters.append({"id": "superseded-decision", "question": f"Why was {old[0].get('rejected')} rejected, and what replaced it?",
                         "tool": "why_not", "params": {"slug": "managed-commits"}})
    starters.append({"id": "owners", "question": "Where do the declared CODEOWNERS differ from the people doing the work?",
                     "tool": "declared_vs_actual", "params": {}})
    return {"suggestions": starters}


@app.delete("/api/memory/{user}")
def delete_memory(user: str):
    if not re.fullmatch(r"v_[0-9a-f]{32}", user):
        raise HTTPException(status_code=400, detail="Only anonymous visitor ids can be deleted.")
    mark_visitor_deleted(user)
    try:
        client = get_client()
        try:
            client.connection.execute_command("GRAPH.DELETE", f"mem_{user}")
        except Exception as exc:
            message = str(exc).lower()
            if not any(marker in message for marker in ("not found", "does not exist", "no such graph")):
                raise
        result = client.select_graph("mem_team").query(load_query("17b_team_delete_visitor_claims"),
                                                          {"agent": f"chat:{user}"})
        removed = int(result.result_set[0][0]) if result.result_set else 0
        return {"deleted": True, "teamClaimsRemoved": removed}
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


@app.get("/api/team")
def team_memory():
    try:
        return TeamMemory().snapshot()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


WEB_DIR = Path(__file__).resolve().parents[3] / "web"
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
