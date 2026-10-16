"""Run the four reviewer-facing departure queries against the live delta graph."""

import argparse
from datetime import datetime, timedelta, timezone

from busfactor.db import get_graph, load_query


def print_table(title: str, columns: list[str], rows: list[list]) -> None:
    print(f"\n{title}")
    if not rows:
        print("  (no rows)")
        return
    widths = [len(column) for column in columns]
    rendered = [[str(value) for value in row] for row in rows]
    for row in rendered:
        widths = [max(width, len(value)) for width, value in zip(widths, row)]
    print("  " + " | ".join(name.ljust(width) for name, width in zip(columns, widths)))
    print("  " + "-+-".join("-" * width for width in widths))
    for row in rendered:
        print("  " + " | ".join(value.ljust(width) for value, width in zip(row, widths)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Try Bus Factor departure queries against FalkorDB")
    parser.add_argument("--login", required=True, help="GitHub login of the departing person")
    parser.add_argument("--since", type=int, help="activity window start, epoch milliseconds (default: one year)")
    parser.add_argument("--min-commits", type=int, default=2, help="minimum remaining expertise to count")
    parser.add_argument("--min-total", type=int, default=5, help="minimum recent commits for a module/component to be reported")
    args = parser.parse_args(argv)
    if args.min_commits < 1 or args.min_total < 1:
        parser.error("--min-commits and --min-total must be positive")
    since = args.since
    if since is None:
        since = int((datetime.now(timezone.utc) - timedelta(days=365)).timestamp() * 1000)

    graph = get_graph()
    params = {"login": args.login, "since": since, "minCommits": args.min_commits, "minTotal": args.min_total}
    try:
        graph.client.connection.ping()
        module_rows = graph.query(load_query("05_bus_factor"), params).result_set
        component_rows = graph.query(load_query("05b_bus_factor_component"), params).result_set
        impact_rows = graph.query(load_query("06_departure_impact"), params).result_set
        file_rows = graph.query(load_query("06b_departure_files"), params).result_set
    finally:
        graph.client.close()

    module_filtered = module_rows[0][6] if module_rows else 0
    component_filtered = component_rows[0][6] if component_rows else 0
    module_rows = [row[:6] for row in module_rows if row[0] is not None]
    component_rows = [row[:6] for row in component_rows if row[0] is not None]
    print(f"Departure analysis for @{args.login}; since={since}, minCommits={args.min_commits}, minTotal={args.min_total}")
    print(f"Filtered out: {module_filtered} modules, {component_filtered} components with fewer than {args.min_total} commits")
    print_table("Bus factor by module", ["module", "busFactor", "topExpert", "topShare", "people", "total commits"], module_rows)
    print_table("Bus factor by component", ["component", "busFactor", "topExpert", "topShare", "people", "total commits"], component_rows)
    print_table("Departure impact by component", ["component", "theirCommits", "expertsLeft", "remaining", "risk"], impact_rows)
    print_table("Orphaned files by component", ["component", "orphanedFiles", "theirFiles", "examples"], file_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
