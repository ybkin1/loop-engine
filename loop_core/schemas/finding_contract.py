"""
finding_contract.py — Finding 结构化契约校验与 BH 映射（T-0108 F7）。

对齐 BH ``harness-findings.input.json`` 字段映射（design-bh-integration.md F7）：

    LE finding 字段              →  BH harness-findings 字段
    ----------------------------   ---------------------------------
    finding_id                   →  id
    title                        →  title
    severity (小写)               →  severity (High/Medium/Low → 首字母大写)
    reason / message             →  reason
    dimension_refs               →  dimensionRefs
    target.{kind,package_route,
           owner_route}          →  target.{kind,packageRoute,ownerRoute}
    ai_fix_prompt                →  aiFixPrompt
    expected_artifact            →  expectedArtifact
    expected_output(s)           →  expectedOutput[]（单字符串按一条展开）
    （无对应）fix_boundary / verification_command / acceptance_checks

行为约束（design F7 必须保持）：
- fail-closed：schema 校验失败 → ``schema_status=INVALID`` + 告警（调用方记录），
  绝不静默丢弃 finding；schema 文件缺失/不可读同样视为 INVALID（不静默放行）。
- 防篡改：evidence_refs 只引用不修改；本模块不写任何文件。
- 审批闭环：finding 是建议性产物，不触发任何 gate 状态变更。
"""
from __future__ import annotations

import json
from pathlib import Path

_SCHEMA_PATH = Path(__file__).resolve().parent / "finding.schema.json"

_schema_cache: dict | None = None
_schema_load_error: str | None = None


def load_finding_schema() -> dict:
    """加载 finding.schema.json（进程内缓存）。

    Raises:
        RuntimeError: schema 文件缺失/JSON 损坏（调用方应标记 INVALID）。
    """
    global _schema_cache, _schema_load_error
    if _schema_cache is not None:
        return _schema_cache
    if _schema_load_error is not None:
        raise RuntimeError(_schema_load_error)
    try:
        _schema_cache = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _schema_load_error = f"finding.schema.json 不可读: {type(exc).__name__}: {exc}"
        raise RuntimeError(_schema_load_error)
    return _schema_cache


def validate_finding(finding: dict) -> tuple[bool, list[str]]:
    """校验单个 finding dict 是否符合 finding.schema.json。

    Returns:
        (ok, errors)。永不抛出；schema 不可用视为校验失败
        （fail-closed，不静默放行）。
    """
    try:
        schema = load_finding_schema()
    except RuntimeError as exc:
        return False, [str(exc)]
    try:
        import jsonschema  # type: ignore
    except ImportError:
        # jsonschema 不可用 → fail-closed：标 INVALID 并说明原因
        return False, ["jsonschema 不可用，无法校验 finding 契约"]
    try:
        jsonschema.validate(finding, schema)
        return True, []
    except Exception as exc:  # jsonschema.ValidationError 及子类
        errors = str(exc).splitlines()
        return False, [errors[0]] if errors else [str(exc)]


def mark_schema_status(finding: dict) -> dict:
    """就地附加 schema 校验状态（VALID/INVALID + errors），返回原 dict。

    供各扫描器在产出的 finding dict 上调用；不改变其余字段。
    """
    ok, errors = validate_finding(finding)
    finding["schema_status"] = "VALID" if ok else "INVALID"
    if errors:
        finding["schema_errors"] = errors[:5]
    return finding


def to_bh_finding(le_finding: dict) -> dict:
    """LE finding → BH harness-findings.input.json 字段映射（AC-03 对照测试用）。

    只做字段名映射与 severity 大小写规范化；LE 独有字段
    （fix_boundary/verification_command/acceptance_checks 等）原样透传。
    """
    bh: dict = {
        "id": le_finding.get("finding_id", le_finding.get("id", "")),
        "title": le_finding.get("title", ""),
        "severity": str(le_finding.get("severity", "medium")).capitalize(),
        "reason": le_finding.get("reason") or le_finding.get("message", ""),
    }
    dims = le_finding.get("dimension_refs")
    if dims:
        bh["dimensionRefs"] = list(dims)
    target = le_finding.get("target")
    if isinstance(target, dict):
        bh["target"] = {
            "kind": target.get("kind", "repo-root"),
            "packageRoute": target.get("package_route"),
            "ownerRoute": target.get("owner_route"),
        }
    if le_finding.get("ai_fix_prompt"):
        bh["aiFixPrompt"] = le_finding["ai_fix_prompt"]
    if le_finding.get("expected_artifact"):
        bh["expectedArtifact"] = le_finding["expected_artifact"]
    outputs = le_finding.get("expected_outputs")
    if outputs:
        bh["expectedOutput"] = list(outputs)
    elif le_finding.get("expected_output"):
        bh["expectedOutput"] = [le_finding["expected_output"]]
    return bh


def validate_finding_list(findings: list[dict]) -> tuple[int, list[dict]]:
    """批量校验；返回 (invalid_count, 已附加 schema_status 的 findings)。"""
    invalid = 0
    for finding in findings:
        mark_schema_status(finding)
        if finding.get("schema_status") == "INVALID":
            invalid += 1
    return invalid, findings
