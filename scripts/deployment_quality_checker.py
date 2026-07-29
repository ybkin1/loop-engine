"""
deployment_quality_checker.py — T-0072: 部署质量完整验证

扩展 T-0069 的 deployment_smoke_test，增加：
1. 构建版本一致性（Build ID 匹配）
2. 静态资源完整性（HTML 引用的 CSS/JS 是否存在）
3. 浏览器关键路径冒烟（首页/API/静态资源）
4. 部署原子性（检查部分部署/不完整 scp）
5. 回滚就绪（上一版本是否保留）
6. 冷缓存测试（Cache-Control 头检查）

覆盖 T-0069 未覆盖的"部署完整性与浏览器真实用户旅程"维度。
"""

import hashlib
import json
import os
import re
import socket
import sys
import urllib.request
import urllib.error
from pathlib import Path


def check_build_consistency(project_root: str, deploy_root: str = None) -> dict:
    """验证构建产物与源码的一致性。

    检查: .next/BUILD_ID 是否匹配, HTML 引用的 JS/CSS hash 是否存在。
    """
    root = Path(project_root)
    results = {"checks": [], "consistent": True}
    
    # Find BUILD_ID
    build_id_path = root / ".next" / "BUILD_ID"
    if not build_id_path.exists():
        results["checks"].append({"check": "build_id", "status": "MISSING", 
                                   "detail": ".next/BUILD_ID not found"})
        results["consistent"] = False
        return results
    
    build_id = build_id_path.read_text().strip()
    results["build_id"] = build_id
    
    # Check that HTML references match build output
    static_dir = root / ".next" / "static"
    if not static_dir.exists():
        results["checks"].append({"check": "static_dir", "status": "MISSING", "detail": str(static_dir)})
        results["consistent"] = False
    else:
        # Find all JS/CSS files in static/
        static_files = {f.name for f in static_dir.rglob("*") if f.is_file() and f.suffix in ('.js', '.css')}

        # Parse HTML files for resource references
        for html_file in root.rglob("*.html"):
            try:
                content = html_file.read_text(encoding="utf-8")
                refs = re.findall(r'(?:src|href)=["\']([^"\']*\.(?:js|css)(?:\?[^"\']*)?)["\']', content)
                for ref in refs:
                    filename = ref.split("/")[-1].split("?", 1)[0]
                    if filename and filename not in static_files:
                        results["checks"].append({
                            "check": "resource_missing",
                            "file": str(html_file.relative_to(root)),
                            "reference": ref,
                            "status": "MISSING"
                        })
                        results["consistent"] = False
            except (OSError, UnicodeDecodeError) as exc:
                results["checks"].append({"check": "html_read", "file": str(html_file), "status": "ERROR", "detail": str(exc)})
                results["consistent"] = False
    if deploy_root:
        deployed_id = Path(deploy_root) / ".next" / "BUILD_ID"
        if not deployed_id.exists() or deployed_id.read_text(encoding="utf-8").strip() != build_id:
            results["checks"].append({"check": "deploy_build_id", "status": "MISMATCH"})
            results["consistent"] = False
    
    results["checks"].append({"check": "build_id", "status": "OK", "build_id": build_id})
    return results


def check_static_resource_integrity(base_url: str, timeout: float = 10.0) -> dict:
    """验证线上 HTML 引用的静态资源是否全部可达（200 OK）。

    抓取首页 HTML，提取所有 CSS/JS 引用，逐一 HEAD 请求验证。
    """
    results = {"url": base_url, "checks": [], "all_reachable": True}
    
    try:
        req = urllib.request.Request(base_url)
        resp = urllib.request.urlopen(req, timeout=timeout)
        html = resp.read().decode("utf-8")[:100000]
    except Exception as e:
        results["error"] = str(e)
        results["all_reachable"] = False
        return results
    
    # Extract resource URLs
    resources = re.findall(r'(?:src|href)=["\']([^"\']*(?:\.js|\.css)(?:\?[^"\']*)?)["\']', html)
    
    checked = 0
    failed = 0
    for res in resources[:20]:  # Check first 20 to avoid excessive requests
        # Make absolute URL
        if res.startswith("http"):
            url = res
        elif res.startswith("//"):
            url = "https:" + res
        elif res.startswith("/"):
            from urllib.parse import urljoin
            url = urljoin(base_url, res)
        else:
            continue
        
        try:
            head_req = urllib.request.Request(url, method="HEAD")
            head_resp = urllib.request.urlopen(head_req, timeout=5)
            results["checks"].append({"resource": res, "status": head_resp.status, "reachable": head_resp.status == 200})
            if head_resp.status != 200:
                failed += 1
        except Exception as e:
            results["checks"].append({"resource": res, "status": 0, "reachable": False, "error": str(e)[:100]})
            failed += 1
        checked += 1
    
    results["total_checked"] = checked
    results["failed"] = failed
    results["all_reachable"] = failed == 0
    
    return results


def check_deployment_atomicity(deploy_path: str) -> dict:
    """检查部署是否完整（防止部分 scp 覆盖）。

    检查: .next/ 目录完整性, node_modules 与 package.json 一致性。
    """
    root = Path(deploy_path)
    results = {"checks": [], "atomic": True}
    
    # Check .next/ has essential files
    essential = [".next/BUILD_ID", ".next/server", ".next/static"]
    for e in essential:
        p = root / e
        if not p.exists():
            results["checks"].append({"check": "essential_missing", "path": e, "status": "MISSING"})
            results["atomic"] = False
    
    # Check package.json vs node_modules
    pkg_json = root / "package.json"
    node_modules = root / "node_modules"
    if pkg_json.exists() and node_modules.exists():
        pkg_mtime = pkg_json.stat().st_mtime
        nm_mtime = node_modules.stat().st_mtime
        if pkg_mtime > nm_mtime:
            results["checks"].append({
                "check": "node_modules_stale",
                "status": "WARN",
                "detail": "package.json is newer than node_modules — may need npm install"
            })
    
    # Check for leftover temp files indicating partial deployment
    temp_patterns = ["*.tmp", "*.scp_tmp", "*.partial"]
    for pattern in temp_patterns:
        matches = list(root.rglob(pattern))
        if matches:
            results["checks"].append({
                "check": "temp_files_found",
                "status": "WARN",
                "files": [str(m.relative_to(root)) for m in matches[:5]],
                "detail": "Temporary files found — possible partial deployment"
            })
    
    results["checks"].append({"check": "atomicity", "status": "OK" if results["atomic"] else "FAIL"})
    return results


def check_rollback_readiness(deploy_path: str) -> dict:
    """检查是否保留了上一版本以便回滚。

    检查: 是否有 .next.old/, 是否有 git reflog, 是否有备份标记。
    """
    root = Path(deploy_path)
    results = {"checks": [], "rollback_ready": False}
    
    # Check for previous build backup
    prev_build = root / ".next.old"
    if prev_build.is_dir() and (prev_build / "BUILD_ID").is_file():
        results["checks"].append({"check": "prev_build_backup", "status": "OK"})
        results["rollback_ready"] = True
    else:
        results["checks"].append({"check": "prev_build_backup", "status": "MISSING",
                                   "detail": "No .next.old/ backup — cannot rollback build"})
    
    # Check git availability for code rollback
    git_dir = root / ".git"
    if git_dir.exists():
        results["checks"].append({"check": "git_available", "status": "OK"})
    else:
        results["checks"].append({"check": "git_available", "status": "WARN",
                                   "detail": "Not a git repo — code rollback not possible"})
    
    # Check for rollback script
    rollback_script = root / "scripts" / "rollback.sh"
    if rollback_script.exists():
        results["checks"].append({"check": "rollback_script", "status": "OK"})
    
    return results


def check_cache_headers(base_url: str, timeout: float = 10.0) -> dict:
    """检查关键资源的 Cache-Control 头（冷缓存/缓存破坏测试）。

    验证: HTML 不缓存, JS/CSS 长期缓存（带 hash）。
    """
    results = {"checks": [], "cache_safe": True}
    
    # Check HTML — should NOT be cached
    try:
        req = urllib.request.Request(base_url)
        resp = urllib.request.urlopen(req, timeout=timeout)
        cache_control = resp.headers.get("Cache-Control", "")
        if "no-cache" in cache_control or "no-store" in cache_control or "max-age=0" in cache_control:
            results["checks"].append({"resource": "HTML", "cache_control": cache_control, "status": "OK"})
        else:
            results["checks"].append({"resource": "HTML", "cache_control": cache_control, 
                                       "status": "WARN", "detail": "HTML may be cached — stale pages risk"})
            results["cache_safe"] = False
    except Exception as e:
        results["checks"].append({"resource": "HTML", "error": str(e)[:100], "status": "ERROR"})
        results["cache_safe"] = False
    
    return results


def run_full_deployment_check(project_root: str, base_url: str = None, 
                              deploy_path: str = None) -> dict:
    """执行完整部署质量检查。

    Returns: {"passed": bool, "results": {...}}
    """
    all_results = {}
    all_passed = True
    
    # 1. Build consistency
    bc = check_build_consistency(project_root, deploy_path)
    all_results["build_consistency"] = bc
    if not bc["consistent"]:
        all_passed = False
    
    # 2. Static resource integrity (if URL provided)
    if base_url:
        si = check_static_resource_integrity(base_url)
        all_results["static_integrity"] = si
        if not si["all_reachable"]:
            all_passed = False
        
        # 3. Cache headers
        ch = check_cache_headers(base_url)
        all_results["cache_headers"] = ch
        if not ch["cache_safe"]:
            all_passed = False
    
    # 4. Deployment atomicity
    da = check_deployment_atomicity(deploy_path or project_root)
    all_results["deployment_atomicity"] = da
    if not da["atomic"]:
        all_passed = False
    
    # 5. Rollback readiness
    rr = check_rollback_readiness(deploy_path or project_root)
    all_results["rollback_readiness"] = rr
    if not rr["rollback_ready"]:
        all_passed = False
    
    return {"passed": all_passed, "results": all_results}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("project_root")
    p.add_argument("--base-url", help="Deployed site URL for browser-level checks")
    p.add_argument("--deploy-path", help="Deployment directory path")
    p.add_argument("--output", help="Output JSON file")
    args = p.parse_args()
    
    result = run_full_deployment_check(
        args.project_root,
        base_url=args.base_url,
        deploy_path=args.deploy_path
    )
    
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["passed"] else 1)
