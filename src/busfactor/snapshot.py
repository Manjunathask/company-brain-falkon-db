"""Export and read the small, public, parsed inputs used to build the graph."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
SNAPSHOT = ROOT / "data" / "snapshot"
INPUTS = ("git_log", "rfcs", "codeowners", "prs", "rfc_issues", "identities", "head_files")


def read_input(name: str):
    """Read one parsed input from the snapshot when selected, otherwise raw cache."""
    if name not in INPUTS:
        raise ValueError(f"unknown snapshot input: {name}")
    if os.getenv("BUSFACTOR_INPUT", "raw") == "snapshot":
        path = SNAPSHOT / f"{name}.json.gz"
        if not path.exists():
            raise FileNotFoundError(f"Snapshot input missing: {path}")
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    path = RAW / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Parsed input missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _git_head() -> str | None:
    repo = ROOT / "data" / "delta"
    if not (repo / ".git").exists():
        return None
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()


def export() -> dict:
    SNAPSHOT.mkdir(parents=True, exist_ok=True)
    values = {name: json.loads((RAW / f"{name}.json").read_text(encoding="utf-8"))
              for name in INPUTS[:-1]}
    repo = ROOT / "data" / "delta"
    if (repo / ".git").exists():
        values["head_files"] = subprocess.run(
            ["git", "-C", str(repo), "ls-files"], check=True,
            capture_output=True, text=True, encoding="utf-8",
        ).stdout.splitlines()
        values["head_files"] = sorted(path.replace("\\", "/") for path in values["head_files"])
    else:
        head_path = RAW / "head_files.json"
        if head_path.exists():
            values["head_files"] = json.loads(head_path.read_text(encoding="utf-8"))
        else:
        # Each git row records whether its touched path exists at the checked-out HEAD.
            values["head_files"] = sorted({f["path"].replace("\\", "/")
                                            for c in values["git_log"] for f in c.get("files", [])
                                            if f.get("exists")})
    counts = {}
    for name, value in values.items():
        payload = (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        target = SNAPSHOT / f"{name}.json.gz"
        with target.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as compressed:
                compressed.write(payload)
        counts[name] = len(value)
    manifest = {
        "format_version": 1,
        "source": "Public GitHub data from delta-io/delta only; no private or login-protected sources.",
        "repository": "https://github.com/delta-io/delta",
        "git_head_sha": _git_head(),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
    }
    (SNAPSHOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    total = sum(p.stat().st_size for p in SNAPSHOT.iterdir() if p.is_file())
    print(f"Snapshot exported: {SNAPSHOT.relative_to(ROOT)} ({total:,} bytes; {total / 1024:.1f} KiB)")
    print("Counts: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage the reproducible public data snapshot")
    parser.add_argument("command", choices=["export"])
    args = parser.parse_args(argv)
    if args.command == "export":
        try:
            export()
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Snapshot export failed: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
