"""Derive PR-to-decision links from graph evidence and curated title keywords."""

import json
import re
import sys
from collections import Counter

from redis.exceptions import RedisError

from busfactor.db import ROOT, get_graph, load_query
from busfactor.decision_keywords import KEYWORDS
from busfactor.snapshot import read_input

RAW = ROOT / "data" / "raw"
HIGH_CONFIDENCE = "high"
LOW_CONFIDENCE = "low"


def strongest_evidence(existing: dict | None, via: str, confidence: str) -> dict:
    """Return merged evidence, retaining the strongest via and all evidence sources."""
    previous = existing or {}
    sources = list(dict.fromkeys([*previous.get("sources", []), via]))
    old_confidence = previous.get("confidence")
    if old_confidence == HIGH_CONFIDENCE or confidence != HIGH_CONFIDENCE and old_confidence:
        strongest_via = previous.get("via", via)
        strongest_confidence = old_confidence
    else:
        strongest_via = via
        strongest_confidence = confidence
    return {"via": strongest_via, "confidence": strongest_confidence, "sources": sources}


def validate_keywords() -> list[dict]:
    """Ensure all currently parsed RFC slugs are explicitly represented."""
    rfcs = read_input("rfcs")
    slugs = {rfc["slug"] for rfc in rfcs}
    missing = sorted(slugs - KEYWORDS.keys())
    extra = sorted(KEYWORDS.keys() - slugs)
    if missing or extra:
        raise ValueError(f"keyword table/RFC slug mismatch: missing={missing}, extra={extra}")
    if any(not isinstance(patterns, list) or any(not p for p in patterns) for patterns in KEYWORDS.values()):
        raise ValueError("each decision keyword entry must be an explicit list of non-empty patterns")
    return rfcs


def matching_patterns(title: str, slug: str) -> list[str]:
    """Return matching patterns, keeping the ICT abbreviation case-sensitive."""
    matched = []
    for pattern in KEYWORDS[slug]:
        flags = 0 if pattern == r"\bICT\b" else re.IGNORECASE
        if re.search(pattern, title, flags):
            matched.append(pattern)
    return matched


def title_matches(pr_titles: list[dict], rfcs: list[dict]) -> list[dict]:
    """Make one load row per PR/decision pair, preserving its first matching pattern."""
    rows = []
    for pr in pr_titles:
        title = pr.get("title") or ""
        for rfc in rfcs:
            matches = matching_patterns(title, rfc["slug"])
            if matches:
                rows.append({"pr": int(pr["number"]), "slug": rfc["slug"], "pattern": matches[0]})
    return rows


def _json(name: str) -> list[dict]:
    if __import__("os").getenv("BUSFACTOR_INPUT", "raw") == "snapshot":
        return read_input(name.removesuffix(".json"))
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def _pr_titles(graph) -> list[dict]:
    rows = graph.ro_query(load_query("04g_link_pr_titles")).result_set
    if rows:
        return [{"number": row[0], "title": row[1] or ""} for row in rows]
    # This path keeps the matcher useful before GitHub PR nodes have been loaded.
    commits = _json("git_log.json")
    titles = {}
    for commit in commits:
        number = commit.get("pr")
        if number is None:
            match = re.search(r"\(#(\d+)\)\s*$", commit.get("subject", ""))
            number = int(match.group(1)) if match else None
        if number is not None:
            titles.setdefault(int(number), commit.get("subject", ""))
    return [{"number": number, "title": title} for number, title in titles.items()]


def _print_results(graph, matches: list[dict], rfcs: list[dict]) -> None:
    via_counts = graph.ro_query(load_query("04h_implements_counts_by_via")).result_set
    print("IMPLEMENTS edges per via:")
    for via, count in via_counts:
        print(f"  {via}: {count}")

    by_decision = graph.ro_query(load_query("04i_implements_counts_by_decision")).result_set
    print("IMPLEMENTS edges per decision:")
    for slug, count in by_decision:
        print(f"  {slug}: {count}")
        recent = graph.ro_query(load_query("04j_recent_implements"), {"slug": slug}).result_set
        for number, title, merged_at, via, confidence in recent:
            print(f"    #{number} ({merged_at or 'date unknown'}, {via}/{confidence}): {title}")

    counts = Counter(row["slug"] for row in matches)
    print("Keyword title matches per decision:")
    examples: dict[str, list[str]] = {}
    titles = {int(pr["number"]): pr.get("title", "") for pr in _pr_titles(graph)}
    for row in matches:
        examples.setdefault(row["slug"], [])
        title = titles.get(row["pr"], "")
        if title not in examples[row["slug"]] and len(examples[row["slug"]]) < 5:
            examples[row["slug"]].append(title)
    for rfc in rfcs:
        slug = rfc["slug"]
        print(f"  {slug}: {counts[slug]}")
        for title in examples.get(slug, []):
            print(f"    - {title}")


def run(graph) -> None:
    rfcs = validate_keywords()
    matches = title_matches(_pr_titles(graph), rfcs)
    # Remove stale low-only edges so changed keyword patterns are reflected on replay.
    graph.query(load_query("04k_delete_stale_keyword_links"))

    for name in ("04d_derive_implements_issue_ref", "04e_derive_implements_rfc_doc"):
        result = graph.query(load_query(name))
        print(f"{name}: relationships created={result.relationships_created}")

    query = load_query("04f_load_implements_keyword")
    for start in range(0, len(matches), 500):
        graph.query(query, {"rows": matches[start:start + 500]})
    print(f"04f_load_implements_keyword: rows={len(matches)}, batches={(len(matches) + 499) // 500}")
    _print_results(graph, matches, rfcs)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args not in ([], ["--from-snapshot"]):
        print("Usage: python -m busfactor.link_decisions [--from-snapshot]", file=sys.stderr)
        return 2
    if args:
        __import__("os").environ["BUSFACTOR_INPUT"] = "snapshot"
    try:
        graph = get_graph()
        graph.client.connection.ping()
        run(graph)
    except (RedisError, OSError, ConnectionError) as exc:
        print(f"FalkorDB is unreachable or decision linking failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
