"""Parse the Proposed, Accepted, and Rejected RFC tables."""

from datetime import date, datetime, timezone
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
README = ROOT / "data" / "delta" / "protocol_rfcs" / "README.md"
EXPECTED = {"proposed": 11, "accepted": 7, "rejected": 1}


def _epoch_ms(value: str) -> int:
    parsed = datetime.combine(date.fromisoformat(value.strip()), datetime.min.time(), tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def parse_rfcs(markdown: str) -> list[dict]:
    section = None
    results = []
    for line in markdown.splitlines():
        heading = re.match(r"^###\s+(Proposed|Accepted|Rejected) RFCs", line, re.I)
        if heading:
            section = heading.group(1).lower()
            continue
        if line.startswith("### "):
            section = None
            continue
        if not section or not line.strip().startswith("|") or re.match(r"^\|\s*[:-]+", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        expected_columns = 4 if section == "proposed" else 5
        if len(cells) != expected_columns or cells[0].lower().startswith("date "):
            continue
        dates = [re.search(r"\d{4}-\d{2}-\d{2}", cells[0]).group()]
        if section != "proposed":
            dates.append(re.search(r"\d{4}-\d{2}-\d{2}", cells[1]).group())
        file_cell = cells[1] if section == "proposed" else cells[2]
        link = re.search(r"\[[^]]*\]\((https://github\.com/[^)]+/blob/[^)]+)\)", file_cell)
        issue_match = re.search(r"/issues/(\d+)", cells[2] if section == "proposed" else cells[3])
        if not link or not issue_match:
            raise ValueError(f"could not parse RFC row: {line}")
        url_path = link.group(1).split("/blob/", 1)[1]
        slug = Path(url_path).stem
        repo_path = "/".join(url_path.split("/")[1:])
        title = cells[3] if section == "proposed" else cells[4]
        results.append({
            "slug": slug,
            "title": title,
            "status": section,
            "proposedOn": _epoch_ms(dates[0]),
            "decidedOn": _epoch_ms(dates[1]) if len(dates) == 2 else None,
            "issue": int(issue_match.group(1)),
            "path": repo_path,
            "module": repo_path.split("/", 1)[0],
        })
    counts = {status: sum(row["status"] == status for row in results) for status in EXPECTED}
    if counts != EXPECTED:
        raise ValueError(f"expected RFC counts {EXPECTED}, found {counts}")
    if len(results) != 19:
        raise ValueError(f"expected exactly 19 RFCs, found {len(results)}")
    return results


def main() -> None:
    rows = parse_rfcs(README.read_text(encoding="utf-8"))
    output = ROOT / "data" / "raw" / "rfcs.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(f"{'STATUS':<10} {'PROPOSED':<12} {'DECIDED':<12} {'ISSUE':>6}  {'SLUG':<42} PATH")
    for row in rows:
        print(f"{row['status']:<10} {row['proposedOn']:<12} {str(row['decidedOn'] or ''):<12} {row['issue']:>6}  {row['slug']:<42} {row['path']}")
    print(f"RFCs: {len(rows)} (proposed=11, accepted=7, rejected=1)")
    print(f"Wrote: {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
