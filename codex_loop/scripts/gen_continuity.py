"""Generate a minimal valid ProjectContinuity/v1 for a Loop project."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
ai_dir = root / ".ai"

# Build source manifest from existing .ai/ files
out_path = ai_dir / "project_continuity.yaml"
out_path_json = ai_dir / "project_continuity.json"

sources = []
for f in sorted(ai_dir.rglob("*")):
    if f.is_file() and f.suffix in (".yaml", ".md"):
        # Exclude the output file itself to prevent first-run hash drift
        # Generated continuity and handoff files are controllers, not immutable source inputs.
        if f.resolve() in {
            out_path.resolve(), out_path_json.resolve(),
            (ai_dir / "HANDOFF.md").resolve(), (ai_dir / "state.yaml").resolve(),
        }:
            continue
        rel = str(f.relative_to(root)).replace("\\", "/")
        data = f.read_bytes()
        sources.append({
            "path": rel,
            "sha256": hashlib.sha256(data).hexdigest().upper(),
            "size": len(data),
        })

manifest_json = json.dumps(sources, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
source_sha = hashlib.sha256(manifest_json.encode()).hexdigest().upper()

now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

doc = {
    "schema": "ProjectContinuity/v1",
    "contract_id": "PCC-2026-07-16-R1",
    "project_id": "loop-engine",
    "created_at": now,
    "created_by": "loop-governance",
    "authority_ref": "G-T-0001-INIT",
    "requirements_revision": "v0.1.0",
    "semantic_sha256": "8F32DFDC8DF0D3B5F6BA4993193CD8DD0CEBC44294317B5A04DAA355C51A8847",
    "source_sha256": source_sha,
    "source_manifest": sources,
    "project_continuity": {
        "user_origin": {
            "audience": "单人AI辅助软件研发",
            "capability_assumptions": ["用户无代码能力", "用户无项目管理背景"],
            "user_authorities": ["批准gate", "拒绝gate", "请求修复", "提出目标"],
        },
        "product_identity": {
            "project_id": "loop-engine",
            "one_sentence_outcome": "帮助无代码能力的用户以Loop工程方式从需求到可交付软件",
            "north_star": "每个非技术用户都能借助AI交付可用软件",
            "success_signals": [
                "治理流程可被非技术用户理解",
                "gate机制有效阻断未授权操作",
                "证据链完整可审计",
            ],
        },
        "design_language": {
            "terms": {},
            "forbidden_equivalences": [],
        },
        "engineering_invariants": {
            "architecture": "Loop工程治理插件架构",
            "technology": "Python 3.10+, ZCode Plugin API",
            "interfaces": "ZCode Hook协议, MCP JSON-RPC",
            "coding_standards": "PEP 8",
            "quality": "test coverage >= 80%",
            "security": "no hardcoded secrets",
        },
        "authorization_boundaries": {
            "allowed_effects": ["read", "write governance files"],
            "forbidden_effects": [
                "deploy", "rollback", "database", "permission",
                "secret", "payment", "production_data", "migration",
            ],
            "current_gate_id": None,
        },
        "lifecycle": {
            "phase": "S0-init",
            "task_id": None,
            "task_status": None,
            "active_transaction_ids": [],
            "in_flight_actor_ids": [],
        },
        "evidence_index": {
            "canonical": [],
            "additive": [],
            "superseded_not_deleted": [],
        },
        "revision_lineage": {
            "parent_revision": None,
            "change_set_id": "init-v1",
            "impact_assessment_ref": None,
            "approval_ref": None,
        },
        "protected_decisions": [
            {
                "decision_id": "MEANS_END_BOUNDARY",
                "statement": "AI负责手段，用户负责目标和gate批准",
                "rationale_ref": ".ai/DECISIONS.md",
                "authority_ref": "user",
                "change_policy": "需用户显式gate批准",
            },
            {
                "decision_id": "USER_AUTHORITY",
                "statement": "只有用户能批准gate、拒绝gate、请求修复",
                "rationale_ref": ".ai/DECISIONS.md",
                "authority_ref": "user",
                "change_policy": "不可变更",
            },
            {
                "decision_id": "CODEX_DELIVERY_RESPONSIBILITY",
                "statement": "AI负责在批准范围内完成交付",
                "rationale_ref": ".ai/DECISIONS.md",
                "authority_ref": "user",
                "change_policy": "需用户显式gate批准",
            },
            {
                "decision_id": "EVIDENCE_ONLY_BOUNDARY",
                "statement": "reviewer PASS、测试通过、validator成功仅为evidence，不替代用户批准",
                "rationale_ref": ".ai/DECISIONS.md",
                "authority_ref": "user",
                "change_policy": "不可变更",
            },
        ],
        "golden_references": [],
        "non_goals": [],
    },
}

# Write as YAML (use PyYAML if available, otherwise JSON)
try:
    import yaml

    out_path = ai_dir / "project_continuity.yaml"
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(doc, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"[ok] Created: {out_path}")
except ImportError:
    # Fallback: write JSON and tell user to convert
    out_path = ai_dir / "project_continuity.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    print(f"[warn] PyYAML not available, wrote JSON: {out_path}")
    print("[warn] Please convert to YAML format.")
