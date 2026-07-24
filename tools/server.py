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
                "verify": {"type": "boolean", "description": "true=验证完整性, false=追加条目"}
            },
            "required": ["event", "actor"]
        }
    }
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
