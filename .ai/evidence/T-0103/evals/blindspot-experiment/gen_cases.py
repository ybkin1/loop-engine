#!/usr/bin/env python3
r"""gen_cases.py — 生成盲点实验 EvalCase 集（cases-blindspot.yaml）

D-04 §6 步骤 4：用 fixture 的种子盲点 + outputs/ 产出生成 case 文件。
每个产出（10 份实验产出 + 2 份校准样例）生成 8 个 case：
  - D1-struct   : 盲点表格结构存在（text_matches `| B\d` 行）
  - D1/D3-seedN : 5 个种子盲点各一个 text_contains 命中断言
                  （D1 覆盖率 = PASS 数；D3 漏检数 = 5 - PASS 数）
  - D2-conseq   : 含"若不考虑"后果说明（text_contains）
  - D4-confirm  : 至少一条"需要用户确认：是"（text_matches `| 是 |`）

用法: C:/Python312/python.exe gen_cases.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))  # 项目根

from loop_core.evals import EvalCase, dump_cases_yaml  # noqa: E402

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
OUTPUTS = HERE / "outputs"
CASES_OUT = HERE / "cases" / "cases-blindspot.yaml"

SEED_SEVERITY = "high"   # 漏检种子 = 返工风险
STRUCT_SEVERITY = "medium"
D4_SEVERITY = "high"


def load_fixtures() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for fp in sorted(FIXTURES.glob("scenario-*.json")):
        data = json.loads(fp.read_text(encoding="utf-8"))
        out[data["scenario_id"]] = data
    return out


def build_cases_for_output(
    rel_name: str,
    text: str,
    fixture: dict,
    group: str,
    scenario: str,
) -> list[dict]:
    sc = fixture["scenario_id"]
    cases: list[dict] = []

    # D1 结构 case：盲点表格行（| B1 | ...）
    cases.append({
        "case_id": f"{sc}-{group}-D1-struct",
        "title": f"[{sc}/{group}] 盲点清单表格结构存在（B 编号行）",
        "input": text,
        "rule": {"type": "text_matches", "params": {"pattern": r"\| B\d"}},
        "severity": STRUCT_SEVERITY,
        "version": "1",
        "tags": ["experiment:blindspot", f"group:{group}",
                 f"scenario:{scenario}", "dimension:D1"],
    })

    # 5 个种子盲点命中断言（D1 覆盖率 / D3 漏检数共用）
    for seed in fixture["seed_blind_spots"]:
        cases.append({
            "case_id": f"{sc}-{group}-D3-seed-{seed['id']}",
            "title": (f"[{sc}/{group}] 种子盲点命中：{seed['id']} "
                      f"（{seed['keyword']}）"),
            "input": text,
            "rule": {"type": "text_contains", "params": {"value": seed["keyword"]}},
            "severity": SEED_SEVERITY,
            "version": "1",
            "tags": ["experiment:blindspot", f"group:{group}",
                     f"scenario:{scenario}", "dimension:D1", "dimension:D3",
                     f"seed:{seed['id']}"],
        })

    # D2 问题质量：后果说明标志词
    cases.append({
        "case_id": f"{sc}-{group}-D2-conseq",
        "title": f"[{sc}/{group}] 盲点含'若不考虑'后果说明",
        "input": text,
        "rule": {"type": "text_contains", "params": {"value": "若不考虑"}},
        "severity": STRUCT_SEVERITY,
        "version": "1",
        "tags": ["experiment:blindspot", f"group:{group}",
                 f"scenario:{scenario}", "dimension:D2"],
    })

    # D4 用户需确认次数：至少 1 条"需要用户确认：是"
    cases.append({
        "case_id": f"{sc}-{group}-D4-confirm",
        "title": f"[{sc}/{group}] 存在'需要用户确认：是'的盲点（≥1）",
        "input": text,
        "rule": {"type": "text_matches", "params": {"pattern": r"\| 是 \|"}},
        "severity": D4_SEVERITY,
        "version": "1",
        "tags": ["experiment:blindspot", f"group:{group}",
                 f"scenario:{scenario}", "dimension:D4"],
    })
    return cases


def main() -> int:
    fixtures = load_fixtures()
    all_cases: list[dict] = []
    scenario_names = {"S1": "S1", "S2": "S2", "S4": "S4", "S5": "S5", "S6": "S6"}

    # 实验产出：A/B × 5 场景
    for group in ("A", "B"):
        for sc_id in ("S1", "S2", "S4", "S5", "S6"):
            fp = OUTPUTS / f"{group}-{sc_id}-1.md"
            if not fp.exists():
                print(f"missing output: {fp}")
                return 1
            all_cases += build_cases_for_output(
                fp.name, fp.read_text(encoding="utf-8"),
                fixtures[sc_id], group, scenario_names[sc_id],
            )

    # 校准样例（评分规则区分度验证）
    calib_high = OUTPUTS / "calibration" / "calib-high.md"
    calib_low = OUTPUTS / "calibration" / "calib-low.md"
    all_cases += build_cases_for_output(
        calib_high.name, calib_high.read_text(encoding="utf-8"),
        fixtures["S1"], "calib-high", "S1",
    )
    all_cases += build_cases_for_output(
        calib_low.name, calib_low.read_text(encoding="utf-8"),
        fixtures["S1"], "calib-low", "S1",
    )

    # schema 校验（非法 case 整批拒绝）
    objs = [EvalCase.from_dict(c) for c in all_cases]
    dump_cases_yaml(objs, CASES_OUT)
    print(f"cases written: {CASES_OUT} ({len(objs)} cases, "
          f"{len({c.case_id for c in objs})} unique ids)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
