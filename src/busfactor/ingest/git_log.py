"""Parse recent Delta git history and cache the normalized commit rows."""

import json
import os
from collections import Counter
from pathlib import Path
import re
import subprocess

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
RECORD = "\x1e"
FIELD = "\x1f"
HEADER = "%x1e%H%x1f%ct%x1f%s%x1f%ae%x1f%an"


def _area(subject: str) -> str | None:
    match = re.match(r"^\[([^\]]+)\]", subject)
    return match.group(1).strip().lower() if match else None


def _pr(subject: str) -> int | None:
    match = re.search(r"\(#(\d+)\)\s*$", subject)
    return int(match.group(1)) if match else None


def parse_git_log(output: str) -> list[dict]:
    commits = []
    for record in output.split(RECORD):
        record = record.strip("\r\n")
        if not record:
            continue
        header, *numstat_lines = record.splitlines()
        fields = header.split(FIELD)
        if len(fields) != 5:
            raise ValueError(f"malformed git log record header: {header!r}")
        sha, timestamp, subject, email, author_name = fields
        files = []
        for line in numstat_lines:
            if not line:
                continue
            values = line.split("\t", 2)
            if len(values) != 3:
                raise ValueError(f"malformed numstat line: {line!r}")
            added, deleted, path = values
            parts = path.replace("\\", "/").split("/")
            files.append({
                "path": path,
                "module": parts[0] if len(parts) > 1 else "root",
                "added": int(added) if added.isdigit() else 0,
                "deleted": int(deleted) if deleted.isdigit() else 0,
            })
        commits.append({
            "sha": sha,
            "ts": int(timestamp) * 1000,
            "subject": subject,
            "area": _area(subject),
            "pr": _pr(subject),
            "authorEmail": email.strip().lower(),
            "authorName": author_name,
            "files": files,
        })
    return commits


def collect_commits(repo: Path, since: str) -> list[dict]:
    command = [
        "git", "-C", str(repo), "-c", "core.quotepath=off", "log",
        f"--since={since}", "--no-merges", "--no-renames", "--numstat",
        f"--format={HEADER}",
    ]
    output = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8").stdout
    return parse_git_log(output)


def summarize(commits: list[dict]) -> str:
    emails = {c["authorEmail"] for c in commits}
    files = {f["path"] for c in commits for f in c["files"]}
    modules = Counter()
    for commit in commits:
        modules.update({file["module"] for file in commit["files"]})
    areas = Counter(c["area"] for c in commits if c["area"])
    with_pr = sum(c["pr"] is not None for c in commits)
    lines = [
        f"Commits: {len(commits)}",
        f"Distinct author emails: {len(emails)}",
        f"Distinct files: {len(files)}",
        "Modules (commits): " + ", ".join(f"{k}={v}" for k, v in modules.most_common()),
        f"Commits with PR number: {with_pr}",
        "Top 10 area tags: " + ", ".join(f"{k}={v}" for k, v in areas.most_common(10)),
    ]
    return "\n".join(lines)


def main() -> None:
    repo = Path(os.getenv("DELTA_REPO", "data/delta"))
    if not repo.is_absolute():
        repo = ROOT / repo
    commits = collect_commits(repo, os.getenv("GIT_SINCE", "2024-10-15"))
    output = ROOT / "data" / "raw" / "git_log.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(commits, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(summarize(commits))
    print(f"Wrote: {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
