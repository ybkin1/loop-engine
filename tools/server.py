#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
server.py — Loop 工程 MCP 工具服务器。

通过 MCP stdio JSON-RPC 协议暴露工具给 ZCode LLM agent 调用。
每个工具对应一个 role 脚本的薄包装，返回结构化 JSON。

工具清单（tools/list）：
  - quality_gates_run     → 跑质量门禁，返回质量报告
  - security_scan_run     → 跑安全扫描，返回安全报告
  - dependency_analysis   → 分析项目依赖图，检测循环依赖
  - contract_validate     → 验证接口契约 schema 与代码一致性
  - evidence_verify       → 验证证据链完整性
  - evidence_freeze       → 冻结证据（写入 content_sha256）
  - cost_report           → 生成 token 成本报告

协议：JSON-RPC 2.0 over stdin/stdout
"""
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent

TOOLS = {
    "quality_gates_run": {
        "description": "运行质量门禁（lint/test/coverage/audit），返回结构化质量报告",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string", "description": "项目根目录路径"},
                "output_dir": {"type": "string", "description": "报告输出目录（默认 .ai/evidence/quality/）"}
            },
            "required": ["project_root"]
        }
    },
    "security_scan_run": {
        "description": "运行安全扫描（CVE/密钥/注入面/权限），返回结构化安全报告",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string", "description": "项目根目录路径"},
                "output_dir": {"type": "string", "description": "报告输出目录"}
            },
            "required": ["project_root"]
        }
    },
    "dependency_analysis": {
        "description": "分析项目模块依赖图，检测循环依赖和边界违规",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string", "description": "项目根目录路径"},
                "rules_file": {"type": "string", "description": "边界规则 JSON 文件路径"}
            },
            "required": ["project_root"]
        }
    },
    "contract_validate": {
        "description": "验证接口契约 JSON schema 完整性，可选对比代码实际导出",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "contract_file": {"type": "string", "description": "interface-contract.json 路径"},
                "check_actual": {"type": "boolean", "description": "是否对比代码实际导出"}
            },
            "required": ["project_root", "contract_file"]
        }
    },
    "evidence_verify": {
        "description": "验证证据链完整性——检查每个节点的 input_hashes 是否与上游文件 SHA256 一致",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "strict": {"type": "boolean", "description": "严格模式：required 节点缺失即 BLOCKED"}
            },
            "required": ["project_root"]
        }
    },
    "evidence_freeze": {
        "description": "冻结证据——计算并写入 content_sha256 到证据文件",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "file": {"type": "string", "description": "要冻结的文件路径（相对 project_root）"}
            },
            "required": ["project_root", "file"]
        }
    },
    "cost_report": {
        "description": "生成 token 成本报告",
        "inputSchema": {
            "type": "object",
            "properties": {"project_root": {"type": "string"}},
            "required": ["project_root"]
        }
    },
    # v3.4 — governance tools
    "loop_certify_role": {
        "description": "运行角色能力认证挑战，验证角色是否胜任",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "role_id": {"type": "string", "description": "角色ID 或 'all'"}
            },
            "required": ["role_id"]
        }
    },
    "loop_governance_status": {
        "description": "获取项目治理健康状态摘要 (HEALTHY/DEGRADED/BLOCKED)",
        "inputSchema": {
            "type": "object",
            "properties": {"project_root": {"type": "string"}}
        }
    },
    "loop_state": {
        "description": "查询当前项目状态（阶段/任务/gate）",
        "inputSchema": {
            "type": "object",
            "properties": {"project_root": {"type": "string"}}
        }
    },
    "loop_review_packet": {
        "description": "生成人可读的 gate 审批包或否决升级包",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "packet_type": {"type": "string", "description": "GATE_APPROVAL | VETO_ESCALATION | CHANGE_REQUEST"},
                "phase": {"type": "string"},
                "task_id": {"type": "string"},
                "vetos": {"type": "array", "items": {"type": "object"}},
                "description": {"type": "string"}
            },
            "required": ["packet_type"]
        }
    },
    "loop_audit_log": {
        "description": "追加或验证链式哈希审计日志",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "event": {"type": "string"},
                "actor": {"type": "string"},
                "details": {"type": "object"},
                "verify": {"type": "boolean"}
            },
            "required": ["event", "actor"]
        }
    },
    # v3.5 — remaining governance tools
    "loop_route_intent": {
        "description": "分析用户意图，推荐 Loop 模式和变更类型",
        "inputSchema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "用户意图描述"},
                "is_existing": {"type": "boolean"}
            },
            "required": ["description"]
        }
    },
    "loop_constraint_check": {
        "description": "运行全部 8 项硬约束检查 (C1-C8)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "target_path": {"type": "string"},
                "current_phase": {"type": "string"},
                "target_phase": {"type": "string"}
            }
        }
    },
    "loop_execute_phase": {
        "description": "执行一个完整的 Loop 阶段",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "phase_id": {"type": "string"}
            },
            "required": ["phase_id"]
        }
    },
    "loop_execution_log": {
        "description": "查询执行账本记录",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "task_id": {"type": "string"},
                "role_id": {"type": "string"},
                "recent": {"type": "number"}
            }
        }
    },
    "loop_veto_escalate": {
        "description": "分析否决并确定升级级别",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vetos": {"type": "array", "items": {"type": "object"}},
                "generate_summary": {"type": "boolean"}
            },
            "required": ["vetos"]
        }
    },
    "loop_evidence_submit": {
        "description": "提交证据并绑定内容哈希",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "evidence_id": {"type": "string"},
                "type": {"type": "string"},
                "content": {"type": "string"},
                "role_id": {"type": "string"},
                "ttl_seconds": {"type": "number"}
            },
            "required": ["evidence_id", "type", "content"]
        }
    },
    "loop_handoff": {
        "description": "创建角色间交接记录",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "from_role": {"type": "string"},
                "to_role": {"type": "string"},
                "context_summary": {"type": "string"},
                "artifacts": {"type": "array", "items": {"type": "object"}}
            },
            "required": ["from_role", "to_role", "context_summary"]
        }
    },
    "loop_load_context": {
        "description": "根据任务复杂度加载渐进式角色上下文",
        "inputSchema": {
            "type": "object",
            "properties": {
                "role_id": {"type": "string"},
                "complexity": {"type": "number"}
            },
            "required": ["role_id"]
        }
    },
    # v3.6 — canonical runtime controller entry points
    "loop_onboard_project": {
        "description": "幂等接入项目并初始化 Loop 运行时（不创建活动任务）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "intent": {"type": "string"},
                "idempotency_key": {"type": "string"}
            },
            "required": ["project_root"]
        }
    },
    "loop_propose_work_package": {
        "description": "创建工作包提案并等待用户批准",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "task_id": {"type": "string"},
                "gate_id": {"type": "string"},
                "title": {"type": "string"},
                "allowed_paths": {"type": "array", "items": {"type": "string"}},
                "non_goals": {"type": "array", "items": {"type": "string"}},
                "risk_flags": {"type": "object"}
            },
            "required": ["project_root", "task_id", "gate_id", "title", "allowed_paths"]
        }
    },
    "loop_approve_and_execute": {
        "description": "记录用户批准并原子启动执行能力",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "gate_id": {"type": "string"},
                "approval": {"type": "string"},
                "user_actor_id": {"type": "string"},
                "idempotency_key": {"type": "string"}
            },
            "required": ["project_root", "gate_id", "approval"]
        }
    },
    "loop_resume_execution": {
        "description": "使用任务和执行上下文恢复已批准执行",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"},
                "actor_id": {"type": "string"},
                "role_id": {"type": "string"},
                "caller_class": {"type": "string"},
                "task_id": {"type": "string"},
                "execution_id": {"type": "string"},
                "session_id": {"type": "string"},
                "capability_id": {"type": "string"}
            },
            "required": ["project_root", "actor_id", "role_id", "caller_class", "task_id", "execution_id"]
        }
    },
    # v3.10 — MCP Agent Runtime: bypass ZCode sub-agent limitation
    "safe_bash": SAFE_BASH_SCHEMA if SAFE_BASH_SCHEMA else {"name":"safe_bash","description":"Execute safe shell commands"} ,
        "loop_dispatch_agents": {
        "description": "按 SubagentManifest 调度所有子代理（通过 LLM API 直接调用），返回聚合结果。不写文件。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string", "description": "项目根目录"},
                "manifest": {"type": "object", "description": "SubagentManifest JSON"},
                "max_retries": {"type": "integer", "description": "每个 subagent 最大重试次数（默认 2）"}
            },
            "required": ["project_root", "manifest"]
        }
    },
}


def handle_request(request: dict) -> dict:
    """处理单个 JSON-RPC 请求，返回响应。"""
    method = request.get("method", "")
    req_id = request.get("id")

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": [
                {"name": name, **schema} for name, schema in TOOLS.items()
            ]}
        }

    if method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name not in TOOLS:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}

        result = _dispatch(tool_name, arguments)
        return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}}

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def _dispatch(tool_name: str, args: dict) -> dict:
    """分派到具体的工具脚本执行。"""
    project_root = args.get("project_root", ".")

    if tool_name == "quality_gates_run":
        from tool_quality_gates import run
        return run(project_root, args.get("output_dir"))
    elif tool_name == "security_scan_run":
        from tool_security_scan import run
        return run(project_root, args.get("output_dir"))
    elif tool_name == "dependency_analysis":
        from tool_dependency_analysis import run
        return run(project_root, args.get("rules_file"))
    elif tool_name == "contract_validate":
        from tool_contract_validate import run
        return run(project_root, args["contract_file"], args.get("check_actual", False))
        return run(project_root, args["contract_file"], args.get("check_actual", False))
    elif tool_name == "evidence_verify":
        from tool_evidence_chain import run_verify
        return run_verify(project_root, args.get("strict", False))
    elif tool_name == "evidence_freeze":
        from tool_evidence_chain import run_freeze
        return run_freeze(project_root, args["file"])
    elif tool_name == "cost_report":
        from tool_cost_tracker import run_report
        return run_report(project_root)
    # v3.4 — governance tools
    elif tool_name == "loop_certify_role":
        from tool_certify_role import run
        return run(args["role_id"], project_root)
    elif tool_name == "loop_governance_status":
        from tool_governance_status import run
        return run(project_root)
    elif tool_name == "loop_state":
        from tool_state import run
        return run(project_root)
    elif tool_name == "loop_review_packet":
        from tool_review_packet import run
        return run(
            args["packet_type"], project_root,
            phase=args.get("phase", "unknown"),
            task_id=args.get("task_id", ""),
            vetos=args.get("vetos", []),
            description=args.get("description", ""),
        )
    elif tool_name == "loop_audit_log":
        from tool_audit_log import run
        return run(
            args["event"], args["actor"], project_root,
            details=args.get("details"),
            verify=args.get("verify", False),
        )
    # v3.5
    elif tool_name == "loop_route_intent":
        from tool_route_intent import run
        return run(args.get("description", ""), is_existing=args.get("is_existing", False))
    elif tool_name == "loop_constraint_check":
        from tool_constraint_check import run
        return run(project_root, target_path=args.get("target_path"),
                   current_phase=args.get("current_phase"), target_phase=args.get("target_phase"))
    elif tool_name == "loop_execute_phase":
        from tool_execute_phase import run
        return run(args["phase_id"], project_root)
    elif tool_name == "loop_execution_log":
        from tool_execution_log import run
        return run(project_root, task_id=args.get("task_id"), role_id=args.get("role_id"), recent=args.get("recent", 10))
    elif tool_name == "loop_veto_escalate":
        from tool_veto_escalate import run
        return run(args.get("vetos", []), generate_summary=args.get("generate_summary", False))
    elif tool_name == "loop_evidence_submit":
        from tool_evidence_submit import run
        return run(args["evidence_id"], args["type"], args["content"], project_root,
                   role_id=args.get("role_id"), ttl_seconds=args.get("ttl_seconds"))
    elif tool_name == "loop_handoff":
        from tool_handoff import run
        return run(args["from_role"], args["to_role"], args["context_summary"],
                   project_root, artifacts=args.get("artifacts", []))
    elif tool_name == "loop_load_context":
        from tool_load_context import run
        return run(args["role_id"], complexity=args.get("complexity", 0.5))
    # v3.6 — canonical runtime controller
    elif tool_name in {"loop_onboard_project", "loop_propose_work_package", "loop_approve_and_execute", "loop_resume_execution"}:
        from loop_core.runtime_controller import ExecutionContext, RuntimeController
        controller = RuntimeController(project_root)
        try:
            if tool_name == "loop_onboard_project":
                snapshot = controller.onboard_project(
                    args.get("intent", ""), idempotency_key=args.get("idempotency_key")
                )
            elif tool_name == "loop_propose_work_package":
                snapshot = controller.create_work_package_proposal(
                    args["task_id"], args["gate_id"], args["title"], args["allowed_paths"],
                    non_goals=args.get("non_goals"), risk_flags=args.get("risk_flags"),
                )
            elif tool_name == "loop_approve_and_execute":
                snapshot = controller.approve_and_execute(
                    args["gate_id"], approval=args["approval"],
                    user_actor_id=args.get("user_actor_id", "user"),
                    idempotency_key=args.get("idempotency_key"),
                )
            else:
                snapshot = controller.resume_execution(ExecutionContext(
                    actor_id=args["actor_id"], role_id=args["role_id"],
                    caller_class=args["caller_class"], task_id=args["task_id"],
                    execution_id=args["execution_id"], session_id=args.get("session_id"),
                    capability_id=args.get("capability_id"),
                ))
            return {"ok": True, **snapshot.__dict__}
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:200]}

    if tool_name == "loop_dispatch_agents":
        project_root = args.get("project_root", ".")
        manifest = args.get("manifest", {})
        max_retries = args.get("max_retries", 2)
        try:
            from tools.mcp_agent_runtime import MCPAgentRuntime
            runtime = MCPAgentRuntime(agents_dir=Path(project_root) / "agents")
            result = runtime.dispatch_manifest(manifest, max_retries=max_retries)
            return {
                "manifest_id": result.manifest_id,
                "total": result.total,
                "completed": result.completed,
                "failed": result.failed,
                "results": [
                    {
                        "subagent_id": r.subagent_id,
                        "status": r.status,
                        "output": r.output,
                        "error": r.error,
                        "token_count": r.token_count,
                        "duration_ms": r.duration_ms,
                    }
                    for r in result.results
                ],
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    return {"error": f"unhandled tool: {tool_name}"}


def main():
    """MCP stdio 主循环——读取 JSON-RPC 请求，写回响应。"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle_request(request)
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
