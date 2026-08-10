#!/usr/bin/env python3
"""output_quality.py — OQA-5D Python Parity 引擎（T-0170）

与 Qoder TS 侧 output_quality.ts / authenticity.ts 语义对齐的五维产出质量检查：
  REQUIREMENTS 需求符合性 / CODING 编码规范 / DESIGN 设计理念 /
  ENGINEERING 软件工程 / AUTHENTICITY 真实性（AI 行为验证）

用法：
  python output_quality.py <project_root> <target> [--task-id T-0001] [--phase S4] [--json]
输出：output_quality_report/v1 JSON（与 TS schema 一致）
"""
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

SCHEMA = "output_quality_report/v1"
ENGINE_VERSION = "1.0.0"

CODE_EXTS = {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java", ".c", ".h", ".cpp", ".hpp"}
TEST_PATTERNS = [r"\.(test|spec)\.(ts|tsx|js|jsx)$", r"^test_.*\.py$"]

SECRET_PATTERNS = [
    re.compile(r'(api[_-]?key|apikey|secret|token|password|passwd|pwd)\s*[:=]\s*["\'][A-Za-z0-9_\-]{16,}["\']', re.I),
    re.compile(r"(BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY)"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]
DEBUG_PATTERNS = [
    re.compile(r"\bconsole\.log\s*\("),
    re.compile(r"\bprint\s*\(\s*['\"]?(DEBUG|debug)"),
    re.compile(r"\bdebugger\s*;?"),
    re.compile(r"\bTODO\s*:"),
    re.compile(r"\bFIXME\s*:"),
    re.compile(r"\bHACK\s*:"),
]
PLACEHOLDER_PATTERNS = [
    re.compile(r"\bTODO\s*:"),
    re.compile(r"\bFIXME\s*:"),
    re.compile(r"\bHACK\s*:"),
    re.compile(r"\bNotImplementedError\b"),
    re.compile(r"\bNotImplemented\b"),
    re.compile(r"\bthrow new Error\(['\"]not implemented", re.I),
    re.compile(r"\blorem ipsum\b", re.I),
]
MAGIC_NUMBER_RE = re.compile(r"[=:,(]\s*-?\d{3,}\s*[,;)\]]")

MAX_LINES_WARN = 400
MAX_LINES_BLOCK = 1200
MAX_FILES_WARN = 50


# ── Helpers ─────────────────────────────────────────────────────────────

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def list_files(root: Path, target: str) -> list[str]:
    abs_p = (root / target).resolve()
    if not abs_p.exists():
        return []
    if abs_p.is_file():
        return [str(abs_p.relative_to(root)).replace("\\", "/")]
    return [str(p.relative_to(root)).replace("\\", "/") for p in sorted(abs_p.rglob("*")) if p.is_file()]


def read_maybe(root: Path, rel: str) -> str | None:
    try:
        return (root / rel).read_text(encoding="utf-8")
    except Exception:
        return None


def load_yaml(text: str) -> dict | None:
    if yaml:
        try:
            return yaml.safe_load(text) or {}
        except Exception:
            return None
    return None


def strip_comments(code: str) -> str:
    code = re.sub(r"/\*[\s\S]*?\*/", "", code)
    code = re.sub(r"//[^\n]*", "", code)
    return code


def task_card(root: Path, task_id: str) -> dict | None:
    raw = read_maybe(root, f".ai/tasks/{task_id}.md")
    if not raw:
        return None
    acs = re.findall(r"\[AC-\d+\][^\n]*", raw)
    allowed = []
    fm = re.match(r"^---\n([\s\S]*?)\n---", raw)
    if fm:
        data = load_yaml(fm.group(1))
        if data and isinstance(data.get("allowed_paths"), list):
            allowed = [str(x) for x in data["allowed_paths"]]
    if not allowed:
        m = re.search(r"##\s*允许路径\s*\n([\s\S]*?)(?=\n##\s|\n## Status|$)", raw)
        if m:
            for line in m.group(1).split("\n"):
                t = line.strip().lstrip("-* ").strip()
                # 去掉中文尾注（括号内容）
                t = re.sub(r"[（(].*?[）)]$", "", t).strip()
                if t and not t.startswith("#"):
                    allowed.append(t)
    return {"acs": [a.strip() for a in acs], "allowed_paths": allowed}


def finding(checker_id: str, severity: str, message: str, evidence: str, remediation: str) -> dict:
    return {"checker_id": checker_id, "severity": severity, "message": message,
            "evidence": evidence, "remediation": remediation}


# ── Checkers ───────────────────────────────────────────────────────────

def rq_01(root: Path, files: list[str], ctx: dict, content: dict) -> list[dict]:
    v = []
    task_id = ctx.get("task_id")
    if not task_id:
        return [finding("RQ-01-task-card-binding", "BLOCKER", "No task_id in verify context.",
                        "context.task_id undefined", "Pass task_id from state.yaml.")]
    card = task_card(root, task_id)
    if not card:
        return [finding("RQ-01-task-card-binding", "BLOCKER", f"Task card .ai/tasks/{task_id}.md not found.",
                        f".ai/tasks/{task_id}.md", "Create the task card.")]
    if not card["allowed_paths"]:
        return [finding("RQ-01-task-card-binding", "INFO", "Task card has no allowed_paths — scope check skipped.",
                        f".ai/tasks/{task_id}.md", "Add allowed_paths.")]
    for f in files:
        ok = any(f == ap.rstrip("/") or f.startswith(ap.rstrip("/") + "/") or ap.endswith("*") and f.startswith(ap[:-1])
                 for ap in card["allowed_paths"])
        if not ok:
            v.append(finding("RQ-01-task-card-binding", "BLOCKER",
                             f"Artifact {f} is outside task {task_id} allowed_paths.",
                             f"{f} not in {card['allowed_paths']}", "Move file or amend task card."))
    return v


def rq_02(root: Path, files: list[str], ctx: dict, content: dict) -> list[dict]:
    task_id = ctx.get("task_id")
    if not task_id:
        return []
    card = task_card(root, task_id)
    if not card or not card["acs"]:
        return [finding("RQ-02-ac-reference", "INFO", "No ACs found in task card — coverage check skipped.",
                        f".ai/tasks/{task_id}.md", "Define [AC-xx] criteria.")]
    referenced = 0
    for ac in card["acs"]:
        m = re.search(r"\[(AC-\d+)\]", ac)
        if not m:
            continue
        pat = re.compile(rf"\b{re.escape(m.group(1))}\b")
        if any(pat.search(content.get(f, "")) for f in files):
            referenced += 1
    missing = len(card["acs"]) - referenced
    if missing > 0:
        return [finding("RQ-02-ac-reference", "WARNING",
                        f"{missing}/{len(card['acs'])} ACs not referenced (coverage {round(referenced * 100 / len(card['acs']))}%).",
                        f"ACs referenced: {referenced}/{len(card['acs'])}", "Reference [AC-xx] ids.")]
    return []


def cd_01(_root: Path, files: list[str], _ctx: dict, content: dict) -> list[dict]:
    v = []
    for f in files:
        c = content.get(f, "")
        for i, pat in enumerate(SECRET_PATTERNS):
            m = pat.search(c)
            if m:
                line = c[:m.start()].count("\n") + 1
                v.append(finding("CD-01-secret-scan", "BLOCKER", f"Possible secret in {f}:{line} (pattern {i + 1}).",
                                 f"{f}:{line}", "Move secrets to env/vault."))
                break
    return v


def cd_02(_root: Path, files: list[str], _ctx: dict, content: dict) -> list[dict]:
    v = []
    exempt = ["DEBUG_PATTERNS", "SECRET_PATTERNS", "PLACEHOLDER_PATTERNS", "\\bdebugger", "\\bconsole"]
    for f in files:
        if Path(f).suffix.lower() not in CODE_EXTS:
            continue
        c = content.get(f, "")
        if not c:
            continue
        for i, line in enumerate(c.split("\n")):
            if any(s in line for s in exempt):
                continue
            for pat in DEBUG_PATTERNS:
                if pat.search(line):
                    v.append(finding("CD-02-debug-residue", "WARNING",
                                     f"Debug residue in {f}:{i + 1}: {line.strip()[:40]}",
                                     f"{f}:{i + 1}", "Remove console.log/print/debugger/TODO."))
                    break
    return v


def cd_03(_root: Path, files: list[str], _ctx: dict, content: dict) -> list[dict]:
    v = []
    for f in files:
        if Path(f).suffix.lower() not in CODE_EXTS:
            continue
        c = content.get(f, "")
        if not c:
            continue
        n = c.count("\n") + 1
        if n > MAX_LINES_BLOCK:
            v.append(finding("CD-03-file-scale", "BLOCKER", f"{f} has {n} lines (hard cap {MAX_LINES_BLOCK}).",
                             f"{f}: {n}", "Split the file."))
        elif n > MAX_LINES_WARN:
            v.append(finding("CD-03-file-scale", "WARNING", f"{f} has {n} lines (advisory {MAX_LINES_WARN}).",
                             f"{f}: {n}", "Consider splitting."))
    return v


def ds_01(root: Path, files: list[str], _ctx: dict = None, _content: dict = None) -> list[dict]:
    v = []
    for arch in ["docs/02-architecture.md", ".ai/ARCHITECTURE.md"]:
        raw = read_maybe(root, arch)
        if raw:
            designed = set()
            fm = re.match(r"^---\n([\s\S]*?)\n---", raw)
            if fm:
                data = load_yaml(fm.group(1))
                if data and isinstance(data.get("designed_files"), list):
                    designed = {str(x) for x in data["designed_files"]}
            if not designed:
                designed = set(re.findall(r"^\s*[-*]\s*`([^`]+)`", raw, re.M))
            for f in files:
                if Path(f).suffix.lower() not in CODE_EXTS:
                    continue
                if not any(f == d.rstrip("/") or f.startswith(d.rstrip("/") + "/") or d == "*" for d in designed):
                    v.append(finding("DS-01-architecture-alignment", "WARNING",
                                     f"{f} not declared in designed_files manifest.", f, "Declare in architecture doc."))
            break
    return v


def en_01(_root: Path, files: list[str], _ctx: dict, _content: dict = None) -> list[dict]:
    v = []
    test_files = [f for f in files if any(re.search(p, f) for p in TEST_PATTERNS)]
    for f in files:
        if Path(f).suffix.lower() not in CODE_EXTS or any(re.search(p, f) for p in TEST_PATTERNS):
            continue
        base = Path(f).stem.lower()
        if not any(base in Path(t).stem.lower() for t in test_files):
            v.append(finding("EN-01-test-existence", "WARNING", f"{f} has no corresponding test file.",
                             f"{f}", "Write unit tests."))
    return v


def af_01(root: Path, files: list[str], _ctx: dict = None, _content: dict = None) -> list[dict]:
    v = []
    for f in files:
        if not re.search(r"\.(json|yaml|yml)$", f) or ".ai/evidence" not in f:
            continue
        raw = read_maybe(root, f)
        if not raw:
            continue
        try:
            data = json.loads(raw) if f.endswith(".json") else (load_yaml(raw) or {})
        except Exception:
            continue
        if isinstance(data.get("content"), str) and isinstance(data.get("content_hash"), str):
            if sha256(data["content"]) != data["content_hash"]:
                v.append(finding("AF-01-evidence-authenticity", "BLOCKER",
                                 f"{f} claims content_hash {data['content_hash'][:12]}… but real is {sha256(data['content'])[:12]}….",
                                 f"{f}: hash mismatch", "Recompute evidence."))
        if data.get("exit_code") == 0 and isinstance(data.get("artifacts"), list):
            for a in data["artifacts"]:
                if not (root / a).exists():
                    v.append(finding("AF-01-evidence-authenticity", "BLOCKER",
                                     f"{f} claims artifact {a} but it does not exist.", f"{f}: {a}", "Do not fabricate."))
    return v


def al_01(_root: Path, files: list[str], _ctx: dict, content: dict) -> list[dict]:
    v = []
    exempt = ["PLACEHOLDER_PATTERNS", "TODO_PATTERNS", "AL-01-placeholder"]
    for f in files:
        if Path(f).suffix.lower() not in CODE_EXTS:
            continue
        c = content.get(f, "")
        if not c:
            continue
        for i, line in enumerate(c.split("\n")):
            if any(s in line for s in exempt):
                continue
            for pat in PLACEHOLDER_PATTERNS:
                if pat.search(line):
                    v.append(finding("AL-01-placeholder-detection", "BLOCKER",
                                     f"Placeholder in {f}:{i + 1}: {line.strip()[:40]}",
                                     f"{f}:{i + 1}", "Implement fully."))
                    break
    return v


def al_02(_root: Path, files: list[str], _ctx: dict, content: dict) -> list[dict]:
    v = []
    for f in files:
        if not any(re.search(p, f) for p in TEST_PATTERNS):
            continue
        c = content.get(f, "")
        if not c:
            continue
        code = strip_comments(c)
        assertions = len(re.findall(r"\b(expect|assertEqual|assertIn|assertTrue|assertFalse|assertIs|assertRaises|strictEqual|deepEqual|should|toEqual|toBe|toBeTruthy|ok\()\s*\(", code)) \
            + len(re.findall(r"^\s*assert\s+[^\n]+", code, re.M))
        if assertions == 0:
            v.append(finding("AL-02-test-quality", "WARNING", f"{f} has 0 assertions.",
                             f"{f}", "Add assertions."))
        elif not re.search(r"(throws?|reject|error|invalid|empty|not found|edge|boundary|fail|negative)", code, re.I):
            v.append(finding("AL-02-test-quality", "WARNING",
                             f"{f} has {assertions} assertion(s) but no failure-path cases.",
                             f"{f}: happy-path only", "Add failure-path tests."))
    return v


def ai_02(root: Path, files: list[str], ctx: dict, _content: dict = None) -> list[dict]:
    task_id = ctx.get("task_id")
    if not task_id:
        return []
    state_raw = read_maybe(root, ".ai/state.yaml")
    if not state_raw:
        return []
    data = load_yaml(state_raw) or {}
    if data.get("current_task_id") == task_id and not files:
        return [finding("AI-02-state-artifact-drift", "WARNING",
                        f"state.yaml claims task {task_id} active but target contains no artifacts.",
                        f"{ctx.get('target', '?')}: 0 files", "Produce artifacts.")]
    return []


# ── Engine ──────────────────────────────────────────────────────────────

CHECKERS = [
    ("REQUIREMENTS", "需求符合性", [rq_01, rq_02]),
    ("CODING", "编码规范", [cd_01, cd_02, cd_03]),
    ("DESIGN", "设计理念", [ds_01]),
    ("ENGINEERING", "软件工程", [en_01]),
    ("AUTHENTICITY", "真实性（AI 行为验证）", [af_01, al_01, al_02, ai_02]),
]


def run_report(root: Path, target: str, ctx: dict) -> dict:
    files = list_files(root, target)
    content = {f: read_maybe(root, f) or "" for f in files}
    hash_input = "".join(f + "\n" + content[f] + "\n" for f in files)
    dims = []
    blocked_by = []
    total_b = total_w = 0
    for dim, label, checkers in CHECKERS:
        checks = []
        for fn in checkers:
            findings_list = fn(root, files, ctx, content)
            checks.append({"checker_id": findings_list[0]["checker_id"] if findings_list else f"{dim}-check",
                           "dimension": dim, "passed": not any(f["severity"] == "BLOCKER" for f in findings_list),
                           "findings": findings_list, "duration_ms": 0})
        blockers = [f for c in checks for f in c["findings"] if f["severity"] == "BLOCKER"]
        warnings = [f for c in checks for f in c["findings"] if f["severity"] == "WARNING"]
        total_b += len(blockers)
        total_w += len(warnings)
        status = "BLOCKED" if blockers else ("WARNING" if warnings else "PASS")
        if blockers:
            blocked_by.append(f"{dim}({len(blockers)})")
        dims.append({"dimension": dim, "label": label, "checks": checks,
                     "blocker_count": len(blockers), "warning_count": len(warnings), "status": status})
    return {
        "schema": SCHEMA, "project_root": str(root), "target": target,
        "target_kind": "directory" if len(files) > 1 else ("file" if files else "virtual"),
        "content_hash": sha256(hash_input), "context": ctx, "dimensions": dims,
        "overall": "BLOCKED" if total_b else ("WARNING" if total_w else "PASS"),
        "blocked_by": blocked_by, "generated_at": __import__("datetime").datetime.now().isoformat(),
        "engine_version": ENGINE_VERSION,
    }


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: output_quality.py <project_root> <target> [--task-id T-x] [--phase Sx] [--json]", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    target = sys.argv[2]
    ctx = {"task_id": None, "phase": None, "role": None}
    if "--task-id" in sys.argv:
        ctx["task_id"] = sys.argv[sys.argv.index("--task-id") + 1]
    if "--phase" in sys.argv:
        ctx["phase"] = sys.argv[sys.argv.index("--phase") + 1]
    ctx["target"] = target
    report = run_report(root, target, ctx)
    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Output Quality Report (OQA-5D {ENGINE_VERSION})")
        print(f"Target: {target}  Overall: {report['overall']}" + (f"  blocked_by: {report['blocked_by']}" if report["blocked_by"] else ""))
        for d in report["dimensions"]:
            icon = "✓" if d["status"] == "PASS" else ("⚠" if d["status"] == "WARNING" else "✗")
            print(f"  {icon} {d['dimension']} {d['label']}: {d['status']} ({d['blocker_count']}b/{d['warning_count']}w)")
            for c in d["checks"]:
                for f in c["findings"]:
                    if f["severity"] != "INFO":
                        print(f"      [{f['severity']}] {f['checker_id']}: {f['message'][:80]}")
    return 0 if report["overall"] != "BLOCKED" else 1


if __name__ == "__main__":
    sys.exit(main())
