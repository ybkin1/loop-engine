from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codex_loop.context.policy import safe_relative_path
from codex_loop.core.contracts import RoleRegistry
from codex_loop.core.models import ProjectProfile
from codex_loop.core.store import LoopStore
from codex_loop.materials import MaterialCatalog
from codex_loop.packets.functional import FunctionalDesignPacket
from codex_loop.packets.human import render_human_review_packet
from codex_loop.planning.phases import default_phases
from codex_loop.quality.checks import check_candidate_store, check_role_prompts, check_role_registry
from codex_loop.runtime.runner import CodexRuntime, RoleRunRequest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ROLE_REGISTRY = PACKAGE_ROOT / "roles" / "registry.json"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_evidence(root: Path, values: list[str]) -> tuple[tuple[str, str], ...]:
    evidence: list[tuple[str, str]] = []
    for value in values:
        if "=" not in value:
            raise SystemExit("--evidence must use label=relative-path")
        label, raw_path = value.split("=", 1)
        if not label or not raw_path:
            raise SystemExit("--evidence label and path are required")
        relative = safe_relative_path(root, Path(raw_path))
        path = root / relative
        if not path.is_file():
            raise SystemExit(f"evidence file does not exist: {relative.as_posix()}")
        evidence.append((label, path.read_text(encoding="utf-8")))
    return tuple(evidence)


def _feature_demo() -> dict[str, Any]:
    return {
        "feature_id": "T0036-MATERIAL-LIBRARY",
        "feature_name": "软件工程与提示词工程素材库",
        "user_goal": "让未来项目优先复用软件工程规范、案例、模板和输出范式，而不是依赖模型临时自觉。",
        "actors": ["项目负责人", "产品经理", "架构师", "质量工程师", "Codex 主控"],
        "preconditions": ["项目意图已确认", "T-0036 catalog 可读", "来源状态可追溯"],
        "user_guide": {
            "entry": "Codex 识别项目类型、技术栈、风险和目标后启动 Loop",
            "steps": ["生成 Project Profile", "按软件工程问题检索材料", "记录采用/拒绝/待验证材料", "形成角色和阶段工作包", "用户阅读交付包并决定是否继续"],
            "success": "项目获得可追溯的需求、架构、设计、测试和交付输入",
            "failure": "来源不可信、范围不清或证据不足时阻断并列出需要补充的内容",
            "navigation": "用户通过 Human Review Packet 查看结论、取舍、风险和下一步",
        },
        "frontend": {
            "pages": ["Project Profile", "Material Selection", "Phase Review", "Functional Design Packet"],
            "elements": ["阶段导航", "材料筛选结果", "采用/拒绝原因", "验证状态", "风险列表", "用户决策按钮"],
            "states": ["candidate", "needs_research", "repair_required", "ready_for_review", "approved", "blocked"],
            "validation": ["用户决策不能为空", "未验证来源显示警告", "阻断状态不可进入下一阶段"],
            "accessibility": ["结论先于证据", "每个状态有文本标签", "键盘可达的决策控件"],
        },
        "backend": {
            "modules": ["intent_router", "material_selector", "role_registry", "context_builder", "phase_planner", "evidence_checker", "packet_renderer"],
            "apis": ["create project profile", "select materials", "create work packet", "run deterministic checks", "render review packet"],
            "data_model": ["ProjectProfile", "MaterialSelection", "RoleContract", "WorkPacket", "RoleRunEnvelope", "Finding", "GateRecord"],
            "state_transitions": ["candidate -> ready_for_review -> approved_by_user", "repair_required -> repaired -> regression_checked", "blocked -> user_decision_required"],
            "errors": ["missing input", "unknown role/material", "context budget exceeded", "write boundary violation", "pending user gate"],
            "idempotency": ["same input fingerprint yields same selection/order", "atomic JSON writes", "re-running checks does not duplicate findings"],
            "observability": ["command trace", "artifact fingerprints", "role/phase/run IDs", "check result"],
        },
        "security": {
            "boundaries": ["external source is untrusted data", "role output is not a state transition", "project root is the write boundary"],
            "authn_authz": ["Codex host capability is detected", "role allowed_read/allowed_write is checked", "independent reviewer is read-only"],
            "input_protection": ["secret markers rejected", "prompt-like external content never becomes control instruction", "path traversal rejected"],
            "abuse_prevention": ["bounded context", "bounded task scope", "no unbounded parallel dispatch", "blocked states are sticky until decision"],
            "data_protection": ["no secrets in packets", "fingerprints instead of raw sensitive values", "local candidate only"],
            "audit": ["RoleRunEnvelope", "finding history", "Gate decision record"],
        },
        "performance": {
            "budgets": ["role context budget declared per contract", "selection loads only matched materials", "packet rendering is local and deterministic"],
            "bottlenecks": ["large catalog search", "independent review context", "repeated repair loops"],
            "scaling": ["index catalog by category and terms later", "cache stable role contracts", "parallelize disjoint evidence checks"],
            "degradation": ["reduce selected evidence", "serialize work", "return USER_DECISION_REQUIRED instead of guessing"],
        },
        "maintainability": {
            "module_boundaries": ["core models do not import CLI", "role registry does not mutate project state", "packets render from structured data"],
            "dependencies": ["Python standard library", "PyYAML only for external material catalog"],
            "extension": ["add role contract without changing controller", "add checker by registry", "add packet section through schema version"],
            "runbook": ["validate roles", "init project", "run checks", "inspect review packet"],
        },
        "testing": {
            "unit": ["role contract validation", "fingerprints", "graph cycles", "packet required sections"],
            "component": ["context builder", "path policy", "material selector", "store atomic write"],
            "contract": ["RoleRunEnvelope and WorkPacket fields", "packet schema"],
            "integration": ["init -> select -> plan -> packet -> verify"],
            "e2e": ["T-0036 local candidate exercise"],
            "security": ["path traversal", "secret markers", "role self-approval", "untrusted source instruction"],
            "performance": ["bounded context and catalog selection timing"],
            "recovery": ["atomic write interruption", "stale fingerprint", "blocked phase"],
        },
        "decisions": ["软件工程来源优先于提示词技巧", "Codex-only local candidate", "内部质量 Gate 与用户 Gate 分离", "结构化交付物优先于长自然语言"],
        "risks": ["素材库候选内容尚未全部独立复核", "Codex host runtime capability is not globally enabled", "真实模型调用和角色效果尚未认证"],
        "user_decisions": ["是否接受该素材库作为 Codex Loop 设计输入", "是否接受角色/阶段/功能设计包结构", "是否允许进入下一阶段实现或要求修复"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-loop")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("roles-validate")
    init = sub.add_parser("init")
    init.add_argument("--root", type=Path, required=True)
    init.add_argument("--project-id", required=True)
    init.add_argument("--goal", required=True)
    init.add_argument("--risk-tier", default="medium")
    init.add_argument("--delivery-target", default="candidate")
    phases = sub.add_parser("phases")
    phases.add_argument("--output", type=Path)
    plan = sub.add_parser("plan")
    plan.add_argument("--output", type=Path)
    packet = sub.add_parser("packet")
    packet.add_argument("--input", type=Path)
    packet.add_argument("--output", type=Path, required=True)
    packet.add_argument("--demo-t0036", action="store_true")
    select = sub.add_parser("select-materials")
    select.add_argument("--catalog", type=Path, required=True)
    select.add_argument("--output", type=Path, required=True)
    select.add_argument("terms", nargs="+")
    demo = sub.add_parser("demo-t0036")
    demo.add_argument("--root", type=Path, required=True)
    prepare = sub.add_parser("prepare-run")
    prepare.add_argument("--root", type=Path, required=True)
    prepare.add_argument("--role", required=True)
    prepare.add_argument("--task-id", required=True)
    prepare.add_argument("--phase-id", required=True)
    prepare.add_argument("--purpose", required=True)
    prepare.add_argument("--tool", dest="available_tools", action="append", default=[])
    prepare.add_argument("--write-target", action="append", default=[])
    prepare.add_argument("--evidence", action="append", default=[])
    prepare.add_argument("--material", dest="selected_materials", action="append", default=[])
    verify = sub.add_parser("verify")
    verify.add_argument("--root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "roles-validate":
        registry = RoleRegistry.load(ROLE_REGISTRY)
        results = [check_role_registry(registry), check_role_prompts(registry)]
        status = "PASS" if all(result.status == "PASS" for result in results) else "FAIL"
        print(json.dumps({"status": status, "checks": [result.to_dict() for result in results]}, ensure_ascii=False))
        return 0 if status == "PASS" else 1
    if args.command == "init":
        store = LoopStore(args.root)
        store.initialize(ProjectProfile(args.project_id, args.goal, args.risk_tier, args.delivery_target))
        print(json.dumps({"status": "initialized", "root": str(args.root.resolve()), "store": str(store.loop_root)}, ensure_ascii=False))
        return 0
    if args.command == "phases":
        payload = {"phases": [phase.to_dict() for phase in default_phases()]}
        if args.output:
            _write_json(args.output, payload)
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.command == "plan":
        from codex_loop.planning.graph import default_task_graph

        payload = default_task_graph().to_dict()
        if args.output:
            _write_json(args.output, payload)
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.command == "packet":
        if not args.demo_t0036 and not args.input:
            raise SystemExit("--input is required unless --demo-t0036 is set")
        source = _feature_demo() if args.demo_t0036 else json.loads(args.input.read_text(encoding="utf-8"))
        packet = FunctionalDesignPacket.from_dict(source)
        errors = packet.validate()
        if errors:
            raise SystemExit(f"invalid packet sections: {', '.join(errors)}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(packet.render_markdown(), encoding="utf-8")
        return 0
    if args.command == "select-materials":
        catalog = MaterialCatalog.load(args.catalog)
        selected = catalog.select(tuple(args.terms))
        _write_json(args.output, catalog.selection_record(selected, tuple(args.terms)))
        print(json.dumps({"status": "candidate", "selected": [item.material_id for item in selected]}, ensure_ascii=False))
        return 0
    if args.command == "demo-t0036":
        store = LoopStore(args.root)
        store.initialize(ProjectProfile("T-0036", "build software engineering material library", "medium", "candidate"))
        packet = FunctionalDesignPacket.from_dict(_feature_demo())
        output = store.loop_root / "packets" / "functional" / "T-0036-material-library.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(packet.render_markdown(), encoding="utf-8")
        review = render_human_review_packet(
            "T-0036",
            "P11",
            "Candidate Codex Loop material-library exercise is ready for review.",
            [".loop/packets/functional/T-0036-material-library.md"],
            ["role registry", "phase model", "functional packet schema"],
            ["real model role execution", "independent production review"],
            ["accept candidate packet and continue", "require repair", "defer"],
        )
        (store.loop_root / "packets" / "review").mkdir(parents=True, exist_ok=True)
        (store.loop_root / "packets" / "review" / "P11-human-review.md").write_text(review, encoding="utf-8")
        print(json.dumps({"status": "candidate", "store": str(store.loop_root), "packet": str(output)}, ensure_ascii=False))
        return 0
    if args.command == "prepare-run":
        root = args.root.resolve()
        request = RoleRunRequest(
            run_id=f"run-{args.role}-{args.task_id}",
            role_id=args.role,
            task_id=args.task_id,
            phase_id=args.phase_id,
            purpose=args.purpose,
            selected_materials=tuple(args.selected_materials),
            selected_evidence=_read_evidence(root, args.evidence),
            available_tools=tuple(args.available_tools),
            write_targets=tuple(args.write_target),
        )
        envelope = CodexRuntime(root).prepare_run(request)
        print(json.dumps({"status": envelope.verdict, "run_id": envelope.run_id}, ensure_ascii=False))
        return 0 if envelope.verdict == "READY_TO_INVOKE" else 1
    if args.command == "verify":
        store = LoopStore(args.root)
        if not store.exists():
            print(json.dumps({"status": "FAIL", "message": "Loop store is not initialized"}, ensure_ascii=False))
            return 1
        registry = RoleRegistry.load(ROLE_REGISTRY)
        results = [check_role_registry(registry), check_role_prompts(registry), check_candidate_store(store.loop_root)]
        status = "PASS" if all(result.status == "PASS" for result in results) else "FAIL"
        print(json.dumps({
            "status": status,
            "checks": [{"id": result.check_id, "status": result.status, "message": result.message} for result in results],
        }, ensure_ascii=False))
        return 0 if status == "PASS" else 1
    raise SystemExit("unhandled command")
