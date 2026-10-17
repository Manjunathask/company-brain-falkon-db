"""Incrementally refresh the Delta graph and publish deterministic team observations."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from dotenv import load_dotenv
from redis.exceptions import RedisError

from busfactor import derive, load, link_decisions
from busfactor.db import ROOT, get_graph, load_query
from busfactor.ingest.components import component_of
from busfactor.ingest.github_api import GitHubGraphQL, PR_FIELDS, _connection_nodes, parse_pr
from busfactor.ingest.identity import is_bot, load_api_map, resolve_person_key
from busfactor.team_memory import TeamMemory

RAW = ROOT / "data" / "raw"


def _columns(result):
    return [header[1] for header in result.header]


def watermarks(graph) -> dict:
    result = graph.ro_query(load_query("15_refresh_watermarks"))
    return dict(zip(_columns(result), result.result_set[0]))


def parse_new_commits(output: str, watermark: int | None, head_paths: list[str]) -> list[dict]:
    from busfactor.ingest.git_log import parse_git_log
    rows = parse_git_log(output)
    head = {path.replace("\\", "/") for path in head_paths}
    for row in rows:
        row["files"] = [dict(file, exists=file["path"].replace("\\", "/") in head) for file in row["files"]]
    return [row for row in rows if watermark is None or row["ts"] > int(watermark)]


def git_updates(repo: Path, watermark: int | None, *, pull: bool) -> tuple[list[dict], list[str]]:
    if pull:
        subprocess.run(["git", "-C", str(repo), "pull", "--ff-only"], check=True,
                       capture_output=True, text=True, encoding="utf-8")
    since = "1970-01-01" if watermark is None else datetime.fromtimestamp(int(watermark) / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    from busfactor.ingest.git_log import HEADER
    output = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", "log",
                             f"--since={since}", "--no-merges", "--no-renames", "--numstat",
                             f"--format={HEADER}"], check=True, capture_output=True,
                            text=True, encoding="utf-8").stdout
    paths = subprocess.run(["git", "-C", str(repo), "ls-files"], check=True,
                           capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
    return parse_new_commits(output, watermark, paths), paths


def collect_updated_prs(fetch_page, watermark: int | None) -> list[dict]:
    """Read newest-updated pages until a previously known, unchanged PR appears."""
    cursor = None
    rows = {}
    page = 0
    while True:
        connection = fetch_page(cursor, page)
        stop = False
        for raw in _connection_nodes(connection):
            updated = raw.get("updatedAt") or raw.get("mergedAt") or raw.get("createdAt")
            updated_ms = int(datetime.fromisoformat(updated.replace("Z", "+00:00")).timestamp() * 1000) if updated else 0
            if watermark is not None and updated_ms <= int(watermark):
                stop = True
                break
            rows[int(raw["number"])] = raw
        if stop or not connection.get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = connection["pageInfo"].get("endCursor")
        page += 1
    return [parse_pr(rows[number]) for number in sorted(rows)]


def github_updates(token: str, watermark: int | None, stamp: int) -> list[dict]:
    api = GitHubGraphQL(token, refresh=True)
    def fetch_page(cursor, page):
        after = f', after: "{cursor}"' if cursor else ""
        query = f'''query {{ rateLimit {{ cost remaining resetAt }} repository(owner:"delta-io", name:"delta") {{ pullRequests(first:25, orderBy:{{field: UPDATED_AT, direction: DESC}}{after}) {{ nodes {{ {PR_FIELDS} }} pageInfo {{ hasNextPage endCursor }} }} }} }}'''
        cache = RAW / "github" / "refresh_prs" / f"{stamp}-page-{page}.json"
        payload = api._request(query, cache)
        return payload["data"]["repository"]["pullRequests"]
    return collect_updated_prs(fetch_page, watermark)


def _risk_snapshot(graph, since: int) -> dict[str, str]:
    """Map each Component to its qualifying recent-author count: '0', '1' or '2+'."""
    result = graph.ro_query(load_query("15b_refresh_component_risk"), {"since": since})
    return {row[0]: "2+" if row[1] >= 2 else str(row[1]) for row in result.result_set}


def _active_people(graph) -> set[str]:
    result = graph.ro_query("MATCH (p:Person:Active) RETURN p.login")
    return {row[0] for row in result.result_set}


def _prepare_commit(row: dict, api_map: dict) -> dict:
    prepared = dict(row)
    prepared["files"] = [dict(file, component=component_of(file["path"])) for file in row["files"]]
    prepared["author"] = resolve_person_key(row["authorEmail"], api_map)
    prepared["authorHandle"] = api_map.get(row["authorEmail"])
    prepared["authorBot"] = is_bot(prepared["author"])
    return prepared


def count_commits_per_component(commits: list[dict]) -> dict[str, int]:
    """Count each commit at most once per component, regardless of files touched."""
    by_component: dict[str, set[str]] = {}
    for commit in commits:
        sha = commit["sha"]
        for component in {component_of(file["path"]) for file in commit.get("files", [])}:
            by_component.setdefault(component, set()).add(sha)
    return {component: len(shas) for component, shas in sorted(by_component.items())}


def _write_cache(name: str, rows: list[dict], *, append: bool = False):
    path = RAW / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if append and path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        seen = {row.get("sha", row.get("number")) for row in old}
        rows = old + [row for row in rows if row.get("sha", row.get("number")) not in seen]
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _team_observations(graph, team: TeamMemory, before_risk: dict, after_risk: dict,
                       before_active: set[str], after_active: set[str], changed_decisions: list[dict], ts: int) -> list[str]:
    observations = []
    for component in sorted(before_risk.keys() | after_risk.keys()):
        old, new = before_risk.get(component), after_risk.get(component)
        if old != new and new:
            observations.append((f"Component {component} recent authors changed from {old or 'unknown'} to {new}.", "risk_change", f"component:{component}"))
    for login in sorted(before_active - after_active):
        observations.append((f"{login} is no longer Active in the current activity window.", "person_inactive", f"person:{login}"))
    for item in changed_decisions:
        observations.append((f"New PR activity linked to decision {item['title']} (#{item['number']}).", "decision_activity", f"decision:{item['slug']}"))
    ids = []
    for text, kind, key in observations:
        row = team.write_observation(agent="watcher", text=text, ts=ts, kind=kind, source="delta refresh", key=key)
        ids.append(row["id"])
    return ids


def run_refresh(*, graph=None, repo: Path | None = None, no_pull: bool = False, no_github: bool = False,
                commit_output: str | None = None, head_paths: list[str] | None = None,
                pr_page_fetcher=None, team_memory=None, run_derive=True) -> dict:
    graph = graph or get_graph()
    repo = repo or Path(os.getenv("DELTA_REPO", "data/delta"))
    if not repo.is_absolute():
        repo = ROOT / repo
    watermark = watermarks(graph)
    now_ms = int(time.time() * 1000)
    since = derive.default_since()
    before_risk = _risk_snapshot(graph, since)
    before_active = _active_people(graph)
    if commit_output is None:
        commits, head_paths = git_updates(repo, watermark.get("newestCommit"), pull=not no_pull)
    else:
        if head_paths is None:
            head_paths = []
        commits = parse_new_commits(commit_output, watermark.get("newestCommit"), head_paths)
    api_map = load_api_map()
    prepared_commits = [_prepare_commit(row, api_map) for row in commits]
    prs = []
    if not no_github:
        if pr_page_fetcher:
            prs = collect_updated_prs(pr_page_fetcher, watermark.get("newestPR"))
        else:
            load_dotenv(ROOT / ".env")
            token = os.getenv("GITHUB_TOKEN")
            if not token:
                raise RuntimeError("GITHUB_TOKEN not set; use --no-github to skip GitHub refresh")
            prs = github_updates(token, watermark.get("newestPR"), now_ms)

    if prs:
        _write_cache("prs.json", prs, append=True)
        load._run_rows(graph, "01c_load_prs", prs, "refresh PRs")
    if prepared_commits:
        _write_cache("git_log.json", commits, append=True)
        load._run_rows(graph, "01_load_commits", prepared_commits, "refresh commits")
    # Recompute file existence on every run, even when there were no new commits.
    graph.query(load_query("15a_refresh_head_files"), {"paths": [p.replace("\\", "/") for p in (head_paths or [])]})
    graph.query(load_query("01b_link_part_of"))
    if prs:
        refs = [{"pr": pr["number"], "issue": issue}
                for pr in prs for issue in sorted(__import__("busfactor.ingest.github_api", fromlist=["references"]).references(pr.get("body")))]
        if refs:
            load._run_rows(graph, "01e_link_references", refs, "refresh references")
    # This linker uses the complete PR graph and cached RFC table; all links are idempotent.
    # The full decision linker and derive commands have detailed reports of their own;
    # refresh keeps its CLI focused on the incremental change summary below.
    with redirect_stdout(io.StringIO()):
        link_decisions.run(graph)
        if run_derive:
            derive.run_derive(graph, since, 3, 150)
    after_risk = _risk_snapshot(graph, since)
    after_active = _active_people(graph)
    # Report new decision activity only when a refreshed PR now has an IMPLEMENTS edge.
    changed_decisions = []
    if prs:
        result = graph.ro_query("MATCH (pr:PR)-[:IMPLEMENTS]->(d:Decision) WHERE pr.number IN $numbers RETURN DISTINCT pr.number,d.slug,d.title", {"numbers": [pr["number"] for pr in prs]})
        changed_decisions = [{"number": row[0], "slug": row[1], "title": row[2]} for row in result.result_set]
    team = team_memory or TeamMemory()
    observation_ids = _team_observations(graph, team, before_risk, after_risk, before_active, after_active,
                                         changed_decisions, now_ms)
    team.record_refresh(ts=now_ms, new_commits=len(commits), new_prs=len(prs), observation_ids=observation_ids)
    components = count_commits_per_component(commits)
    risk_changes = [(key, before_risk.get(key), after_risk.get(key)) for key in sorted(before_risk.keys() | after_risk.keys())
                    if before_risk.get(key) != after_risk.get(key)]
    summary = {"newCommits": len(commits), "newPRs": len(prs), "commitsPerComponent": components,
               "becameActive": sorted(after_active - before_active), "becameInactive": sorted(before_active - after_active),
               "riskChanges": risk_changes, "observationIds": observation_ids}
    print("Refresh summary")
    print(f"  New commits: {len(commits)}" + (" (none)" if not commits else ""))
    if components:
        print("  New commits per component: " + ", ".join(f"{k}={v}" for k, v in sorted(components.items())))
    print(f"  New PRs: {len(prs)}" + (" (none)" if not prs else ""))
    print("  Became Active: " + (", ".join(summary["becameActive"]) or "none"))
    print("  Became inactive: " + (", ".join(summary["becameInactive"]) or "none"))
    print("  Component recent-author changes: " +(", ".join(f"{k}: {old or 'unknown'} -> {new}" for k, old, new in risk_changes) or "none"))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Incrementally refresh Bus Factor's Delta graph")
    parser.add_argument("--no-pull", action="store_true", help="do not pull the local Delta clone")
    parser.add_argument("--no-github", action="store_true", help="do not fetch updated GitHub pull requests")
    args = parser.parse_args(argv)
    try:
        graph = get_graph()
        graph.client.connection.ping()
        run_refresh(graph=graph, no_pull=args.no_pull, no_github=args.no_github)
    except (RedisError, OSError, ConnectionError, RuntimeError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"Refresh failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
