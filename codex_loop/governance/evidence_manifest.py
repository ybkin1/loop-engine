from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path, PurePosixPath

from codex_loop.governance.governor_lib import (
    GovernanceError,
    canonical_json,
    dump_yaml,
    load_yaml,
    safe_project_path,
)

MAX_FILES = 256
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024
MANIFEST_FIELDS = {
    "schema", "manifest_id", "task_id", "gate_id", "authority_ref", "evidence_root",
    "limits", "files", "file_count", "total_bytes", "ordered_entries_sha256",
    "semantic_sha256", "created_at", "created_by",
}
LIMIT_FIELDS = {"max_file_count", "max_per_file_bytes", "max_total_bytes", "stream_chunk_bytes"}
FILE_FIELDS = {"path", "role", "required", "sha256", "size", "mtime_ns"}
ROLES = {"source", "test", "command", "stdout", "stderr", "result", "protected"}


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _normalized_relative(raw: str) -> str:
    if not isinstance(raw, str) or not raw or "\x00" in raw or "\\" in raw or ":" in raw:
        raise GovernanceError("EVIDENCE_PATH_INVALID", f"Manifest path is not canonical: {raw!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise GovernanceError("EVIDENCE_PATH_INVALID", f"Manifest path escapes its root: {raw!r}")
    return path.as_posix()


def _is_reparse(stat_result) -> bool:
    return bool(getattr(stat_result, "st_file_attributes", 0) & 0x400)


def _checked_path(root: Path, relative: str) -> Path:
    normalized = _normalized_relative(relative)
    root = root.resolve()
    cursor = root
    for part in PurePosixPath(normalized).parts:
        cursor = cursor / part
        try:
            current = os.lstat(cursor)
        except FileNotFoundError:
            raise GovernanceError("EVIDENCE_SUBJECT_MISSING", f"Evidence subject missing: {normalized}")
        if os.path.islink(cursor) or _is_reparse(current):
            raise GovernanceError("EVIDENCE_REPARSE_FORBIDDEN", f"Reparse subject is forbidden: {normalized}")
    try:
        cursor.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as exc:
        raise GovernanceError("EVIDENCE_PATH_INVALID", f"Evidence subject escapes project: {normalized}") from exc
    if not cursor.is_file():
        raise GovernanceError("EVIDENCE_PATH_INVALID", f"Evidence subject is not a regular file: {normalized}")
    return cursor


def _identity(value) -> tuple[int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def stream_fingerprint(root: Path, entry: dict, per_file_limit: int, chunk_bytes: int) -> dict:
    path = _checked_path(root, entry["path"])
    before = os.stat(path, follow_symlinks=False)
    if before.st_size > per_file_limit:
        raise GovernanceError("EVIDENCE_LIMIT_EXCEEDED", f"Evidence file exceeds limit: {entry['path']}")
    digest = hashlib.sha256()
    total = 0
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if _identity(opened) != _identity(before) or _is_reparse(opened):
            raise GovernanceError("EVIDENCE_SUBJECT_CHANGED", f"Evidence identity changed before open: {entry['path']}")
        while True:
            chunk = os.read(descriptor, chunk_bytes)
            if not chunk:
                break
            total += len(chunk)
            if total > per_file_limit:
                raise GovernanceError("EVIDENCE_LIMIT_EXCEEDED", f"Evidence file exceeds limit: {entry['path']}")
            digest.update(chunk)
        opened_after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after = os.stat(path, follow_symlinks=False)
    if _identity(before) != _identity(opened_after) or _identity(before) != _identity(after):
        raise GovernanceError("EVIDENCE_SUBJECT_CHANGED", f"Evidence changed while hashing: {entry['path']}")
    actual = {
        "path": entry["path"], "role": entry["role"], "required": entry["required"],
        "sha256": digest.hexdigest().upper(), "size": total, "mtime_ns": after.st_mtime_ns,
    }
    if actual != entry:
        raise GovernanceError("EVIDENCE_FINGERPRINT_MISMATCH", f"Evidence fingerprint mismatch: {entry['path']}")
    return actual


def verify_evidence_manifest(root: Path, manifest_relative: str) -> dict:
    root = root.resolve()
    manifest_path = safe_project_path(root, manifest_relative)
    if not manifest_path.is_file():
        raise GovernanceError("EVIDENCE_MANIFEST_REQUIRED", f"Evidence manifest missing: {manifest_relative}")
    manifest = load_yaml(manifest_path)
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS or manifest.get("schema") != "EvidenceManifest/v1":
        raise GovernanceError("EVIDENCE_MANIFEST_INVALID", "EvidenceManifest/v1 fields are invalid")
    limits = manifest.get("limits")
    if not isinstance(limits, dict) or set(limits) != LIMIT_FIELDS:
        raise GovernanceError("EVIDENCE_MANIFEST_INVALID", "Evidence limits are invalid")
    caps = (limits["max_file_count"], limits["max_per_file_bytes"], limits["max_total_bytes"])
    if any(not isinstance(value, int) or value <= 0 for value in caps):
        raise GovernanceError("EVIDENCE_MANIFEST_INVALID", "Evidence limits must be positive integers")
    if caps[0] > MAX_FILES or caps[1] > MAX_FILE_BYTES or caps[2] > MAX_TOTAL_BYTES or limits["stream_chunk_bytes"] != CHUNK_BYTES:
        raise GovernanceError("EVIDENCE_LIMIT_EXCEEDED", "Evidence manifest raises approved hard limits")
    files = manifest.get("files")
    if not isinstance(files, list) or not files or len(files) > caps[0]:
        raise GovernanceError("EVIDENCE_LIMIT_EXCEEDED", "Evidence file list is empty or oversized")
    normalized = []
    seen = set()
    evidence_root = _normalized_relative(manifest["evidence_root"])
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != FILE_FIELDS or entry.get("role") not in ROLES:
            raise GovernanceError("EVIDENCE_MANIFEST_INVALID", "Evidence file entry is invalid")
        path = _normalized_relative(entry.get("path"))
        folded = path.casefold()
        if folded in seen:
            raise GovernanceError("EVIDENCE_PATH_COLLISION", f"Duplicate/case-colliding path: {path}")
        seen.add(folded)
        if entry["role"] in {"command", "stdout", "stderr", "result"} and not path.startswith(evidence_root + "/"):
            raise GovernanceError("EVIDENCE_PATH_INVALID", f"Role must be beneath evidence root: {path}")
        if entry.get("required") is not True or not isinstance(entry.get("size"), int) or not isinstance(entry.get("mtime_ns"), int):
            raise GovernanceError("EVIDENCE_MANIFEST_INVALID", f"Required evidence metadata is invalid: {path}")
        if not isinstance(entry.get("sha256"), str) or len(entry["sha256"]) != 64:
            raise GovernanceError("EVIDENCE_MANIFEST_INVALID", f"Evidence SHA-256 is invalid: {path}")
        normalized.append(dict(entry, path=path, sha256=entry["sha256"].upper()))
    ordered = sorted(normalized, key=lambda item: item["path"].casefold())
    ordered_hash = _sha(canonical_json(ordered).encode("utf-8"))
    if manifest["file_count"] != len(ordered) or manifest["ordered_entries_sha256"] != ordered_hash:
        raise GovernanceError("EVIDENCE_MANIFEST_HASH_MISMATCH", "Evidence ordered-entry binding mismatch")
    total = 0
    for entry in ordered:
        total += stream_fingerprint(root, entry, caps[1], limits["stream_chunk_bytes"])["size"]
        if total > caps[2]:
            raise GovernanceError("EVIDENCE_LIMIT_EXCEEDED", "Evidence total exceeds manifest limit")
    if manifest["total_bytes"] != total:
        raise GovernanceError("EVIDENCE_MANIFEST_HASH_MISMATCH", "Evidence total-byte binding mismatch")
    semantic = {key: value for key, value in manifest.items() if key not in {"semantic_sha256", "created_at"}}
    if manifest["semantic_sha256"] != _sha(canonical_json(semantic).encode("utf-8")):
        raise GovernanceError("EVIDENCE_MANIFEST_HASH_MISMATCH", "Evidence semantic hash mismatch")
    return {
        "manifest_file_sha256": _sha(manifest_path.read_bytes()),
        "ordered_entries_sha256": ordered_hash,
        "semantic_sha256": manifest["semantic_sha256"],
        "file_count": len(ordered),
        "total_bytes": total,
    }


def write_manifest_create_only(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (dump_yaml(manifest) + "\n").encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise GovernanceError("CONFLICT", f"Evidence manifest is immutable: {path}") from exc
    finally:
        Path(temporary).unlink(missing_ok=True)
