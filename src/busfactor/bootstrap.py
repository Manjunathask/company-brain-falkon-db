"""One-shot container entrypoint: build an empty graph from the checked-in snapshot, then serve."""
import os
import subprocess
import sys
import time

from busfactor.db import get_graph, load_query


def wait_for_falkordb(graph, *, timeout_seconds: int = 60, sleep=time.sleep) -> None:
    """Wait up to a minute for PING, with visible progress for container logs."""
    deadline = time.monotonic() + timeout_seconds
    print(f"Waiting up to {timeout_seconds}s for FalkorDB PING...", flush=True)
    while True:
        try:
            graph.client.connection.ping()
            print("FalkorDB PING succeeded.", flush=True)
            return
        except Exception as exc:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError(f"FalkorDB did not answer PING within {timeout_seconds}s: {exc}") from exc
            print(f"FalkorDB is not ready yet; retrying in up to 2s ({int(remaining)}s left): {exc}", flush=True)
            sleep(min(2, remaining))


def graph_counts(graph) -> tuple[int, int]:
    row = graph.ro_query(load_query("00_counts"), {}).result_set[0]
    return int(row[0]), int(row[1])


def needs_snapshot(graph, graph_name: str) -> bool:
    """A missing graph is empty; only query counts after GRAPH.LIST confirms it exists."""
    names = graph.client.list_graphs()
    if graph_name not in names:
        return True
    nodes, _ = graph_counts(graph)
    return nodes == 0


def bootstrap_graph(graph, graph_name: str, *, env=None, run=subprocess.run) -> bool:
    """Load, link, and derive an empty graph from the checked-in snapshot."""
    if not needs_snapshot(graph, graph_name):
        nodes, edges = graph_counts(graph)
        print(f"Graph {graph_name!r} already has data; snapshot bootstrap skipped ({nodes} nodes, {edges} relationships).", flush=True)
        return False

    print(f"Graph {graph_name!r} is missing or empty; bootstrapping from data/snapshot.", flush=True)
    child_env = dict(os.environ if env is None else env, BUSFACTOR_INPUT="snapshot")
    steps = [
        ("load", [sys.executable, "-m", "busfactor.load", "all", "--from-snapshot"]),
        ("link", [sys.executable, "-m", "busfactor.link_decisions", "--from-snapshot"]),
        ("derive", [sys.executable, "-m", "busfactor.derive"]),
    ]
    for label, command in steps:
        print(f"Bootstrap {label}: starting", flush=True)
        run(command, check=True, env=child_env)
        nodes, edges = graph_counts(graph)
        print(f"Bootstrap {label}: complete; nodes={nodes}, relationships={edges}", flush=True)
    return True


def main() -> int:
    graph = get_graph()
    wait_for_falkordb(graph)
    graph_name = os.getenv("FALKORDB_GRAPH", "delta")
    bootstrap_graph(graph, graph_name)
    return subprocess.call([sys.executable, "-m", "busfactor.api"], env=os.environ)


if __name__ == "__main__":
    raise SystemExit(main())
