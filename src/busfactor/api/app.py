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
        orphaned = next((row for row in results["impact"]["rows"] if row.get("risk") == "ORPHANED"), None)
        results["top_orphaned_component"] = orphaned.get("component") if orphaned else None
        results["successor"] = (graph_tools.successor(login, orphaned["component"])
                                if orphaned else {"rows": [], "graph": {"nodes": [], "edges": []},
                                                  "cypher": "", "params": {}, "tool": "successor"})
        evidence = {"nodes": [], "edges": []}
        for key in ("simulation", "impact", "files", "decision_share", "successor"):
            _merge_graph(evidence, results[key].get("graph", {}))
        results["graph"] = evidence
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
