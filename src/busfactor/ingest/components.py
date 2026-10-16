"""Map repository paths to stable, explainable code components.

Source components use the first directory below a known Java/Scala/Python package
root, so production and test files for the same package share expertise. Explicit
package prefixes handle common layouts; unfamiliar reverse-DNS roots drop their
first three package segments. Test resources share a dedicated fixture component.
Other paths use two directory segments when available; a top-level file is grouped
under ``<first segment>/(files)`` and root-level files use ``root``.
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
import re
from collections import Counter

from busfactor.db import ROOT, get_graph

SOURCE_PATH = re.compile(
    r"^(?P<project>.+?)/src/(?P<phase>main|test)/(?P<language>scala(?:-[^/]+)?|java|python|resources)/(?P<rest>.+)$"
)

# Longest prefixes win so narrower Spark and Kernel package roots are preserved.
PACKAGE_PREFIXES = tuple(sorted((
    "io/delta/spark/internal/v2",
    "io/delta/kernel/spark",
    "io/delta/sharing/spark",
    "io/delta/standalone/internal",
    "io/delta/kernel/defaults/internal",
    "org/apache/spark/sql/delta",
    "com/databricks/spark",
    "org/apache/iceberg",
    "io/delta/standalone",
    "io/delta/kernel/defaults",
    "io/delta/kernel/internal",
    "io/delta/kernel",
    "io/delta/flink",
    "io/delta/sharing",
    "io/delta/storage",
    "io/delta",
    "org/apache/spark/sql",
    "io/unitycatalog",
), key=len, reverse=True))


def _component_and_rule(path: str) -> tuple[str, str]:
    """Return a component and the mapping rule used for one repository path."""
    match = SOURCE_PATH.match(path.replace("\\", "/"))
    if match:
        project, phase, language, rest = match.group("project", "phase", "language", "rest")
        if phase == "test" and language == "resources":
            return f"{project}/(test-resources)", "source/test-resources"
        if phase == "main" and language == "resources":
            parts = PurePosixPath(rest).parts
            directory = parts[0] if "/" in rest else "(core)"
            return f"{project}/{directory}", "source/main-resources-directory"

        remainder = None
        for prefix in PACKAGE_PREFIXES:
            if rest == prefix:
                remainder = ""
                break
            if rest.startswith(prefix + "/"):
                remainder = rest[len(prefix) + 1:]
                break
        if remainder is not None:
            rule = "source/explicit-package-prefix"
        else:
            parts = PurePosixPath(rest).parts
            if parts and parts[0] in {"org", "com", "io", "net"}:
                # Generic reverse-DNS fallback: org/example/project/a/File.java
                # drops the first three package segments, then uses the next dir.
                remainder = "/".join(parts[3:])
                rule = "source/reverse-DNS-fallback"
            else:
                remainder = rest
                rule = "source/relative-package-directory"

        # A single remaining segment is the source file itself, not a directory.
        suffix = PurePosixPath(remainder).parts if "/" in remainder else ()
        return f"{project}/{suffix[0] if suffix else '(core)'}", rule

    normalized = path.replace("\\", "/").strip("/")
    parts = PurePosixPath(normalized).parts
    if len(parts) == 1:
        return "root", "non-source/root-file"
    if len(parts) >= 3:
        return "/".join(parts[:2]), "non-source/nested-directory"
    return f"{parts[0]}/(files)", "non-source/top-level-file-bucket"


def component_of(path: str) -> str:
    """Return a component name for a repository-relative POSIX path.

    A source package maps to ``<project>/<first remaining directory>`` or
    ``<project>/(core)`` for a package-root file. Main and test code share a
    component; test resources map to ``<project>/(test-resources)``. Explicit
    package prefixes are preferred, then an unfamiliar ``org``/``com``/``io``/
    ``net`` reverse-DNS prefix drops three segments before choosing a directory.
    Other paths with at least three segments map to their first two directories;
    two-segment paths map to ``<first>/(files)``, and root files map to ``root``.
    """
    return _component_and_rule(path)[0]


def _source_paths() -> list[str]:
    raw = ROOT / "data" / "raw" / "git_log.json"
    if not raw.exists():
        raise FileNotFoundError(f"Parsed input missing: {raw}; run busfactor.ingest.git_log first")
    commits = json.loads(raw.read_text(encoding="utf-8"))
    paths = {f["path"] for commit in commits for f in commit.get("files", [])}
    rfc_path = ROOT / "data" / "raw" / "rfcs.json"
    if rfc_path.exists():
        paths.update(row["path"] for row in json.loads(rfc_path.read_text(encoding="utf-8")))
    return sorted(paths)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize file components in the live delta graph")
    args = parser.parse_args()
    del args
    paths = _source_paths()
    graph = get_graph()
    since = int((datetime.now(timezone.utc) - timedelta(days=730)).timestamp() * 1000)
    try:
        rows = graph.query(
            "MATCH (:Person)-[:AUTHORED]->(commit:Commit)-[:TOUCHED]->(f:File)-[:IN_COMPONENT]->(c:Component) "
            "WHERE commit.ts > $since "
            "RETURN c.name, count(*) AS touches ORDER BY touches DESC, c.name LIMIT 40",
            {"since": since},
        ).result_set
        component_count = graph.query("MATCH (c:Component) RETURN count(c)").result_set[0][0]
    finally:
        graph.client.close()
    print(f"Components: {component_count}")
    source_components = {component_of(path) for path in paths if SOURCE_PATH.match(path.replace("\\", "/"))}
    print(f"Source components: {len(source_components)}")
    print("Top 40 components by recent file touches:")
    for name, count in rows:
        print(f"  {name}: {count}")
    rule_counts = Counter(_component_and_rule(path)[1] for path in paths)
    fallback_rules = {rule: count for rule, count in rule_counts.items() if "fallback" in rule}
    print("Unplaced paths: 0 (every path has a deterministic mapping rule)")
    print(f"Fallback paths: {sum(fallback_rules.values())}")
    print("Path counts by placement rule:")
    for rule, count in sorted(rule_counts.items()):
        print(f"  {rule}: {count}")
    for rule in fallback_rules:
        examples = [path for path in paths if _component_and_rule(path)[1] == rule][:5]
        if examples:
            print(f"Examples for {rule}:")
            for path in examples:
                print(f"  {path} -> {component_of(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
