from __future__ import annotations

import re
from pathlib import Path


class PermissionError(ValueError):
    """Raised when a packet attempts to cross its declared boundary."""


SECRET_MARKERS = (
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "api_key=",
    "apikey=",
    "secret=",
    "password=",
)


def safe_relative_path(root: Path, candidate: Path) -> Path:
    root = root.resolve()
    candidate = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    try:
        return candidate.relative_to(root)
    except ValueError as exc:
        raise PermissionError(f"path escapes project root: {candidate}") from exc


def assert_write_allowed(root: Path, candidate: Path, allowed_prefixes: tuple[str, ...]) -> Path:
    relative = safe_relative_path(root, candidate)
    normalized = relative.as_posix()
    if not allowed_prefixes:
        raise PermissionError("no write paths declared")
    if not any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in allowed_prefixes):
        raise PermissionError(f"write path is not allowed: {normalized}")
    return relative


def assert_no_secret_markers(text: str) -> None:
    lowered = text.lower()
    for marker in SECRET_MARKERS:
        if marker.lower() in lowered:
            raise PermissionError(f"secret-like marker in context: {marker}")
    if re.search(r"\b(sk|pk)-[A-Za-z0-9]{20,}\b", text):
        raise PermissionError("token-like value in context")
