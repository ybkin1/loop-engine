#!/usr/bin/env python3
"""wire_authenticity.py — 将 AUTHENTICITY 维度接入 output_quality.ts（OQA-5D）

1. 导入 authenticityCheckers + AUTHENTICITY_LABEL
2. DIMENSION_ORDER 增加 AUTHENTICITY
3. DIMENSION_LABELS 增加 AUTHENTICITY
4. CHECKER_REGISTRY 增加 AUTHENTICITY
5. renderReportSummary 标题 OQA-4D → OQA-5D
幂等：哨兵检查。
"""
from pathlib import Path

ENGINE = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\core\output_quality.ts")
AUTH = Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\core\authenticity.ts")

def main() -> int:
    # 1. 部署 authenticity.ts
    if AUTH.exists():
        import hashlib
        staging = Path(r"C:\Users\Administrator\ZCodeProject\loop-engine\.ai\staging\T-0168\authenticity.ts")
        if not AUTH.exists() or hashlib.sha256(AUTH.read_bytes()).hexdigest() != hashlib.sha256(staging.read_bytes()).hexdigest():
            AUTH.write_text(staging.read_text(encoding="utf-8"), encoding="utf-8")
            print("[copy] authenticity.ts deployed")
        else:
            print("[same] authenticity.ts")
    else:
        AUTH.write_text(Path(r"C:\Users\Administrator\ZCodeProject\loop-engine\.ai\staging\T-0168\authenticity.ts").read_text(encoding="utf-8"), encoding="utf-8")
        print("[copy] authenticity.ts deployed")

    t = ENGINE.read_text(encoding="utf-8")

    # 2. 导入
    if "authenticityCheckers" not in t:
        old_import = 'import { parseDocument } from "yaml";'
        new_import = 'import { parseDocument } from "yaml";\nimport { authenticityCheckers, AUTHENTICITY_LABEL } from "./authenticity.js";'
        assert t.count(old_import) == 1, "import anchor"
        t = t.replace(old_import, new_import)
        print("[patch] import added")

    # 3. DIMENSION_ORDER
    old_order = 'export const DIMENSION_ORDER: DimensionId[] = [\n  "REQUIREMENTS",\n  "CODING",\n  "DESIGN",\n  "ENGINEERING",\n];'
    new_order = 'export const DIMENSION_ORDER: DimensionId[] = [\n  "REQUIREMENTS",\n  "CODING",\n  "DESIGN",\n  "ENGINEERING",\n  "AUTHENTICITY",\n];'
    if '"AUTHENTICITY",' not in t:
        assert t.count(old_order) == 1, "DIMENSION_ORDER anchor"
        t = t.replace(old_order, new_order)
        print("[patch] DIMENSION_ORDER + AUTHENTICITY")

    # 4. DimensionId type
    old_type = 'export type DimensionId =\n  | "REQUIREMENTS"\n  | "CODING"\n  | "DESIGN"\n  | "ENGINEERING";'
    new_type = 'export type DimensionId =\n  | "REQUIREMENTS"\n  | "CODING"\n  | "DESIGN"\n  | "ENGINEERING"\n  | "AUTHENTICITY";'
    if '"AUTHENTICITY";' not in t:
        assert t.count(old_type) == 1, "DimensionId anchor"
        t = t.replace(old_type, new_type)
        print("[patch] DimensionId + AUTHENTICITY")

    # 5. DIMENSION_LABELS
    old_labels = 'const DIMENSION_LABELS: Record<DimensionId, string> = {\n  REQUIREMENTS: "需求符合性",\n  CODING: "编码规范",\n  DESIGN: "设计理念",\n  ENGINEERING: "软件工程",\n};'
    new_labels = 'const DIMENSION_LABELS: Record<DimensionId, string> = {\n  REQUIREMENTS: "需求符合性",\n  CODING: "编码规范",\n  DESIGN: "设计理念",\n  ENGINEERING: "软件工程",\n  AUTHENTICITY: AUTHENTICITY_LABEL,\n};'
    if "AUTHENTICITY: AUTHENTICITY_LABEL" not in t:
        assert t.count(old_labels) == 1, "DIMENSION_LABELS anchor"
        t = t.replace(old_labels, new_labels)
        print("[patch] DIMENSION_LABELS + AUTHENTICITY")

    # 6. CHECKER_REGISTRY
    old_reg = "const CHECKER_REGISTRY: Record<DimensionId, Checker[]> = {\n  REQUIREMENTS: requirementCheckers,\n  CODING: codingCheckers,\n  DESIGN: designCheckers,\n  ENGINEERING: engineeringCheckers,\n};"
    new_reg = "const CHECKER_REGISTRY: Record<DimensionId, Checker[]> = {\n  REQUIREMENTS: requirementCheckers,\n  CODING: codingCheckers,\n  DESIGN: designCheckers,\n  ENGINEERING: engineeringCheckers,\n  AUTHENTICITY: authenticityCheckers as unknown as Checker[],\n};"
    if "AUTHENTICITY: authenticityCheckers" not in t:
        assert t.count(old_reg) == 1, "CHECKER_REGISTRY anchor"
        t = t.replace(old_reg, new_reg)
        print("[patch] CHECKER_REGISTRY + AUTHENTICITY")

    # 7. renderReportSummary 标题
    old_title = "`Output Quality Report (OQA-4D ${report.engine_version})`"
    new_title = "`Output Quality Report (OQA-5D ${report.engine_version})`"
    if "OQA-5D" not in t:
        assert t.count(old_title) == 1, "title anchor"
        t = t.replace(old_title, new_title)
        print("[patch] report title OQA-5D")

    ENGINE.write_text(t, encoding="utf-8")
    print("[ok] OQA-5D wiring complete")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
