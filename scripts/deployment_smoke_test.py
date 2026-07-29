"""
deployment_smoke_test.py — T-0069: 部署就绪验证框架

验证部署环境的完整性，包括：
1. 端口可达性检查
2. 关键接口响应验证
3. 配置文件一致性对比
4. 运行时健康检查
5. 部署方式可复现性检查

作为 S6-delivery 阶段的强制门禁之一。
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any


def check_port(host: str, port: int, timeout: float = 5.0) -> dict:
    """检查端口是否可达。"""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return {"host": host, "port": port, "reachable": True}
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return {"host": host, "port": port, "reachable": False, "error": str(e)}


def check_http_endpoint(url: str, method: str = "GET", expected_status: int = 200, 
                        timeout: float = 10.0, data: dict = None) -> dict:
    """检查 HTTP 端点是否返回预期状态码。"""
    try:
        req = urllib.request.Request(url, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
            req.data = json.dumps(data).encode("utf-8")
        resp = urllib.request.urlopen(req, timeout=timeout)
        body = resp.read().decode("utf-8")[:500]
        return {
            "url": url, "method": method, "status": resp.status,
            "expected": expected_status, "match": resp.status == expected_status,
            "body_preview": body,
        }
    except urllib.error.HTTPError as e:
        return {"url": url, "method": method, "status": e.code, 
                "expected": expected_status, "match": e.code == expected_status,
                "error": str(e)}
    except Exception as e:
        return {"url": url, "method": method, "status": 0, 
                "expected": expected_status, "match": False, "error": str(e)}


def check_config_consistency(dev_config: Path, deploy_config: Path) -> dict:
    """对比开发环境和部署环境的配置差异（仅对比存在的文件）。"""
    result = {"dev_exists": dev_config.exists(), "deploy_exists": deploy_config.exists(),
              "differences": [], "only_dev": [], "only_deploy": []}
    
    if not dev_config.exists() or not deploy_config.exists():
        return result
    
    try:
        dev = json.loads(dev_config.read_text(encoding="utf-8"))
        dep = json.loads(deploy_config.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception) as e:
        result["error"] = str(e)
        return result
    
    # Compare top-level keys
    dev_keys = set(dev.keys())
    dep_keys = set(dep.keys())
    result["only_dev"] = list(dev_keys - dep_keys)
    result["only_deploy"] = list(dep_keys - dev_keys)
    
    for key in dev_keys & dep_keys:
        if dev[key] != dep[key]:
            result["differences"].append({
                "key": key,
                "dev": str(dev[key])[:100],
                "deploy": str(dep[key])[:100],
            })
    
    return result


def check_deploy_reproducibility(project_root: Path) -> dict:
    """检查部署方式是否可复现（是否使用 Git 管理 + 是否有构建脚本）。"""
    is_git = (project_root / ".git").exists()
    has_dockerfile = (project_root / "Dockerfile").exists()
    has_build_script = (
        (project_root / "Makefile").exists() or
        (project_root / "scripts" / "build.sh").exists() or
        (project_root / "scripts" / "build.ps1").exists()
    )
    
    warnings = []
    if not is_git:
        warnings.append("项目不在 Git 仓库中——部署版本不可追溯")
    if not has_dockerfile and not has_build_script:
        warnings.append("无 Dockerfile 或构建脚本——部署过程不可复现")
    
    return {
        "is_git_repo": is_git,
        "has_dockerfile": has_dockerfile,
        "has_build_script": has_build_script,
        "reproducible": is_git and (has_dockerfile or has_build_script),
        "warnings": warnings,
    }


def run_smoke_tests(project_root: str, endpoints: list[dict] = None,
                    ports: list[dict] = None) -> dict:
    """执行完整的部署冒烟测试。
    
    Args:
        project_root: 项目根目录
        endpoints: [{"url": "...", "method": "GET", "expected": 200}, ...]
        ports: [{"host": "127.0.0.1", "port": 3000}, ...]
    
    Returns:
        {"passed": bool, "checks": [...], "summary": "..."}
    """
    root = Path(project_root)
    results = []
    all_passed = True
    
    # 1. Port checks
    if ports:
        for p in ports:
            r = check_port(p.get("host", "127.0.0.1"), p["port"])
            results.append({"check": "port", **r})
            if not r["reachable"]:
                all_passed = False
    
    # 2. Endpoint checks
    if endpoints:
        for ep in endpoints:
            r = check_http_endpoint(
                ep["url"], 
                method=ep.get("method", "GET"),
                expected_status=ep.get("expected", 200),
                data=ep.get("data"),
            )
            results.append({"check": "endpoint", **r})
            if not r["match"]:
                all_passed = False
    
    # 3. Deploy reproducibility
    repro = check_deploy_reproducibility(root)
    results.append({"check": "reproducibility", **repro})
    if not repro["reproducible"]:
        all_passed = False
    
    # 4. Config consistency (if deploy config exists)
    dev_config = root / ".zcode" / "config.json"
    deploy_config = root / "config.deploy.json"
    if deploy_config.exists():
        config = check_config_consistency(dev_config, deploy_config)
        results.append({"check": "config_consistency", **config})
        if config.get("differences"):
            all_passed = False
    
    summary = "ALL_PASSED" if all_passed else "SOME_FAILED"
    
    return {
        "passed": all_passed,
        "summary": summary,
        "total_checks": len(results),
        "failed": sum(1 for r in results if not r.get("reachable", r.get("match", r.get("reproducible", True)))),
        "checks": results,
    }


# CLI entry point
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Deployment smoke test")
    parser.add_argument("project_root", help="Project root directory")
    parser.add_argument("--endpoints", help="JSON file with endpoint definitions")
    parser.add_argument("--ports", help="JSON file with port definitions")
    parser.add_argument("--output", help="Output JSON file path")
    args = parser.parse_args()
    
    endpoints = []
    ports = []
    
    if args.endpoints:
        with open(args.endpoints) as f:
            endpoints = json.load(f)
    if args.ports:
        with open(args.ports) as f:
            ports = json.load(f)
    
    result = run_smoke_tests(args.project_root, endpoints=endpoints, ports=ports)
    
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["passed"] else 1)
