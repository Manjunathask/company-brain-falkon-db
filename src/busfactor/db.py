"""Small FalkorDB connection and query-file helpers."""

from itertools import islice
from pathlib import Path
import os

from dotenv import load_dotenv
from falkordb import FalkorDB
from redis.exceptions import ResponseError

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def get_graph():
    """Return the configured FalkorDB graph using the official Python client."""
    client = FalkorDB(
        host=os.getenv("FALKORDB_HOST", "localhost"),
        port=int(os.getenv("FALKORDB_PORT", "6379")),
        password=os.getenv("FALKORDB_PASSWORD") or None,
    )
    return client.select_graph(os.getenv("FALKORDB_GRAPH", "delta"))


def load_query(name: str) -> str:
    """Read a named Cypher query from the repository's queries directory."""
    if not name or ".." in name or "/" in name or "\\" in name or name.endswith(".cypher"):
        raise ValueError("query name must be a bare name without a path or extension")
    return (ROOT / "queries" / f"{name}.cypher").read_text(encoding="utf-8")


def create_indexes(graph) -> None:
    """Create the indexes, tolerating only FalkorDB's duplicate-index error."""
    for line in load_query("00_indexes").splitlines():
        statement = line.strip()
        if not statement or statement.startswith("//"):
            continue
        try:
            graph.query(statement)
        except ResponseError as exc:
            if not is_duplicate_index_error(exc):
                raise
            print("exists")


def is_duplicate_index_error(error: Exception) -> bool:
    """Match the FalkorDB error that create_indexes treats as an idempotent duplicate."""
    return "is already indexed" in str(error)


def run_query(name: str, params: dict | None = None):
    """Run a named query file with optional Cypher parameters."""
    graph = get_graph()
    if name == "00_indexes":
        return create_indexes(graph)
    query = load_query(name)
    return graph.query(query, params or {})


def batched(items, size: int = 500):
    """Yield lists of at most size items from any iterable."""
    if size < 1:
        raise ValueError("size must be at least 1")
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch
