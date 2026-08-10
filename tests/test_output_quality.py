#!/usr/bin/env python3
"""test_output_quality.py — OQA-5D Python Parity 引擎测试（T-0170）"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".zcode/tools"))
from output_quality import run_report  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  OK {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {detail}")


def make_project() -> Path:
    root = Path(tempfile.mkdtemp(prefix="oqa-py-"))
    (root / ".ai/tasks").mkdir(parents=True, exist_ok=True)
    (root / "src").mkdir(exist_ok=True)
    (root / "tests").mkdir(exist_ok=True)
    (root / ".ai/state.yaml").write_text("schema_version: 1\ncurrent_task_id: T-1\ncurrent_phase: S4\n", encoding="utf-8")
    (root / ".ai/tasks/T-1.md").write_text(
        "---\ntask_id: T-1\nallowed_paths:\n  - src/\n  - tests/\n  - .ai/\n---\n# T-1\n## 可验证验收标准\n1. **[AC-01]** works\n2. **[AC-02]** tests pass\n",
        encoding="utf-8")
    return root


def ctx(task="T-1", phase="S4") -> dict:
    return {"task_id": task, "phase": phase, "role": None}


def find(report: dict, cid: str) -> list:
    return [f for d in report["dimensions"] for c in d["checks"] if c["checker_id"] == cid for f in c["findings"]]


def test_rq_01():
    root = make_project()
    (root / "src/a.ts").write_text("export const a = 1;\n", encoding="utf-8")
    r = run_report(root, "src/a.ts", ctx())
    check("RQ-01 inside allowed", not any(f["severity"] == "BLOCKER" for f in find(r, "RQ-01-task-card-binding")))
    (root / "outside").mkdir(exist_ok=True)
    (root / "outside/x.ts").write_text("export const x = 1;\n", encoding="utf-8")
    r2 = run_report(root, "outside/x.ts", ctx())
    check("RQ-01 outside blocked", any(f["severity"] == "BLOCKER" for f in find(r2, "RQ-01-task-card-binding")))
    r3 = run_report(root, "src/a.ts", ctx(task=None))
    check("RQ-01 no task blocked", any(f["severity"] == "BLOCKER" for f in find(r3, "RQ-01-task-card-binding")))


def test_rq_02():
    root = make_project()
    (root / "src/a.ts").write_text("export const a = 1; // [AC-01] [AC-02]\n", encoding="utf-8")
    r = run_report(root, "src/a.ts", ctx())
    check("RQ-02 all referenced", not any(f["severity"] == "WARNING" for f in find(r, "RQ-02-ac-reference")))
    (root / "src/b.ts").write_text("export const b = 1;\n", encoding="utf-8")
    r2 = run_report(root, "src/b.ts", ctx())
    check("RQ-02 unreferenced warning", any(f["severity"] == "WARNING" for f in find(r2, "RQ-02-ac-reference")))


def test_cd_01():
    root = make_project()
    (root / "src/bad.ts").write_text('const k = "sk-0123456789abcdef0123456789abcdef";\n', encoding="utf-8")
    r = run_report(root, "src/bad.ts", ctx())
    check("CD-01 secret blocked", any(f["severity"] == "BLOCKER" for f in find(r, "CD-01-secret-scan")))
    (root / "src/ok.ts").write_text("export const ok = 1;\n", encoding="utf-8")
    r2 = run_report(root, "src/ok.ts", ctx())
    check("CD-01 clean pass", not any(f["severity"] == "BLOCKER" for f in find(r2, "CD-01-secret-scan")))


def test_cd_02():
    root = make_project()
    (root / "src/dbg.ts").write_text("console.log('a');\nconsole.log('b');\nexport const d = 1;\n", encoding="utf-8")
    r = run_report(root, "src/dbg.ts", ctx())
    check("CD-02 debug warning", any(f["severity"] == "WARNING" for f in find(r, "CD-02-debug-residue")))


def test_cd_03():
    root = make_project()
    (root / "src/big.ts").write_text("\n".join(f"// l{i}" for i in range(1300)), encoding="utf-8")
    r = run_report(root, "src/big.ts", ctx())
    check("CD-03 oversized blocked", any(f["severity"] == "BLOCKER" for f in find(r, "CD-03-file-scale")))


def test_ds_01():
    root = make_project()
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs/02-architecture.md").write_text("---\ndesigned_files: [src/declared.ts]\n---\n# Arch\n", encoding="utf-8")
    (root / "src/undeclared.ts").write_text("export const u = 1;\n", encoding="utf-8")
    r = run_report(root, "src/undeclared.ts", ctx())
    check("DS-01 undeclared warning", any(f["severity"] == "WARNING" for f in find(r, "DS-01-architecture-alignment")))


def test_en_01():
    root = make_project()
    (root / "src/only.ts").write_text("export const o = 1;\n", encoding="utf-8")
    r = run_report(root, "src/only.ts", ctx())
    check("EN-01 no test warning", any(f["severity"] == "WARNING" for f in find(r, "EN-01-test-existence")))
    (root / "tests").mkdir(exist_ok=True)
    (root / "tests/pair.test.ts").write_text("import { p } from '../src/pair.js';\n", encoding="utf-8")
    (root / "src/pair.ts").write_text("export const p = 1;\n", encoding="utf-8")
    r2 = run_report(root, ".", ctx())
    check("EN-01 with test pass", not any(f["severity"] == "WARNING" and "src/pair.ts" in f["message"] for f in find(r2, "EN-01-test-existence")))


def test_af_01():
    root = make_project()
    (root / ".ai/evidence/T-1").mkdir(parents=True, exist_ok=True)
    (root / ".ai/evidence/T-1/fake.json").write_text(json.dumps({"content": "real", "content_hash": "f" * 64}), encoding="utf-8")
    r = run_report(root, ".", ctx())
    check("AF-01 fake hash blocked", any(f["severity"] == "BLOCKER" for f in find(r, "AF-01-evidence-authenticity")))


def test_al_01():
    root = make_project()
    (root / "src/todo.ts").write_text("// TODO: implement\nexport const t = 1;\n", encoding="utf-8")
    r = run_report(root, "src/todo.ts", ctx())
    check("AL-01 TODO blocked", any(f["severity"] == "BLOCKER" for f in find(r, "AL-01-placeholder-detection")))
    (root / "src/input.tsx").write_text('export const I = () => <input placeholder="name" />;\n', encoding="utf-8")
    r2 = run_report(root, "src/input.tsx", ctx())
    check("AL-01 JSX placeholder no FP", not any(f["severity"] == "BLOCKER" for f in find(r2, "AL-01-placeholder-detection")))


def test_al_02():
    root = make_project()
    (root / "tests").mkdir(exist_ok=True)
    (root / "tests/empty.test.ts").write_text("import { x } from '../src/x.js';\n", encoding="utf-8")
    r = run_report(root, "tests/empty.test.ts", ctx())
    check("AL-02 zero assertions warning", any(f["severity"] == "WARNING" for f in find(r, "AL-02-test-quality")))
    (root / "tests/ok.test.ts").write_text("import { x } from '../src/x.js';\nexpect(x).toBe(1);\n", encoding="utf-8")
    r2 = run_report(root, "tests/ok.test.ts", ctx())
    check("AL-02 happy-path warning", any(f["severity"] == "WARNING" and "failure-path" in f["message"] for f in find(r2, "AL-02-test-quality")))


def test_ai_02():
    root = make_project()
    r = run_report(root, "src", ctx())
    check("AI-02 empty target drift", any(f["severity"] == "WARNING" for f in find(r, "AI-02-state-artifact-drift")))


def test_integration():
    root = make_project()
    (root / "src/clean.ts").write_text("export const clean = 42; // [AC-01]\n", encoding="utf-8")
    r = run_report(root, "src/clean.ts", ctx())
    check("integration schema", r["schema"] == "output_quality_report/v1")
    check("integration 5 dims", len(r["dimensions"]) == 5)
    check("integration overall not BLOCKED", r["overall"] != "BLOCKED")
    check("integration hash replayable", r["content_hash"] == run_report(root, "src/clean.ts", ctx())["content_hash"])


def main() -> int:
    tests = [test_rq_01, test_rq_02, test_cd_01, test_cd_02, test_cd_03,
             test_ds_01, test_en_01, test_af_01, test_al_01, test_al_02,
             test_ai_02, test_integration]
    for t in tests:
        print(f"[{t.__name__}]")
        t()
    print(f"\nResult: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
