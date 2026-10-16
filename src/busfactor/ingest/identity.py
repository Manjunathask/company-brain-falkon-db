"""Resolve git author emails to stable person keys."""

import re
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def normalize_login(handle: str) -> str:
    """Return the case-insensitive stable key for a GitHub login."""
    return handle.strip().lstrip("@").lower()


def load_api_map() -> dict[str, str | None]:
    """Load the GitHub email identity map cached by the API ingestion step."""
    path = ROOT / "data" / "raw" / "identities.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {email.strip().lower(): login for email, login in data.items()}


def resolve_person_key(email: str, api_map: dict[str, str | None] | None = None) -> str:
    address = email.strip().lower()
    api_map = api_map or {}
    login = next(
        (value for key, value in api_map.items() if key.strip().lower() == address),
        None,
    )
    if login:
        return normalize_login(login)
    match = re.fullmatch(r"(?:\d+\+)?([^@]+)@users\.noreply\.github\.com", address)
    if match:
        return normalize_login(match.group(1))
    return f"email:{address}"
