"""Load parsed local data into FalkorDB in replayable batches."""

import json
from pathlib import Path
import sys

from redis.exceptions import RedisError

from busfactor.db import ROOT, batched, create_indexes, get_graph, load_query
from busfactor.ingest.codeowners import rows_for_loading
from busfactor.ingest.components import component_of
from busfactor.ingest.identity import is_bot, load_api_map, resolve_person_key
from busfactor.ingest.github_api import references
from busfactor.snapshot import INPUTS, read_input

RAW = ROOT / "data" / "raw"


def read_rows(name: str) -> list[dict]:
    if __import__("os").getenv("BUSFACTOR_INPUT", "raw") == "snapshot":
        return read_input(Path(name).stem)
    path = RAW / name
    if not path.exists():
        raise FileNotFoundError(f"Parsed input missing: {path}; run its ingest module first")
    return json.loads(path.read_text(encoding="utf-8"))


def _counts(graph) -> str:
    counts = graph.ro_query(load_query("00_counts")).result_set[0]
    node_count, edge_count = counts
    return f"nodes={node_count}, relationships={edge_count}"


def _run_rows(graph, query_name: str, rows: list[dict], label: str) -> None:
    query = load_query(query_name)
    batch_count = 0
    for batch in batched(rows):
        graph.query(query, {"rows": batch})
        batch_count += 1
    print(f"{label}: rows={len(rows)}, batches={batch_count}; {_counts(graph)}")


def load_step(graph, step: str) -> None:
    if step == "indexes":
        create_indexes(graph)
        print(f"indexes: 8 created or already present; {_counts(graph)}")
    elif step == "commits":
        api_map = read_input("identities") if __import__("os").getenv("BUSFACTOR_INPUT", "raw") == "snapshot" else load_api_map()
        commits = read_rows("git_log.json")
        rows = []
        for commit in commits:
            row = dict(commit)
            row["files"] = [dict(file, component=component_of(file["path"])) for file in commit["files"]]
            row["author"] = resolve_person_key(commit["authorEmail"], api_map)
            row["authorHandle"] = api_map.get(commit["authorEmail"])
            row["authorBot"] = is_bot(row["author"])
            rows.append(row)
        _run_rows(graph, "01_load_commits", rows, "commits")
    elif step == "decisions":
        rows = [dict(row, component=component_of(row["path"])) for row in read_rows("rfcs.json")]
        _run_rows(graph, "02_load_decisions", rows, "decisions")
        graph.query(load_query("02b_superseded_by"))
        print(f"superseded_by: applied; {_counts(graph)}")
    elif step == "codeowners":
        rows = rows_for_loading(read_rows("codeowners.json"))
        _run_rows(graph, "02c_load_codeowners", rows, "codeowners")
    elif step == "prs":
        _run_rows(graph, "01c_load_prs", read_rows("prs.json"), "prs")
    elif step == "part_of":
        graph.query(load_query("01b_link_part_of"))
        print(f"part_of: linked matching commits; {_counts(graph)}")
    elif step == "issues":
        _run_rows(graph, "01d_load_issues", read_rows("rfc_issues.json"), "issues")
    elif step == "references":
        rows = [
            {"pr": pr["number"], "issue": issue}
            for pr in read_rows("prs.json")
            for issue in sorted(references(pr.get("body")))
        ]
        _run_rows(graph, "01e_link_references", rows, "references")
    elif step == "components_cleanup":
        graph.query(load_query("01f_cleanup_components"))
        print(f"components_cleanup: removed unused components; {_counts(graph)}")
    elif step == "head_files":
        if __import__("os").getenv("BUSFACTOR_INPUT", "raw") == "snapshot":
            paths = read_input("head_files")
        elif (RAW / "head_files.json").exists():
            paths = read_rows("head_files.json")
        else:
            paths = sorted({f["path"].replace("\\", "/") for c in read_rows("git_log.json")
                            for f in c.get("files", []) if f.get("exists")})
        graph.query(load_query("15a_refresh_head_files"), {"paths": paths})
        print(f"head_files: paths={len(paths)}; {_counts(graph)}")
    else:
        raise ValueError(f"unknown load step: {step}")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    from_snapshot = "--from-snapshot" in args
    args = [arg for arg in args if arg != "--from-snapshot"]
    if from_snapshot:
        __import__("os").environ["BUSFACTOR_INPUT"] = "snapshot"
    valid_steps = {"indexes", "commits", "decisions", "codeowners", "prs", "part_of", "issues", "references", "components_cleanup", "head_files", "all"}
    if len(args) != 1 or args[0] not in valid_steps:
        print("Usage: python -m busfactor.load {indexes,commits,decisions,codeowners,prs,part_of,issues,references,components_cleanup,head_files,all} [--from-snapshot]", file=sys.stderr)
        return 2
    try:
        graph = get_graph()
        graph.client.connection.ping()
    except (RedisError, OSError, ConnectionError) as exc:
        print(f"FalkorDB is unreachable. Start it with 'docker compose up -d' and check FALKORDB_HOST/PORT: {exc}", file=sys.stderr)
        return 1
    steps = ["indexes", "commits", "decisions", "codeowners", "prs", "part_of", "issues", "references", "head_files", "components_cleanup"] if args[0] == "all" else args
    try:
        for step in steps:
            load_step(graph, step)
    except (RedisError, OSError, ConnectionError) as exc:
        print(f"FalkorDB operation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
