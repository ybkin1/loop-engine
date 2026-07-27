from __future__ import annotations

import hashlib
import json
import os
import secrets
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

from codex_loop.governance.evidence_manifest import CHUNK_BYTES, verify_evidence_manifest, write_manifest_create_only
from codex_loop.governance.governor_lib import GovernanceError, current_task_id, gates, safe_project_path, task_status


OUTPUT_LIMIT = 8 * 1024 * 1024
RESULT_SCHEMA = "UnittestResultEnvelope/v1"
RESULT_LIMIT = 2 * 1024 * 1024
RESULT_FIELDS = {
    "schema", "run_nonce", "adapter_fingerprint", "test_fingerprints", "discovered_test_ids",
    "tests_run", "failures", "errors", "skipped", "unexpected_successes", "successful",
    "started_at", "completed_at", "result_sha256",
}
PROTOCOL_FIELDS = {
    "schema", "adapter_path", "adapter_fingerprint", "test_paths", "test_fingerprints", "expected_test_ids",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _fingerprint(root: Path, value: str, external: bool = False) -> dict:
    raw = Path(value)
    path = raw.resolve() if external and raw.is_absolute() else safe_project_path(root, value)
    if not path.is_file() or path.is_symlink():
        raise GovernanceError("BASELINE_MISSING", f"Validation subject must be a regular file: {value}")
    before = path.stat()
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            digest.update(chunk)
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    ):
        raise GovernanceError("STALE_FINAL_VALIDATION", f"Validation subject changed while reading: {value}")
    try:
        recorded = path.relative_to(root).as_posix()
    except ValueError:
        recorded = path.as_posix()
    return {"path": recorded, "sha256": digest.hexdigest().upper(), "size": total, "mtime_ns": after.st_mtime_ns}


def _write_bytes_create_only(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags)
    except FileExistsError as exc:
        raise GovernanceError("CONFLICT", f"Validation evidence is immutable: {path}") from exc
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _active_gate(root: Path) -> dict:
    task_id = current_task_id(root)
    matches = [
        item for item in gates(root) if item.get("task_id") == task_id and item.get("status") == "approved"
        and item.get("execution_status") == "in_progress"
    ]
    if task_status(root, task_id) != "in_progress" or len(matches) != 1:
        raise GovernanceError("AUTHORITY_MISSING", "Controlled validation requires one Gate-bound in-progress execution")
    return matches[0]


def _controlled_environment(config: dict) -> tuple[dict, dict]:
    requested = config.get("environment")
    if not isinstance(requested, dict) or requested.get("PYTHONPATH") != "absent":
        raise GovernanceError("VALIDATION_ERROR", "Controlled environment must explicitly remove PYTHONPATH")
    allowed = {"PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED", "PYTHONIOENCODING", "PYTHONPATH"}
    if set(requested) - allowed:
        raise GovernanceError("VALIDATION_ERROR", "Controlled environment contains an unapproved key")
    environment = {}
    for key in ("SystemRoot", "TEMP", "TMP", "PATH", "PATHEXT", "COMSPEC"):
        if os.environ.get(key):
            environment[key] = os.environ[key]
    for key, value in requested.items():
        if key != "PYTHONPATH":
            environment[key] = str(value)
    environment.pop("PYTHONPATH", None)
    hashes = {key: _sha(value.encode("utf-8")) for key, value in sorted(environment.items())}
    return environment, hashes


def _execute(argv: list[str], cwd: Path, environment: dict, timeout: int) -> tuple[bytes, bytes, int, bool, bool]:
    with tempfile.TemporaryDirectory() as temporary:
        stdout_path = Path(temporary) / "stdout.bin"
        stderr_path = Path(temporary) / "stderr.bin"
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=stdout, stderr=stderr, shell=False)
            deadline = time.monotonic() + timeout
            timed_out = False
            output_limited = False
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    timed_out = True
                    process.kill()
                    break
                if stdout_path.stat().st_size > OUTPUT_LIMIT or stderr_path.stat().st_size > OUTPUT_LIMIT:
                    output_limited = True
                    process.kill()
                    break
                time.sleep(0.02)
            process.wait(timeout=5)
        stdout_data = stdout_path.read_bytes()
        stderr_data = stderr_path.read_bytes()
    if len(stdout_data) > OUTPUT_LIMIT or len(stderr_data) > OUTPUT_LIMIT:
        output_limited = True
        stdout_data = stdout_data[:OUTPUT_LIMIT]
        stderr_data = stderr_data[:OUTPUT_LIMIT]
    return stdout_data, stderr_data, process.returncode, timed_out, output_limited


def _identity(value) -> tuple[int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def _stable_bytes(path: Path, limit: int | None = None) -> tuple[Path, bytes, os.stat_result]:
    raw = path.absolute()
    if raw.is_symlink():
        raise GovernanceError("TEST_PROTOCOL_REPARSE_FORBIDDEN", f"Test protocol subject is a symlink: {raw}")
    before = os.stat(raw, follow_symlinks=False)
    if getattr(before, "st_file_attributes", 0) & 0x400:
        raise GovernanceError("TEST_PROTOCOL_REPARSE_FORBIDDEN", f"Test protocol subject is a reparse point: {raw}")
    if limit is not None and before.st_size > limit:
        raise GovernanceError("TEST_RESULT_INVALID", f"Structured unittest result exceeds {limit} bytes")
    descriptor = os.open(raw, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    try:
        opened = os.fstat(descriptor)
        if _identity(opened) != _identity(before):
            raise GovernanceError("TEST_PROTOCOL_CHANGED", f"Test protocol subject changed before open: {raw}")
        chunks = []
        total = 0
        while True:
            chunk = os.read(descriptor, CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if limit is not None and total > limit:
                raise GovernanceError("TEST_RESULT_INVALID", f"Structured unittest result exceeds {limit} bytes")
            chunks.append(chunk)
        opened_after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after = os.stat(raw, follow_symlinks=False)
    if _identity(before) != _identity(opened_after) or _identity(before) != _identity(after):
        raise GovernanceError("TEST_PROTOCOL_CHANGED", f"Test protocol subject changed while reading: {raw}")
    return raw.resolve(), b"".join(chunks), after


def _protocol_fingerprint(path: Path) -> dict:
    path, data, stat = _stable_bytes(path)
    return {
        "path": path.as_posix(), "sha256": _sha(data),
        "size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
    }


def _protocol_command(config: dict, argv: list[str], envelope_path: Path, nonce: str) -> tuple[list[str], dict]:
    protocol = config.get("test_result_protocol")
    if not isinstance(protocol, dict) or set(protocol) != PROTOCOL_FIELDS or protocol.get("schema") != RESULT_SCHEMA:
        raise GovernanceError("UNSUPPORTED_TEST_PROTOCOL", "Controlled validation requires UnittestResultEnvelope/v1")
    adapter_raw = protocol.get("adapter_path")
    test_values = protocol.get("test_paths")
    if not isinstance(adapter_raw, str) or not adapter_raw or not isinstance(test_values, list):
        raise GovernanceError("UNSUPPORTED_TEST_PROTOCOL", "Gate-bound adapter and test paths are invalid")
    if any(not isinstance(item, str) or not item for item in test_values):
        raise GovernanceError("UNSUPPORTED_TEST_PROTOCOL", "Gate-bound test path is invalid")
    adapter = Path(adapter_raw).resolve()
    tests = [Path(item).resolve() for item in test_values]
    expected_argv = [str(Path(argv[0]).resolve()), "-B", str(adapter)] + [str(path) for path in tests]
    actual_argv = [str(Path(argv[0]).resolve()), *argv[1:]]
    if actual_argv != expected_argv or len(tests) != 1:
        raise GovernanceError("UNSUPPORTED_TEST_PROTOCOL", "Controlled argv does not match the Gate-bound unittest adapter")
    adapter_fingerprint = _protocol_fingerprint(adapter)
    test_fingerprints = [_protocol_fingerprint(path) for path in tests]
    if protocol.get("adapter_fingerprint") != adapter_fingerprint or protocol.get("test_fingerprints") != test_fingerprints:
        raise GovernanceError("STALE_TEST_PROTOCOL", "Gate-bound adapter or test fingerprint drifted")
    expected_ids = protocol.get("expected_test_ids")
    if (not isinstance(expected_ids, list) or not expected_ids
            or any(not isinstance(item, str) or not item for item in expected_ids)
            or len(expected_ids) != len(set(expected_ids))):
        raise GovernanceError("TEST_RESULT_INVALID", "Gate-bound expected test IDs are invalid")
    command = argv + ["--result-envelope", str(envelope_path), "--run-nonce", nonce]
    return command, {"adapter": adapter_fingerprint, "tests": test_fingerprints, "expected_ids": expected_ids}


def _verify_envelope(path: Path, nonce: str, binding: dict) -> dict:
    if not path.is_file():
        raise GovernanceError("TEST_RESULT_MISSING", "Structured unittest result envelope is missing")

    def unique_object(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise GovernanceError("TEST_RESULT_INVALID", f"Duplicate structured unittest result field: {key}")
            result[key] = value
        return result

    try:
        _, raw, _ = _stable_bytes(path, RESULT_LIMIT)
        envelope = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GovernanceError("TEST_RESULT_INVALID", "Structured unittest result envelope is malformed") from exc
    if not isinstance(envelope, dict) or set(envelope) != RESULT_FIELDS or envelope.get("schema") != RESULT_SCHEMA:
        raise GovernanceError("TEST_RESULT_INVALID", "Structured unittest result envelope fields are invalid")
    semantic = {key: value for key, value in envelope.items() if key != "result_sha256"}
    canonical = json.dumps(semantic, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if envelope["result_sha256"] != _sha(canonical):
        raise GovernanceError("TEST_RESULT_INVALID", "Structured unittest result hash mismatch")
    if envelope["run_nonce"] != nonce:
        raise GovernanceError("TEST_RESULT_INVALID", "Structured unittest result nonce mismatch")
    if envelope["adapter_fingerprint"] != binding["adapter"] or envelope["test_fingerprints"] != binding["tests"]:
        raise GovernanceError("TEST_RESULT_INVALID", "Structured unittest result fingerprint mismatch")
    discovered = envelope["discovered_test_ids"]
    list_fields = ("failures", "errors", "skipped", "unexpected_successes")
    if (not isinstance(envelope["run_nonce"], str) or not isinstance(envelope["tests_run"], int)
            or isinstance(envelope["tests_run"], bool) or not isinstance(discovered, list)
            or any(not isinstance(item, str) or not item for item in discovered)
            or any(not isinstance(envelope[field], list) for field in list_fields)
            or any(any(not isinstance(item, str) or not item for item in envelope[field]) for field in list_fields)
            or not isinstance(envelope["started_at"], str) or not isinstance(envelope["completed_at"], str)
            or not isinstance(envelope["result_sha256"], str)):
        raise GovernanceError("TEST_RESULT_INVALID", "Structured unittest result field types are invalid")
    if discovered != binding["expected_ids"] or len(discovered) != len(set(discovered)):
        raise GovernanceError("TEST_RESULT_INVALID", "Discovered unittest IDs do not match the Gate")
    if envelope["tests_run"] != len(discovered) or envelope["tests_run"] <= 0:
        raise GovernanceError("TEST_RESULT_INVALID", "Structured unittest executed count is invalid")
    if any(envelope[field] for field in list_fields) or envelope["successful"] is not True:
        raise GovernanceError("TEST_RESULT_FAILED", "Structured unittest result is not a clean success")
    return envelope


def run_gate_bound_validation(root: Path) -> dict:
    root = root.resolve()
    gate = _active_gate(root)
    config = gate.get("controlled_final_validation")
    if not isinstance(config, dict):
        raise GovernanceError("VALIDATION_ERROR", "Approved Gate lacks controlled_final_validation")
    argv = config.get("argv")
    if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item for item in argv):
        raise GovernanceError("VALIDATION_ERROR", "Gate-bound argv is invalid")
    cwd = Path(config.get("cwd", "")).resolve()
    try:
        cwd.relative_to(root)
    except ValueError as exc:
        raise GovernanceError("SCOPE_VIOLATION", "Controlled validation cwd escapes project") from exc
    timeout = config.get("timeout_seconds")
    if not isinstance(timeout, int) or timeout < 1 or timeout > 180:
        raise GovernanceError("VALIDATION_ERROR", "Controlled validation timeout is invalid")
    subjects = config.get("target_and_test_paths")
    protected = config.get("protected_paths")
    if not isinstance(subjects, list) or not subjects or not isinstance(protected, list) or not protected:
        raise GovernanceError("VALIDATION_ERROR", "Controlled validation subjects are not Gate-bound")
    manifest_relative = config.get("evidence_manifest")
    stdout_relative = config.get("stdout_path")
    stderr_relative = config.get("stderr_path")
    result_relative = config.get("result_manifest")
    if any(not isinstance(item, str) or not item for item in (manifest_relative, stdout_relative, stderr_relative, result_relative)):
        raise GovernanceError("VALIDATION_ERROR", "Controlled validation evidence paths are not Gate-bound")
    evidence_binding = verify_evidence_manifest(root, manifest_relative)
    if config.get("evidence_manifest_sha256") != evidence_binding["manifest_file_sha256"]:
        raise GovernanceError("EVIDENCE_MANIFEST_HASH_MISMATCH", "Gate-bound evidence manifest file hash mismatch")
    environment, environment_hashes = _controlled_environment(config)
    pre_targets = [_fingerprint(root, item) for item in subjects]
    pre_protected = [_fingerprint(root, item, external=True) for item in protected]
    executable = _fingerprint(root, argv[0], external=True)
    test_files = [_fingerprint(root, item, external=True) for item in argv if item.lower().endswith(".py")]
    started = datetime.now().astimezone().isoformat()
    nonce = secrets.token_hex(32)
    envelope = None
    protocol_error = None
    with tempfile.TemporaryDirectory() as protocol_temp:
        envelope_path = Path(protocol_temp) / "unittest-result.json"
        command, protocol_binding = _protocol_command(config, argv, envelope_path, nonce)
        stdout_data, stderr_data, exit_code, timed_out, output_limited = _execute(command, cwd, environment, timeout)
        try:
            envelope = _verify_envelope(envelope_path, nonce, protocol_binding)
        except GovernanceError as exc:
            protocol_error = exc
    completed = datetime.now().astimezone().isoformat()
    post_targets = [_fingerprint(root, item) for item in subjects]
    post_protected = [_fingerprint(root, item, external=True) for item in protected]
    if pre_targets != post_targets or pre_protected != post_protected:
        raise GovernanceError("STALE_FINAL_VALIDATION", "Validation subjects changed during command execution")
    test_count = envelope["tests_run"] if envelope else 0
    success = protocol_error is None and exit_code == 0 and not timed_out and not output_limited
    stdout_path = safe_project_path(root, stdout_relative)
    stderr_path = safe_project_path(root, stderr_relative)
    result_path = safe_project_path(root, result_relative)
    _write_bytes_create_only(stdout_path, stdout_data)
    _write_bytes_create_only(stderr_path, stderr_data)
    result = {
        "schema": "ControlledFinalValidation/v1", "status": "bound" if success else "failed",
        "task_id": gate["task_id"], "gate_id": gate["id"], "started_at": started, "completed_at": completed,
        "exact_command_argv": argv, "cwd": cwd.as_posix(), "environment_sha256": environment_hashes,
        "stdout_sha256": _sha(stdout_data), "stdout_bytes": len(stdout_data),
        "stderr_sha256": _sha(stderr_data), "stderr_bytes": len(stderr_data),
        "exit_code": exit_code, "timed_out": timed_out, "output_limited": output_limited,
        "test_count": test_count, "executable_fingerprint": executable, "test_fingerprints": test_files,
        "test_result_protocol": RESULT_SCHEMA,
        "test_result_envelope_sha256": envelope["result_sha256"] if envelope else None,
        "test_result_error": protocol_error.code if protocol_error else None,
        "discovered_test_ids": envelope["discovered_test_ids"] if envelope else [],
        "target_and_test_pre": pre_targets, "target_and_test_post": post_targets,
        "protected_pre": pre_protected, "protected_post": post_protected,
        "evidence_manifest_binding": evidence_binding,
    }
    write_manifest_create_only(result_path, result)
    if not success:
        raise GovernanceError("FINAL_VALIDATION_FAILED", "Controlled command did not produce a bound success")
    print(f"[ok] CONTROLLED_VALIDATION_COMMAND_ACTUALLY_EXECUTED tests={test_count}")
    return result
