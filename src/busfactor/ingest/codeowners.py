"""Parse Delta's declared CODEOWNERS rules."""

from pathlib import Path
import json

from busfactor.ingest.identity import normalize_login

ROOT = Path(__file__).resolve().parents[3]
CODEOWNERS = ROOT / "data" / "delta" / ".github" / "CODEOWNERS"


def parse_codeowners(contents: str) -> list[dict]:
    rows = []
    for line in contents.splitlines():
        parts = line.split("#", 1)[0].split()
        if len(parts) < 2:
            continue
        pattern = parts[0]
        clean = pattern.lstrip("/")
        module = clean.split("/", 1)[0] if "/" in clean else "root"
        rows.append({"pattern": pattern, "module": module, "owners": [owner.lstrip("@") for owner in parts[1:]]})
    return rows


def rows_for_loading(rows: list[dict]) -> list[dict]:
    """Pair each original CODEOWNERS spelling with its normalized graph key."""
    return [
        {
            **row,
            "owners": [
                {"login": normalize_login(handle), "handle": handle}
                for handle in row["owners"]
            ],
        }
        for row in rows
    ]


def main() -> None:
    rows = parse_codeowners(CODEOWNERS.read_text(encoding="utf-8"))
    if len(rows) != 9:
        raise ValueError(f"expected 9 CODEOWNERS rules, found {len(rows)}")
    for row in rows:
        print(f"{row['pattern']:<24} {row['module']:<12} {', '.join(row['owners'])}")
    print(f"Rules: {len(rows)}")
    output = ROOT / "data" / "raw" / "codeowners.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote: {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
