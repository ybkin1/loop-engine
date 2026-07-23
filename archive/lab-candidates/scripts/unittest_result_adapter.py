from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path


SCHEMA = "UnittestResultEnvelope/v1"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _fingerprint(path: Path) -> dict:
    path = path.resolve()
    stat = path.stat()
    return {
        "path": path.as_posix(), "sha256": _sha(path.read_bytes()),
        "size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
    }


def _test_ids(suite: unittest.TestSuite) -> list[str]:
    result = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            result.extend(_test_ids(item))
        else:
            result.append(item.id())
    return result


def _write_create_only(path: Path, value: dict) -> None:
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _load_suite(test_path: Path) -> unittest.TestSuite:
    module_name = test_path.stem
    spec = importlib.util.spec_from_file_location(module_name, test_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load test module: {test_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return unittest.defaultTestLoader.loadTestsFromModule(module)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("test_path")
    parser.add_argument("--result-envelope", required=True)
    parser.add_argument("--run-nonce", required=True)
    args = parser.parse_args()
    test_path = Path(args.test_path).resolve()
    started = datetime.now().astimezone().isoformat()
    suite = _load_suite(test_path)
    discovered = _test_ids(suite)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    envelope = {
        "schema": SCHEMA,
        "run_nonce": args.run_nonce,
        "adapter_fingerprint": _fingerprint(Path(__file__)),
        "test_fingerprints": [_fingerprint(test_path)],
        "discovered_test_ids": discovered,
        "tests_run": result.testsRun,
        "failures": [test.id() for test, _ in result.failures + result.expectedFailures],
        "errors": [test.id() for test, _ in result.errors],
        "skipped": [test.id() for test, _ in result.skipped],
        "unexpected_successes": [test.id() for test in result.unexpectedSuccesses],
        "successful": result.wasSuccessful() and not result.expectedFailures,
        "started_at": started,
        "completed_at": datetime.now().astimezone().isoformat(),
    }
    canonical = json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    envelope["result_sha256"] = _sha(canonical)
    _write_create_only(Path(args.result_envelope).resolve(), envelope)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
