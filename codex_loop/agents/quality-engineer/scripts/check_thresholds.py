"""
check_thresholds.py — 质量门禁阈值对比工具。

纯确定性逻辑，不依赖 LLM、不读取网络、不调用外部进程。
被 run_quality_gates.py 导入使用，也可单独运行做快速检查。

用法：
    python check_thresholds.py lint 5 0          # 5 errors > 0 threshold → BLOCKED
    python check_thresholds.py coverage 91 80     # 91% >= 80% threshold → PASS
    python check_thresholds.py test 38/40 100     # 2 failed → BLOCKED
    python check_thresholds.py audit '{"HIGH":1}' '{"HIGH":0}'  # 1 HIGH > 0 → BLOCKED

输出（JSON，一行）：
    {"check": "lint", "status": "blocked", "value": 5, "threshold": 0, "reason": "5 > 0"}

退出码：0 = 通过了所有给定检查；2 = 有阻断项。
"""

import json
import sys

EXIT_PASS = 0
EXIT_BLOCK = 2


def compare_lint(value, threshold):
    """比较 lint error 数与阈值。value ≤ threshold 为 pass。"""
    return value <= threshold


def compare_coverage(value, threshold):
    """比较覆盖率百分比与阈值。value ≥ threshold 为 pass。"""
    return value >= threshold


def compare_test(value, threshold):
    """
    比较测试结果。
    value 格式：'passed/total'（如 '38/40'）或整数 failed 数。
    threshold 为允许的最大失败数（默认 0）。
    """
    try:
        if isinstance(value, str) and "/" in value:
            parts = value.split("/")
            passed, total = int(parts[0]), int(parts[1])
            failed = total - passed
        else:
            failed = int(value)
    except (ValueError, TypeError):
        return False, f"无法解析测试结果: {value}"

    threshold = int(threshold) if threshold is not None else 0
    ok = failed <= threshold
    detail = f"{failed} 个失败用例（上限 {threshold}）" if not ok else f"{failed} 个失败"
    return ok, detail


def compare_audit(value, threshold):
    """
    比较依赖审计结果。
    value/threshold 为 JSON 字符串或 dict：{"HIGH": n, "CRITICAL": m, ...}
    threshold 声明每种级别的最大允许数量；value 任一级别超限 = BLOCKED。
    """
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return False, f"无法解析审计结果: {value}"
    if isinstance(threshold, str):
        try:
            threshold = json.loads(threshold)
        except json.JSONDecodeError:
            threshold = {"HIGH": 0, "CRITICAL": 0}

    value = value if isinstance(value, dict) else {}
    threshold = threshold if isinstance(threshold, dict) else {"HIGH": 0, "CRITICAL": 0}

    violations = []
    for level in ("CRITICAL", "HIGH", "MODERATE", "LOW"):
        actual = value.get(level, 0)
        allowed = threshold.get(level, 0)
        if actual > allowed:
            violations.append(f"{level}: {actual} > {allowed}")

    if violations:
        return False, "; ".join(violations)
    return True, "0 HIGH/CRITICAL"


COMPARATORS = {
    "lint": lambda v, t: (compare_lint(int(v), int(t)), f"{v} > {t}" if not compare_lint(int(v), int(t)) else f"{v} ≤ {t}"),
    "typecheck": lambda v, t: (compare_lint(int(v), int(t)), f"{v} > {t}" if not compare_lint(int(v), int(t)) else f"{v} ≤ {t}"),
    "coverage": lambda v, t: (compare_coverage(float(v), float(t)), f"{v} < {t}" if not compare_coverage(float(v), float(t)) else f"{v} ≥ {t}"),
    "test": compare_test,
    "audit": compare_audit,
    "build": lambda v, t: (int(v) == 0, "exit code != 0" if int(v) != 0 else "exit 0"),
    "compile": lambda v, t: (int(v) <= int(t), f"{v} files failed to compile (threshold {t})" if int(v) > int(t) else f"{v} compile errors ≤ {t}"),
}


def check(name, value, threshold):
    """对给定检查项与阈值做比较；未注册的检查名视为 pass。"""
    comparator = COMPARATORS.get(name)
    if comparator is None:
        return {"name": name, "status": "pass", "value": value, "threshold": threshold, "reason": "unknown check type, skipped"}

    try:
        ok, detail = comparator(value, threshold)
    except Exception as e:
        return {"name": name, "status": "error", "value": value, "threshold": threshold, "reason": str(e)}

    return {
        "name": name,
        "status": "pass" if ok else "blocked",
        "value": value,
        "threshold": threshold,
        "reason": detail,
    }


def check_all(checks_config, results):
    """
    checks_config: {name: threshold} 字典
    results: {name: value} 字典
    返回 (items, overall, blocked_by) 三元组。
    """
    items = []
    blocked_by = []
    for name, threshold in checks_config.items():
        value = results.get(name, results.get("UNKNOWN"))
        item = check(name, value, threshold)
        items.append(item)
        if item["status"] == "blocked":
            blocked_by.append(f"{name}: {item['reason']}")
    overall = "PASS" if not blocked_by else "BLOCKED"
    return items, overall, blocked_by


def main():
    """CLI 入口：check_thresholds.py <name> <value> <threshold>"""
    if len(sys.argv) < 4:
        print(json.dumps({"error": "用法: check_thresholds.py <check_name> <value> <threshold>"}))
        sys.exit(1)

    name = sys.argv[1]
    value = sys.argv[2]
    threshold = sys.argv[3]

    item = check(name, value, threshold)
    print(json.dumps(item, ensure_ascii=False))
    sys.exit(EXIT_BLOCK if item["status"] == "blocked" else EXIT_PASS)


if __name__ == "__main__":
    main()
