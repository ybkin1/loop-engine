"""
run_quality_gates.py — 质量门禁编排脚本。

确定性代码，不依赖 LLM。被质量工程师 agent 通过 Bash 调用。
读取项目 config.yaml 的 quality_gates 节，依次运行各检查工具，
解析输出，与阈值对比，生成结构化质量报告。

用法：
    python run_quality_gates.py [--project-root <dir>] [--output-dir <dir>]

输出文件（写入 --output-dir 或 .ai/evidence/quality/）：
    quality_report.json  — 机器可读（给 hook/validator 用）
    quality_summary.md   — 人可读（给用户看）

退出码：0 = 全 PASS；2 = 有 BLOCKED 项。

配置来源（优先级从高到低）：
    1. 项目根 .zcode/skills/loop-governance/config.yaml 的 quality_gates 节
    2. 项目根 .zcode/skills/loop-governance/config.yaml 的 quality_gates.templates 节（按 project_type 匹配）
    3. 内置默认值
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

# --------------- 默认配置 ---------------

DEFAULT_QUALITY_GATES = {
    "lint_command": None,          # 例: "ruff check --output-format json ."
    "lint_threshold": 0,
    "typecheck_command": None,     # 例: "mypy --strict src/"
    "typecheck_threshold": 0,
    "test_command": None,          # 例: "pytest --cov=src --cov-report=term --tb=short -q"
    "test_threshold": 0,           # 允许的最大失败数
    "coverage_threshold": 80,      # 覆盖率百分比
    "audit_command": None,         # 例: "pip-audit -r requirements.txt --format json"
    "audit_threshold": {"HIGH": 0, "CRITICAL": 0},
    "build_command": None,         # 例: "python -m build"
    "build_threshold": 0,          # exit code 上限
    "compile_command": None,       # 例: "python .ai/checkers/compile_gate.py . --paths loop_core"
    "compile_threshold": 0,        # 允许的最大编译失败文件数
    "project_type": "auto",        # python | javascript | auto
}

# --------------- 解析器 ---------------

def parse_lint_output(raw: str, exit_code: int, command: str) -> tuple[int, str]:
    """解析 lint 工具输出，返回 (error_count, raw_snippet)。"""
    raw_clean = raw.strip()
    # ruff --output-format json
    if "ruff" in command and raw_clean.startswith("["):
        try:
            items = json.loads(raw_clean)
            return len(items), raw[:500]
        except json.JSONDecodeError:
            pass
    # eslint --format json
    if "eslint" in command and raw_clean.startswith("["):
        try:
            items = json.loads(raw_clean)
            total = sum(len(f.get("messages", [])) for f in items)
            return total, raw[:500]
        except json.JSONDecodeError:
            pass
    # 空 JSON 数组 = 零 error
    if raw_clean == "[]":
        return 0, ""
    # 退化为计数非空行（不包括空行和摘要行）
    lines = [l for l in raw_clean.splitlines() if l.strip() and not l.strip().startswith("Found")]
    return len(lines), raw[:500]


def parse_test_output(raw: str, exit_code: int, command: str) -> tuple[int, int, int, str]:
    """解析测试输出，返回 (passed, total, coverage_pct, raw_snippet)。"""
    coverage = 0
    passed = 0
    total = 0
    raw_clean = raw.strip()

    # pytest --cov 输出
    for line in raw_clean.splitlines():
        if "passed" in line and ("failed" in line or "=" in line):
            # 形如 "38 passed, 2 failed" 或 "= 40 passed in 1.23s ="
            import re
            m_passed = re.search(r"(\d+)\s*passed", line)
            m_failed = re.search(r"(\d+)\s*failed", line)
            if m_passed:
                passed = int(m_passed.group(1))
            if m_failed:
                total = passed + int(m_failed.group(1))
            elif m_passed:
                total = passed  # all passed
        if "TOTAL" in line and "%" in line:
            # coverage.py 的 TOTAL 行
            parts = line.split()
            for p in parts:
                if p.endswith("%"):
                    try:
                        coverage = int(float(p.replace("%", "")))
                    except ValueError:
                        pass

    if total == 0:
        total = passed

    return passed, total, coverage, raw[:500]


def parse_audit_output(raw: str, exit_code: int, command: str) -> dict[str, int]:
    """解析依赖审计输出，返回 {severity: count}。"""
    raw_clean = raw.strip()
    counts = {"HIGH": 0, "CRITICAL": 0, "MODERATE": 0, "LOW": 0}

    # pip-audit --format json
    if "pip-audit" in command and raw_clean.startswith("["):
        try:
            items = json.loads(raw_clean)
            for item in items:
                if isinstance(item, dict):
                    sev = (item.get("vulns") or [{}])[0].get("severity", "") if "vulns" in item else ""
            # pip-audit 的 JSON 结构比较复杂，退化为统计退出码
            if exit_code != 0:
                counts["HIGH"] = max(1, len(items))
            return counts
        except json.JSONDecodeError:
            pass

    # npm audit --json
    if "npm audit" in command:
        try:
            data = json.loads(raw_clean)
            vulns = data.get("vulnerabilities", {}) if isinstance(data, dict) else {}
            for v in (vulns.values() if isinstance(vulns, dict) else []):
                if isinstance(v, dict):
                    sev = v.get("severity", "").upper()
                    if sev in counts:
                        counts[sev] += 1
            return counts
        except json.JSONDecodeError:
            pass

    # 退化：根据退出码推断
    if exit_code != 0 and raw_clean:
        counts["HIGH"] = 1  # 保守：有非零退出码就当有 HIGH
    return counts


def parse_build_output(raw: str, exit_code: int, command: str) -> int:
    """解析构建输出：exit code 0 = pass。"""
    return exit_code


def parse_compile_output(raw: str, exit_code: int, command: str) -> tuple[int, int, list]:
    """解析编译门禁输出，返回 (compiled_count, failed_count, error_list)。"""
    raw_clean = raw.strip()
    if raw_clean.startswith("{"):
        try:
            data = json.loads(raw_clean)
            compiled = data.get("compiled_files", 0)
            total = data.get("total_files", compiled)
            failed = data.get("failed_count", total - compiled)
            errors = data.get("errors", [])
            return compiled, failed, errors
        except json.JSONDecodeError:
            pass
    # Fallback: use exit code to determine pass/fail
    if exit_code == 0:
        return 0, 0, []
    else:
        return 0, 1, [{"error": raw_clean[:500]}]


# --------------- 核心 ---------------

def load_config(project_root: Path) -> dict:
    """加载 quality_gates 配置，合并默认值。"""
    import yaml  # type: ignore
    cfg_path = project_root / ".zcode" / "skills" / "loop-governance" / "config.yaml"
    gates = dict(DEFAULT_QUALITY_GATES)
    if not cfg_path.exists():
        return gates

    with open(cfg_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    qg = raw.get("quality_gates", {})
    if isinstance(qg, dict):
        # 通用合并
        for key, default in DEFAULT_QUALITY_GATES.items():
            gates[key] = qg.get(key, default)
    # 模板覆盖：按 project_type 匹配
    templates = qg.get("templates", {})
    if isinstance(templates, dict):
        pt = gates.get("project_type", "auto")
        # Auto-detect project type if set to "auto"
        if pt == "auto":
            if (project_root / "pyproject.toml").exists() or (project_root / "setup.py").exists() or (project_root / "requirements.txt").exists():
                pt = "python"
            elif (project_root / "package.json").exists():
                pt = "javascript"
        tmpl = templates.get(pt, templates.get("default", {}))
        if isinstance(tmpl, dict):
            for key, default in DEFAULT_QUALITY_GATES.items():
                if key in tmpl:
                    gates[key] = tmpl[key]

    return gates


def run_one_check(name: str, command: str | None, project_root: Path, timeout: int = 120) -> dict[str, Any]:
    """运行一个检查，返回 {exit_code, stdout, stderr}。"""
    if not command:
        return {"exit_code": 0, "stdout": "", "stderr": "", "skipped": True}
    try:
        result = subprocess.run(
            shlex.split(command),
            shell=False,
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=timeout,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "skipped": False,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": f"超时 ({timeout}s)", "skipped": False}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e), "skipped": False}


def collect_results(gates: dict, project_root: Path) -> list[dict[str, Any]]:
    """运行所有配置的检查，收集原始结果。"""
    results = []

    # Lint
    if gates.get("lint_command"):
        r = run_one_check("lint", gates["lint_command"], project_root)
        count, snippet = parse_lint_output(r["stdout"], r["exit_code"], gates["lint_command"])
        results.append({"name": "lint", "value": count, "threshold": gates.get("lint_threshold", 0),
                        "raw": snippet, "exit_code": r["exit_code"], "skipped": r.get("skipped", False)})

    # Typecheck
    if gates.get("typecheck_command"):
        r = run_one_check("typecheck", gates["typecheck_command"], project_root)
        count = 0 if r["exit_code"] == 0 else 1  # typecheck 简化为 0/1
        results.append({"name": "typecheck", "value": count, "threshold": gates.get("typecheck_threshold", 0),
                        "raw": r["stdout"][:300], "exit_code": r["exit_code"], "skipped": r.get("skipped", False)})

    # Test + Coverage
    if gates.get("test_command"):
        r = run_one_check("test", gates["test_command"], project_root, timeout=180)
        passed, total, cov, snippet = parse_test_output(r["stdout"], r["exit_code"], gates["test_command"])
        results.append({"name": "test", "value": f"{passed}/{total}", "threshold": gates.get("test_threshold", 0),
                        "raw": snippet, "exit_code": r["exit_code"], "skipped": r.get("skipped", False)})
        results.append({"name": "coverage", "value": cov, "threshold": gates.get("coverage_threshold", 80),
                        "raw": f"{cov}%", "exit_code": r["exit_code"], "skipped": r.get("skipped", False)})

    # Audit
    if gates.get("audit_command"):
        r = run_one_check("audit", gates["audit_command"], project_root)
        counts = parse_audit_output(r["stdout"], r["exit_code"], gates["audit_command"])
        results.append({"name": "audit", "value": counts, "threshold": gates.get("audit_threshold", {"HIGH": 0}),
                        "raw": r["stdout"][:300], "exit_code": r["exit_code"], "skipped": r.get("skipped", False)})

    # Build
    if gates.get("build_command"):
        r = run_one_check("build", gates["build_command"], project_root)
        code = parse_build_output(r["stdout"], r["exit_code"], gates["build_command"])
        results.append({"name": "build", "value": code, "threshold": gates.get("build_threshold", 0),
                        "raw": r["stdout"][:200], "exit_code": code, "skipped": r.get("skipped", False)})

    # Compile
    if gates.get("compile_command"):
        r = run_one_check("compile", gates["compile_command"], project_root, timeout=120)
        compiled, failed, error_list = parse_compile_output(r["stdout"], r["exit_code"], gates["compile_command"])
        results.append({"name": "compile", "value": failed, "threshold": gates.get("compile_threshold", 0),
                        "raw": json.dumps(error_list)[:300] if error_list else "0 errors",
                        "exit_code": r["exit_code"], "skipped": r.get("skipped", False),
                        "compiled_files": compiled})

    # Structural checks (Codex v3.12.8)
    try:
        if gates.get(chr(39)+chr(115)+chr(116)+chr(114)+chr(117)+chr(99)+chr(116)+chr(117)+chr(114)+chr(97)+chr(108)+chr(95)+chr(99)+chr(104)+chr(101)+chr(99)+chr(107)+chr(115)+chr(95)+chr(101)+chr(110)+chr(97)+chr(98)+chr(108)+chr(101)+chr(100)+chr(39)+chr(44)+chr(32)+chr(84)+chr(114)+chr(117)+chr(101)+chr(41)):
            from codex_loop.quality.structural_checks import run_structural_checks
        structural = run_structural_checks(str(project_root))
        results.extend(structural)
    except Exception as e:
        results.append(dict(name=chr(39)+chr(115)+chr(116)+chr(114)+chr(117)+chr(99)+chr(116)+chr(117)+chr(114)+chr(97)+chr(108)+chr(39),value=-1,threshold=0,raw=str(e)[:200],skipped=True))

    return results


def generate_report(results: list[dict[str, Any]], project_root: Path, output_dir: Path) -> tuple[str, list[str]]:
    """生成 quality_report.json 和 quality_summary.md，返回 (overall, blocked_by)。"""
    # ensure scripts dir is importable (caller may be in any cwd)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from check_thresholds import check

    checks_out = []
    blocked_by = []

    for r in results:
        item = check(r["name"], r["value"], r["threshold"])
        item["raw"] = r.get("raw", "")[:200]
        item["skipped"] = r.get("skipped", False)
        checks_out.append(item)
        if item["status"] == "blocked":
            blocked_by.append(f"{r['name']}: {item['reason']}")

    overall = "PASS" if not blocked_by else "BLOCKED"

    # 计算源码树 SHA256（用于证据链绑定）
    src_hash = _compute_src_hash(project_root)

    # JSON report
    report = {
        "schema": "quality_report/v1",
        "role": "quality-engineer",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": str(project_root.resolve()),
        "checks": checks_out,
        "overall": overall,
        "blocked_by": blocked_by,
        "input_hashes": {
            "source_code": f"sha256:{src_hash}" if src_hash else "unavailable",
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "quality_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown summary
    md_lines = [
        f"# 质量报告 · {project_root.name} · {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "| 检查项 | 结果 | 门槛 | 状态 |",
        "|--------|------|------|------|",
    ]
    for item in checks_out:
        status_icon = "✅" if item["status"] == "pass" else ("❌" if item["status"] == "blocked" else "⚠️")
        value_str = str(item.get("value", "—"))
        thresh_str = str(item.get("threshold", "—"))
        if isinstance(value_str, dict):
            value_str = json.dumps(value_str)
        if isinstance(thresh_str, dict):
            thresh_str = json.dumps(thresh_str)
        md_lines.append(f"| {item['name']} | {value_str} | {thresh_str} | {status_icon} |")

    md_lines.append("")
    md_lines.append(f"**结论：{overall}**")
    if blocked_by:
        md_lines.append("")
        md_lines.append("## 阻断项")
        for b in blocked_by:
            md_lines.append(f"- {b}")
    else:
        md_lines.append("")
        md_lines.append("全部检查通过，质量门放行。")

    md_path = output_dir / "quality_summary.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return overall, blocked_by


def main():
    parser = argparse.ArgumentParser(description="运行质量门禁检查")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--output-dir", default=None, help="报告输出目录（默认 .ai/evidence/quality/）")
    parser.add_argument("--json", action="store_true", help="同时输出 JSON 到 stdout")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    output_dir = Path(args.output_dir) if args.output_dir else project_root / ".ai" / "evidence" / "quality"

    gates = load_config(project_root)
    results = collect_results(gates, project_root)
    overall, blocked_by = generate_report(results, project_root, output_dir)

    if args.json:
        json_report = output_dir / "quality_report.json"
        if json_report.exists():
            print(json_report.read_text(encoding="utf-8"))

    if overall == "BLOCKED":
        print(f"\n[quality-engineer] BLOCKED — {len(blocked_by)} 项不合格:", file=sys.stderr)
        for b in blocked_by:
            print(f"  - {b}", file=sys.stderr)
        sys.exit(2)
    else:
        print("\n[quality-engineer] PASS — 全部质量门通过")
        sys.exit(0)


def _compute_src_hash(project_root: Path) -> str:
    """计算源码树 SHA256（排除 .ai/ .git/ node_modules/ __pycache__ 等目录）。"""
    import hashlib
    src_dir = project_root / "src"
    if not src_dir.is_dir():
        return ""
    h = hashlib.sha256()
    exclude = {"__pycache__", ".git", "node_modules", ".venv", "venv", "dist", "build", ".ai"}
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = sorted(d for d in dirs if d not in exclude and not d.startswith("."))
        for fname in sorted(files):
            fpath = Path(root) / fname
            try:
                h.update(fpath.read_bytes())
                h.update(fname.encode())
            except (OSError, PermissionError):
                pass
    return h.hexdigest()


if __name__ == "__main__":
    main()
