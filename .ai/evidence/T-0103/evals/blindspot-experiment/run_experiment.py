#!/usr/bin/env python3
r"""run_experiment.py — 盲点实验 EvalRunner 评分 + 聚合统计

D-04 §6 步骤 4/5：100% 复用现有 eval 栈（load_cases → EvalRunner → EvalReport），
对 10 份实验产出 + 2 份校准样例跑规则断言评分，输出：
  - eval-report.json   （EvalReport，ReportBinding: task_id=T-0103）
  - scores.csv         （逐产出 4 维度得分表）
  - 聚合统计           （Mann-Whitney U 精确检验 / Fisher 精确检验 / Cohen's d）

本实验使用 D-04 降级路径（规则式模拟/构造性评估）：产出为构造样本，
评分 100% 走 EvalRunner 规则断言；无 LLM 外部调用（llm judge 不启用）。

用法: C:/Python312/python.exe run_experiment.py
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))  # 项目根

from loop_core.evals import (  # noqa: E402
    EvalReport,
    EvalRunner,
    load_cases,
)

HERE = Path(__file__).resolve().parent
CASES = HERE / "cases" / "cases-blindspot.yaml"
REPORT = HERE / "eval-report.json"
SCORES = HERE / "scores.csv"

GROUP_OUTPUTS = [
    ("A", "S1"), ("A", "S2"), ("A", "S4"), ("A", "S5"), ("A", "S6"),
    ("B", "S1"), ("B", "S2"), ("B", "S4"), ("B", "S5"), ("B", "S6"),
]
CALIB = [("calib-high", "S1"), ("calib-low", "S1")]

CONFIRM_PATTERN = re.compile(r"\| 是 \|")


# ── 统计工具（纯 Python，无 scipy 依赖） ────────────────────────────────

def _ranks(values: list[float]) -> list[float]:
    """返回每个值的 mid-rank（并列取平均）。"""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while (j + 1 < len(order)
               and values[order[j + 1]] == values[order[i]]):
            j += 1
        mid = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = mid
        i = j + 1
    return ranks


def _mw_exact_p(n1: int, n2: int, u: int) -> float:
    """Mann-Whitney U 双尾精确 p（穷举组合计数，适用于小样本）。"""
    from functools import lru_cache

    @lru_cache(maxsize=None)
    def count(a: int, b: int, uu: int) -> int:
        if uu < 0:
            return 0
        if a == 0 or b == 0:
            return 1
        return count(a - 1, b, uu - b) + count(a, b - 1, uu)

    total = math.comb(n1 + n2, n1)
    p_one = count(n1, n2, u) / total
    return min(1.0, 2 * p_one)


def mann_whitney(x: list[float], y: list[float]) -> dict:
    """U1（x 组）、U2（y 组）、双尾精确 p、效应量 r。"""
    n1, n2 = len(x), len(y)
    ranks = _ranks(x + y)
    r1 = sum(ranks[:n1])
    u1 = r1 - n1 * (n1 + 1) / 2
    u2 = n1 * n2 - u1
    p = _mw_exact_p(n1, n2, int(round(min(u1, u2))))
    return {"U1": u1, "U2": u2, "p_exact_twosided": p,
            "n1": n1, "n2": n2}


def cohens_d(x: list[float], y: list[float]) -> float:
    """pooled Cohen's d（x 组相对 y 组）。"""
    mx, my = sum(x) / len(x), sum(y) / len(y)
    vx = sum((v - mx) ** 2 for v in x) / (len(x) - 1) if len(x) > 1 else 0.0
    vy = sum((v - my) ** 2 for v in y) / (len(y) - 1) if len(y) > 1 else 0.0
    sp = math.sqrt(((len(x) - 1) * vx + (len(y) - 1) * vy) / (len(x) + len(y) - 2))
    if sp == 0:
        return float("inf") if mx != my else 0.0
    return (mx - my) / sp


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """2x2 Fisher 精确检验双尾 p：[[a,b],[c,d]]。"""
    total = math.comb(a + b, a) * math.comb(c + d, c) / math.comb(a + b + c + d, a + c)
    p0 = total
    # 枚举所有更极端的表
    rows, cols = [a + b, c + d], [a + c, b + d]
    p = 0.0
    for x in range(0, min(rows[0], cols[0]) + 1):
        y = cols[0] - x
        if y < 0 or y > rows[1]:
            continue
        w = math.comb(rows[0], x) * math.comb(rows[1], y) / math.comb(rows[0] + rows[1], cols[0])
        if w <= p0 * (1 + 1e-12):
            p += w
    return min(1.0, p)


# ── 聚合 ────────────────────────────────────────────────────────────────

def main() -> int:
    cases = load_cases(CASES)
    runner = EvalRunner(cases, suite_id="loop-blindspot-experiment",
                        suite_version="1")
    run = runner.run()
    report = EvalReport(run, task_id="T-0103", phase="S6-delivery",
                        gate_id="G-T-0103-EVAL-BLINDSPOT",
                        git_commit_sha=None)
    report.write(REPORT)
    print(f"report written: {REPORT}")

    by_case = {r.case_id: r for r in run.results}
    out_prefix = {g: f"{g}-{s}-1.md" for g, s in GROUP_OUTPUTS}
    calib_prefix = {g: f"calibration/{g}.md" for g, _ in CALIB}

    def output_metrics(fname: str, group: str, sc: str) -> dict:
        text = (HERE / "outputs" / fname).read_text(encoding="utf-8")
        tag = f"group:{group}"
        seed_ids = [c.case_id for c in cases
                    if tag in c.tags and f"scenario:{sc}" in c.tags
                    and "dimension:D3" in c.tags and "-D3-seed-" in c.case_id]
        hits = sum(1 for cid in seed_ids if by_case[cid].verdict.value == "PASS")
        missed = len(seed_ids) - hits
        d2 = by_case[f"{sc}-{group}-D2-conseq"].verdict.value == "PASS"
        d4n = len(CONFIRM_PATTERN.findall(text))
        d4_ok = 1 <= d4n <= 3
        d1_struct = by_case[f"{sc}-{group}-D1-struct"].verdict.value == "PASS"
        return {
            "output": fname, "group": group, "scenario": sc,
            "D1_hits": hits, "D1_ge3": d1_struct and hits >= 3,
            "D2_conseq": d2, "D3_missed": missed,
            "D4_confirm_count": d4n, "D4_in_range": d4_ok,
            "chars": len(text),
        }

    rows = [output_metrics(f"{g}-{s}-1.md", g, s) for g, s in GROUP_OUTPUTS]
    calib_rows = [output_metrics(f"calibration/{g}.md", g, s) for g, s in CALIB]

    with open(SCORES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
        for r in calib_rows:
            w.writerow(r)
    print(f"scores written: {SCORES}")

    # ── 校准验证（规则区分度） ──
    hi, lo = calib_rows[0], calib_rows[1]
    calib_ok = (hi["D1_hits"] == 5 and hi["D2_conseq"] and hi["D4_in_range"]
                and lo["D1_hits"] == 0 and not lo["D2_conseq"]
                and lo["D4_confirm_count"] == 0)
    print(f"calibration: high={hi['D1_hits']}hits/D2={hi['D2_conseq']}/"
          f"D4={hi['D4_confirm_count']} low={lo['D1_hits']}hits/D2={lo['D2_conseq']}/"
          f"D4={lo['D4_confirm_count']} -> {'OK' if calib_ok else 'FAILED'}")

    # ── 组间统计 ──
    def group_metric(key: str, group: str) -> list[float]:
        return [float(r[key]) for r in rows if r["group"] == group]

    a_d1 = group_metric("D1_hits", "A")
    b_d1 = group_metric("D1_hits", "B")
    a_d3 = group_metric("D3_missed", "A")
    b_d3 = group_metric("D3_missed", "B")
    a_d2 = [r["D2_conseq"] for r in rows if r["group"] == "A"]
    b_d2 = [r["D2_conseq"] for r in rows if r["group"] == "B"]
    a_d4 = [r["D4_confirm_count"] for r in rows if r["group"] == "A"]
    b_d4 = [r["D4_confirm_count"] for r in rows if r["group"] == "B"]

    mw_d1 = mann_whitney(a_d1, b_d1)
    mw_d3 = mann_whitney(b_d3, a_d3)  # B 漏检 > A 漏检
    d_d1 = cohens_d(a_d1, b_d1)
    d_d3 = cohens_d(b_d3, a_d3)
    f_d2 = fisher_exact(sum(a_d2), len(a_d2) - sum(a_d2),
                        sum(b_d2), len(b_d2) - sum(b_d2))

    print("\n=== GROUP STATS (A: with blindspot prompt, B: baseline) ===")
    print(f"D1 hits        A={a_d1} B={b_d1} | MWU p={mw_d1['p_exact_twosided']:.4f} d={d_d1:.2f}")
    print(f"D2 conseq pass A={sum(a_d2)}/5 B={sum(b_d2)}/5 | Fisher p={f_d2:.4f}")
    print(f"D3 missed      A={a_d3} B={b_d3} | MWU p={mw_d3['p_exact_twosided']:.4f} d={d_d3:.2f}")
    print(f"D4 confirm cnt A={a_d4} B={b_d4} | A in [1,3]: {all(1 <= n <= 3 for n in a_d4)}; "
          f"B in [1,3]: {all(1 <= n <= 3 for n in b_d4)}")
    print(f"D4 char/token budget: A max chars={max(r['chars'] for r in rows if r['group']=='A')} "
          f"(~{max(r['chars'] for r in rows if r['group']=='A') // 2} tokens, budget 800)")

    # 判定输入（D-04 §8）
    d1_sig = mw_d1["p_exact_twosided"] < 0.05 and d_d1 >= 0.8
    d2_sig = f_d2 < 0.05 and sum(a_d2) / 5 >= 0.8 and sum(b_d2) / 5 <= 0.5
    d3_sig = mw_d3["p_exact_twosided"] < 0.05 and d_d3 >= 0.8
    d4_ok = all(1 <= n <= 3 for n in a_d4) and all(n == 0 for n in b_d4)
    sig_count = sum([d1_sig, d2_sig, d3_sig, d4_ok])
    print(f"\nsignals: D1={d1_sig} D2={d2_sig} D3={d3_sig} D4={d4_ok} "
          f"| {sig_count}/4 dimensions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
