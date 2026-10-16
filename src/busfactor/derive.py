"""Refresh derived expertise, activity, collaboration, and decision edges."""

import argparse
from datetime import datetime, timedelta, timezone
import sys
import time

from redis.exceptions import RedisError

from busfactor.db import get_graph, load_query

QUERY_NAMES = (
    "03_derive_knows",
    "03c_derive_knows_component",
    "03b_derive_last_seen",
    "04_derive_works_with",
    "04b_derive_participated_pr",
    "04c_derive_participated_issue",
)


def default_since() -> int:
    """Return now minus 365 days as epoch milliseconds."""
    now = datetime.now(timezone.utc)
    return int((now - timedelta(days=365)).timestamp() * 1000)


def _scalar(graph, query: str) -> int:
    return int(graph.query(query).result_set[0][0])


def build_query_params(since: int, min_shared: int, max_file_commits: int) -> dict[str, dict]:
    """Return the exact parameter maps passed to each derive query."""
    return {
        "03_derive_knows": {},
        "03c_derive_knows_component": {},
        "03b_derive_last_seen": {"since": since},
        "04_derive_works_with": {
            "since": since,
            "minShared": min_shared,
            "maxFileCommits": max_file_commits,
        },
        "04b_derive_participated_pr": {},
        "04c_derive_participated_issue": {},
    }


def _print_sanity(graph) -> None:
    print("\nSanity check")
    print("Top modules by KNOWS edges:")
    rows = graph.query(
        "MATCH (:Person)-[k:KNOWS]->(m:Module) "
        "RETURN m.name, count(k) AS edges ORDER BY edges DESC, m.name LIMIT 10"
    ).result_set
    for module, count in rows:
        print(f"  {module}: {count}")
    print("Top components by KNOWS edges:")
    rows = graph.query(
        "MATCH (:Person)-[k:KNOWS]->(c:Component) "
        "RETURN c.name, count(k) AS edges ORDER BY edges DESC, c.name LIMIT 10"
    ).result_set
    for component, count in rows:
        print(f"  {component}: {count}")

    active = _scalar(graph, "MATCH (p:Person:Active) RETURN count(p)")
    print(f"Active people: {active}")

    works_count = _scalar(graph, "MATCH ()-[w:WORKS_WITH]->() RETURN count(w)")
    print(f"WORKS_WITH edges: {works_count}")
    rows = graph.query(
        "MATCH (a:Person)-[w:WORKS_WITH]->(b:Person) "
        "RETURN a.login, b.login, w.sharedFiles "
        "ORDER BY w.sharedFiles DESC, a.login, b.login LIMIT 5"
    ).result_set
    print("Top WORKS_WITH pairs by sharedFiles:")
    for a, b, shared in rows:
        print(f"  {a} -- {b}: {shared}")

    print("PARTICIPATED_IN edges per decision:")
    rows = graph.query(
        "MATCH (d:Decision) OPTIONAL MATCH (:Person)-[r:PARTICIPATED_IN]->(d) "
        "RETURN d.title, count(r) AS people ORDER BY d.title"
    ).result_set
    for title, count in rows:
        print(f"  {title}: {count}")


def run_derive(graph, since: int, min_shared: int, max_file_commits: int) -> None:
    """Run each named derive query in order and report its work and runtime."""
    for name, query_params in build_query_params(since, min_shared, max_file_commits).items():
        started = time.perf_counter()
        result = graph.query(load_query(name), query_params)
        elapsed = time.perf_counter() - started
        created = int(result.relationships_created)
        total = _scalar(graph, "MATCH ()-[r]->() RETURN count(r)")
        print(f"{name}: relationships created={created}, graph total={total}, elapsed={elapsed:.3f}s")
    _print_sanity(graph)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derive Bus Factor graph relationships")
    parser.add_argument("--since", type=int, default=None, help="activity window start, epoch milliseconds")
    parser.add_argument("--min-shared", type=int, default=3, help="minimum shared recent files for WORKS_WITH")
    parser.add_argument("--max-file-commits", type=int, default=150, help="skip files touched by more recent commits")
    args = parser.parse_args(argv)
    if args.min_shared < 1 or args.max_file_commits < 1:
        parser.error("--min-shared and --max-file-commits must be positive")

    since = default_since() if args.since is None else args.since
    try:
        graph = get_graph()
        graph.client.connection.ping()
        run_derive(graph, since, args.min_shared, args.max_file_commits)
    except (RedisError, OSError, ConnectionError) as exc:
        print(f"FalkorDB is unreachable or the derive query failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
