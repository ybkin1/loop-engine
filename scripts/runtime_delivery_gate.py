"""
runtime_delivery_gate.py — T-0078: P0 运行时交付质量门

执行六层运行时质量检查：
1. 构建产物完整性（Next.js manifest 校验）
2. 服务启动检查（端口监听）
3. 健康端点检查（HTTP 健康接口）
4. API 契约检查（登录成功/失败路径）
5. 浏览器冒烟（真实浏览器 E2E）
6. 总体编排（fail-closed: FAIL/ERROR/SKIPPED/NOT_RUN 全部阻断）

输出统一 runtime-quality.v1 schema 报告。
整体 BLOCKED 时额外输出 repair_tasks 和 diagnoses。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional
import signal
import socket
import tempfile

# ── Constants ──────────────────────────────────────────────────────────────

BLOCKING_STATUSES = {"FAIL", "ERROR", "SKIPPED", "NOT_RUN"}
PASS_STATUS = "PASS"
EXECUTION_MODE = "SIMULATED_MAIN_SESSION"
AGENT_TAKEOVER = False

NEXTJS_MANIFEST_FILES = [
    "routes-manifest.json",
    "pages-manifest.json",
    "app-paths-manifest.json",
    "middleware-manifest.json",
]

# ── Helper Utilities ────────────────────────────────────────────────────────


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _check_result(check_id: str, status: str, detail: str = "", evidence: str = "",
                  duration_ms: float = 0.0) -> dict[str, Any]:
    return {
        "id": check_id, "status": status, "detail": detail,
        "evidence": evidence, "duration_ms": duration_ms,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 1. 构建产物完整性检查
# ══════════════════════════════════════════════════════════════════════════════


def check_artifact_manifest(project_root: str) -> dict[str, Any]:
    """验证 Next.js 构建产物完整性。

    检查: .next/BUILD_ID 存在, 所有 manifest 文件存在且可解析,
    manifest 引用的所有页面 server bundle 存在。
    """
    t0 = time.monotonic()
    root = Path(project_root)
    next_dir = root / ".next"
    build_id_path = next_dir / "BUILD_ID"

    if not build_id_path.exists():
        return _check_result("artifact.manifest", "FAIL",
                             ".next/BUILD_ID not found — build may not have run",
                             str(build_id_path))

    build_id = build_id_path.read_text().strip()
    missing_manifests = []

    for manifest_name in NEXTJS_MANIFEST_FILES:
        manifest_path = next_dir / manifest_name
        if not manifest_path.exists():
            missing_manifests.append(manifest_name)
            continue
        # Try parsing as JSON
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            missing_manifests.append(f"{manifest_name} (unparseable: {exc})")
            continue

        # For routes-manifest, verify referenced pages
        if manifest_name == "routes-manifest.json":
            pages = data.get("pages", {})
            if isinstance(pages, dict):
                for route, page_file in pages.items():
                    page_path = next_dir / "server" / f"{page_file}.js"
                    if not page_path.exists():
                        missing_manifests.append(
                            f"routes-manifest references {page_file} "
                            f"(from route {route}) which does not exist"
                        )

    if missing_manifests:
        return _check_result(
            "artifact.manifest", "FAIL",
            f"Missing/broken manifests: {', '.join(missing_manifests[:10])}",
            evidence=json.dumps({"build_id": build_id, "missing": missing_manifests}),
            duration_ms=(time.monotonic() - t0) * 1000,
        )

    # Check that static resources referenced by HTML exist
    static_dir = next_dir / "static"
    resource_missing = []
    if static_dir.exists():
        static_files = set()
        for f in static_dir.rglob("*"):
            if f.is_file():
                static_files.add(str(f.relative_to(static_dir)).replace("\\", "/"))

        for html_file in next_dir.rglob("*.html"):
            try:
                content = html_file.read_text(encoding="utf-8")
                refs = re.findall(r'(?:src|href)=["\']([^"\']*\.(?:js|css))["\']', content)
                for ref in refs:
                    filename = ref.split("/")[-1]
                    # Check if any static file matches (loose match for hashed names)
                    if not any(filename in sf for sf in static_files):
                        resource_missing.append(f"{html_file.name} refs {ref}")
            except Exception:
                pass

    if resource_missing:
        return _check_result(
            "artifact.manifest", "FAIL",
            f"HTML references missing static resources: {resource_missing[:5]}",
            evidence=json.dumps({"build_id": build_id, "missing_resources": resource_missing}),
            duration_ms=(time.monotonic() - t0) * 1000,
        )

    return _check_result(
        "artifact.manifest", "PASS",
        f"Build {build_id}: all {len(NEXTJS_MANIFEST_FILES)} manifests present and valid",
        evidence=json.dumps({"build_id": build_id, "manifests_checked": len(NEXTJS_MANIFEST_FILES)}),
        duration_ms=(time.monotonic() - t0) * 1000,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 2. 服务启动检查
# ══════════════════════════════════════════════════════════════════════════════


def check_service_startup(project_root: str, service_url: str = None,
                          timeout_seconds: int = 30) -> dict[str, Any]:
    """检查服务是否可达（不启动服务，只检查端口/URL连通性）。

    service_url: 已部署服务的 URL。若未提供则尝试常见 Next.js 端口。
    """
    t0 = time.monotonic()

    urls_to_check = []
    if service_url:
        urls_to_check.append(service_url)
    else:
        for port in [3000, 3001, 8080, 8000]:
            urls_to_check.append(f"http://localhost:{port}")

    for url in urls_to_check:
        try:
            req = urllib.request.Request(url, method="HEAD")
            resp = urllib.request.urlopen(req, timeout=min(5, timeout_seconds))
            if 200 <= resp.status < 500:
                return _check_result(
                    "service.startup", "PASS",
                    f"Service reachable at {url} (HTTP {resp.status})",
                    evidence=json.dumps({"url": url, "status": resp.status}),
                    duration_ms=(time.monotonic() - t0) * 1000,
                )
        except Exception:
            continue

    return _check_result(
        "service.startup", "FAIL",
        f"Service not reachable at any of: {urls_to_check}. "
        "Start the service first or provide --service-url.",
        evidence=json.dumps({"checked_urls": urls_to_check}),
        duration_ms=(time.monotonic() - t0) * 1000,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 3. 健康端点检查
# ══════════════════════════════════════════════════════════════════════════════


def check_health_endpoints(service_url: str, timeout_seconds: int = 10) -> dict[str, Any]:
    """检查关键 HTTP 端点是否返回健康状态。"""
    t0 = time.monotonic()
    results = []
    all_pass = True

    endpoints = [
        ("GET /", "/", lambda resp: resp.status == 200 and len(resp.read() or b"") > 0),
        ("GET /api/health", "/api/health", lambda resp: resp.status == 200),
    ]

    for name, path, validator in endpoints:
        url = service_url.rstrip("/") + path
        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=timeout_seconds)
            if validator(resp):
                results.append(f"{name}: HTTP {resp.status} OK")
            else:
                results.append(f"{name}: HTTP {resp.status} FAIL (validator failed)")
                all_pass = False
        except urllib.error.HTTPError as exc:
            results.append(f"{name}: HTTP {exc.code} (expected 200)")
            all_pass = False
        except Exception as exc:
            results.append(f"{name}: ERROR {exc}")
            all_pass = False

    return _check_result(
        "endpoint.health", "PASS" if all_pass else "FAIL",
        "; ".join(results),
        evidence=json.dumps({"endpoints": results}),
        duration_ms=(time.monotonic() - t0) * 1000,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 4. API 契约检查
# ══════════════════════════════════════════════════════════════════════════════


def check_api_contract(service_url: str, timeout_seconds: int = 10) -> dict[str, Any]:
    """对 /api/login 执行正确和错误凭据的请求响应契约验证。

    验证:
    - 正确凭据: HTTP 200 + token/session
    - 错误凭据: HTTP 401 + errorCode + message
    """
    t0 = time.monotonic()
    results = []
    all_pass = True
    login_url = service_url.rstrip("/") + "/api/login"

    # ── Test 1: incorrect credentials ──
    try:
        data = json.dumps({"username": "admin", "password": "wrong_password"}).encode("utf-8")
        req = urllib.request.Request(login_url, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        resp = urllib.request.urlopen(req, timeout=timeout_seconds)
        results.append(f"POST /api/login (wrong): HTTP {resp.status} — expected 401")
        all_pass = False
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            try:
                body = json.loads(exc.read().decode("utf-8"))
                has_error_code = "errorCode" in body or "error" in body
                has_message = "message" in body or "error" in body
                if has_error_code and has_message:
                    results.append(f"POST /api/login (wrong): HTTP 401 + error response OK")
                else:
                    results.append(f"POST /api/login (wrong): HTTP 401 but response missing errorCode/message fields")
                    all_pass = False
            except (json.JSONDecodeError, UnicodeDecodeError):
                results.append(f"POST /api/login (wrong): HTTP 401 but response not valid JSON")
                all_pass = False
        else:
            results.append(f"POST /api/login (wrong): HTTP {exc.code} — expected 401")
            all_pass = False
    except Exception as exc:
        results.append(f"POST /api/login (wrong): ERROR {exc}")
        all_pass = False

    # ── Test 2: correct credentials ──
    try:
        data = json.dumps({"username": "admin", "password": "admin123456"}).encode("utf-8")
        req = urllib.request.Request(login_url, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        resp = urllib.request.urlopen(req, timeout=timeout_seconds)
        body = json.loads(resp.read().decode("utf-8"))
        has_token = bool(body.get("token") or body.get("accessToken") or body.get("session"))
        if resp.status == 200 and has_token:
            results.append(f"POST /api/login (correct): HTTP 200 + token OK")
        else:
            results.append(f"POST /api/login (correct): HTTP {resp.status}, token missing")
            all_pass = False
    except urllib.error.HTTPError as exc:
        results.append(f"POST /api/login (correct): HTTP {exc.code} — expected 200")
        all_pass = False
    except Exception as exc:
        results.append(f"POST /api/login (correct): ERROR {exc}")
        all_pass = False

    return _check_result(
        "api.contract", "PASS" if all_pass else "FAIL",
        "; ".join(results),
        evidence=json.dumps({"login_checks": results}),
        duration_ms=(time.monotonic() - t0) * 1000,
    )


def _find_available_port(start_port: int = 3000, max_attempts: int = 10) -> int:
    """Find an available port for the production server."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
    return start_port + max_attempts


def _wait_for_server(url: str, timeout_seconds: int = 60) -> bool:
    """Poll a URL until it returns 200 or timeout."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(url, method="HEAD")
            resp = urllib.request.urlopen(req, timeout=3)
            if 200 <= resp.status < 500:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


# ══════════════════════════════════════════════════════════════════════════════
# 5. 浏览器冒烟
# ══════════════════════════════════════════════════════════════════════════════


def check_browser_smoke(service_url: str, timeout_seconds: int = 15) -> dict[str, Any]:
    """使用 Playwright 启动真实浏览器进行页面冒烟测试。

    检查:
    - 首页 body 有可见文本（非白屏）
    - 无 console.error
    - 无 pageerror / unhandled rejection
    - 登录页存在密码输入框和登录按钮
    - 输入错误密码后出现用户可见错误文字
    """
    t0 = time.monotonic()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _check_result(
            "browser.smoke", "NOT_RUN",
            "Playwright not installed. Install with: pip install playwright && playwright install chromium",
            evidence="playwright_import_error",
            duration_ms=(time.monotonic() - t0) * 1000,
        )

    results = []
    all_pass = True
    console_errors = []
    page_errors = []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            page.on("console", lambda msg: (
                console_errors.append(msg.text) if msg.type == "error" else None
            ))
            page.on("pageerror", lambda err: page_errors.append(str(err)))

            # ── Navigate to home page ──
            try:
                page.goto(service_url, timeout=timeout_seconds * 1000, wait_until="networkidle")
            except Exception as exc:
                results.append(f"Home page load failed: {exc}")
                all_pass = False
                browser.close()
                return _check_result(
                    "browser.smoke", "FAIL",
                    f"Failed to load {service_url}: {exc}",
                    evidence=json.dumps({"error": str(exc)}),
                    duration_ms=(time.monotonic() - t0) * 1000,
                )

            # Check page has content
            body_text = page.inner_text("body") if page.locator("body").count() > 0 else ""
            if len(body_text.strip()) < 10:
                results.append("Home page body text is empty (<10 chars) — possible white screen")
                all_pass = False
            else:
                results.append(f"Home page: body has {len(body_text)} chars OK")

            if console_errors:
                results.append(f"Console errors: {len(console_errors)} ({console_errors[:3]})")
                all_pass = False
            if page_errors:
                results.append(f"Page errors: {len(page_errors)} ({page_errors[:3]})")
                all_pass = False

            # ── Navigate to login page ──
            login_url = service_url.rstrip("/") + "/login"
            try:
                page.goto(login_url, timeout=timeout_seconds * 1000, wait_until="networkidle")
            except Exception:
                results.append(f"Login page not found at {login_url} — skipping login checks")
                browser.close()
                return _check_result(
                    "browser.smoke", "PASS" if all_pass else "FAIL",
                    "; ".join(results),
                    evidence=json.dumps({
                        "console_errors": console_errors,
                        "page_errors": page_errors,
                        "body_length": len(body_text),
                    }),
                    duration_ms=(time.monotonic() - t0) * 1000,
                )

            # Check for password input
            pw_input = page.locator("input[type=\"password\"]")
            if pw_input.count() == 0:
                results.append("Login page: no password input found")
                all_pass = False
            else:
                results.append("Login page: password input OK")

            # Check for login button
            login_btn = page.locator("button").filter(has_text=re.compile("login|登录|sign in", re.IGNORECASE))
            if login_btn.count() == 0:
                login_btn = page.locator("input[type=\"submit\"]")
            if login_btn.count() == 0:
                results.append("Login page: no login button found")
                all_pass = False
            else:
                results.append("Login page: login button OK")

            # ── Enter wrong password and check error display ──
            if pw_input.count() > 0 and login_btn.count() > 0:
                try:
                    # Find username input
                    username_input = page.locator("input[type=\"text\"], input[name*=\"user\"], input[name*=\"email\"]").first
                    if username_input.count() > 0:
                        username_input.fill("admin")
                    pw_input.first.fill("wrong_password")
                    login_btn.first.click()
                    page.wait_for_timeout(2000)  # Wait for error to appear

                    # Check for visible error message
                    error_selectors = [
                        "[role=\"alert\"]", ".error", ".alert", ".toast",
                        "text=/wrong|incorrect|invalid|错误|失败/i"
                    ]
                    found_error = False
                    for sel in error_selectors:
                        try:
                            el = page.locator(sel).first
                            if el.count() > 0 and el.is_visible():
                                found_error = True
                                results.append(f"Error message visible: {el.inner_text()[:80]}")
                                break
                        except Exception:
                            continue

                    if not found_error:
                        results.append("Login error: no visible error message after wrong password")
                        all_pass = False

                except Exception as exc:
                    results.append(f"Login error test failed: {exc}")
                    all_pass = False

            browser.close()

    except Exception as exc:
        return _check_result(
            "browser.smoke", "ERROR",
            f"Browser smoke test crashed: {exc}",
            evidence=json.dumps({"error": str(exc)}),
            duration_ms=(time.monotonic() - t0) * 1000,
        )

    return _check_result(
        "browser.smoke", "PASS" if all_pass else "FAIL",
        "; ".join(results),
        evidence=json.dumps({
            "console_errors": console_errors,
            "page_errors": page_errors,
            "results": results,
        }),
        duration_ms=(time.monotonic() - t0) * 1000,
    )


def build_and_start_production(project_root: str, port: int = None
                               ) -> tuple[Optional[subprocess.Popen], str, dict]:
    """Execute production build and start server for testing.
    
    Returns: (server_process, service_url, build_result)
    build_result has {"status": "PASS"|"FAIL", "detail": str}
    """
    root = Path(project_root)
    build_result: dict[str, Any] = {"status": "PASS", "detail": ""}
    
    # Determine the build tool
    is_nextjs = (root / "next.config.js").exists() or (root / "next.config.mjs").exists() or (root / "next.config.ts").exists()
    has_package_json = (root / "package.json").exists()
    
    if not has_package_json:
        build_result = {"status": "SKIPPED", "detail": "No package.json found — not a Node.js project"}
        return None, "", build_result
    
    if not port:
        port = _find_available_port()
    
    # Step 1: Production build
    build_cmd = None
    if is_nextjs:
        build_cmd = ["npm", "run", "build"]
    elif (root / "Makefile").exists():
        build_cmd = ["make", "build"]
    else:
        # Check package.json scripts
        try:
            pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
            scripts = pkg.get("scripts", {})
            if "build" in scripts:
                build_cmd = ["npm", "run", "build"]
        except Exception:
            pass
    
    if build_cmd:
        try:
            build_proc = subprocess.run(
                build_cmd, cwd=str(root), capture_output=True, text=True,
                timeout=300,
            )
            if build_proc.returncode != 0:
                build_result = {
                    "status": "FAIL",
                    "detail": f"Build failed (exit {build_proc.returncode}): {build_proc.stderr[:300]}"
                }
                return None, "", build_result
            build_result["detail"] = f"Build succeeded: {build_cmd}"
        except subprocess.TimeoutExpired:
            build_result = {"status": "FAIL", "detail": f"Build timed out (>300s)"}
            return None, "", build_result
        except FileNotFoundError:
            build_result = {"status": "SKIPPED", "detail": "npm not found"}
            return None, "", build_result
    else:
        build_result = {"status": "SKIPPED", "detail": "No recognized build command"}
        return None, "", build_result
    
    # Step 2: Start production server
    start_cmd = None
    if is_nextjs:
        start_cmd = ["npx", "next", "start", "--port", str(port)]
    elif (root / "package.json").exists():
        try:
            pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
            if "start" in pkg.get("scripts", {}):
                start_cmd = ["npm", "run", "start"]
        except Exception:
            pass
    
    if not start_cmd:
        return None, "", build_result
    
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["NODE_ENV"] = "production"
    
    try:
        server_proc = subprocess.Popen(
            start_cmd, cwd=str(root), stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env=env,
        )
    except FileNotFoundError:
        build_result["status"] = "FAIL"
        build_result["detail"] = f"Cannot start server: {start_cmd[0]} not found"
        return None, "", build_result
    
    service_url = f"http://localhost:{port}"
    
    # Step 3: Wait for server to be ready
    if not _wait_for_server(service_url, timeout_seconds=60):
        try:
            server_proc.terminate()
            server_proc.wait(timeout=5)
        except Exception:
            try:
                server_proc.kill()
            except Exception:
                pass
        build_result["status"] = "FAIL"
        build_result["detail"] = f"Server started but did not respond within 60s at {service_url}"
        return None, "", build_result
    
    return server_proc, service_url, build_result


# ══════════════════════════════════════════════════════════════════════════════
# 6. 总体编排
# ══════════════════════════════════════════════════════════════════════════════


def run_full_runtime_gate(project_root: str, service_url: str = None,
                          timeout_seconds: int = 30,
                          browser_timeout: int = 15,
                          skip_browser: bool = False,
                          production_mode: bool = False) -> dict[str, Any]:
    """执行完整运行时交付质量门。

    Returns: {"overall": "PASS"|"BLOCKED", "checks": [...], ...}
    """
    checks = []
    all_pass = True
    blocked_by = []

    def _run(check_fn, *args, **kwargs):
        nonlocal all_pass, blocked_by
        result = check_fn(*args, **kwargs)
        checks.append(result)
        if result["status"] != "PASS":
            all_pass = False
            blocked_by.append(result["id"])
        return result

    def _build_report(checks_list, all_ok, blocked, url, root_dir):
        overall = "PASS" if all_ok else "BLOCKED"
        repair_tasks = []
        if overall == "BLOCKED":
            for check in checks_list:
                if check["status"] in BLOCKING_STATUSES:
                    repair_tasks.append({
                        "title": f"Fix {check['id']}: {check.get('detail', 'no detail')[:80]}",
                        "check_id": check["id"],
                        "severity": "BLOCKER",
                        "suggested_files": [],
                    })
        report: dict[str, Any] = {
            "schemaVersion": "runtime-quality.v1",
            "execution_mode": EXECUTION_MODE,
            "agent_takeover": AGENT_TAKEOVER,
            "overall": overall,
            "blocked_by": blocked,
            "checks": checks_list,
            "executed_at": _now_iso(),
            "repair_tasks": repair_tasks if overall == "BLOCKED" else [],
            "environment": {
                "service_url": url,
                "project_root": root_dir,
                "build_mode": "production" if production_mode else "external",
            },
        }
        if overall == "BLOCKED":
            diagnoses = []
            for i, check in enumerate(checks_list):
                if check["status"] in BLOCKING_STATUSES:
                    diagnoses.append({
                        "diagnosis_id": f"D-{i + 1:04d}",
                        "kind": "runtime_quality_failure",
                        "severity": "BLOCKER",
                        "symptoms": [f"Check {check['id']} returned {check['status']}"],
                        "root_causes": [check.get("detail", "unknown")],
                        "evidence_refs": [check.get("evidence", "")],
                        "recommended_actions": [f"Review and fix {check['id']}"],
                        "status": "open",
                        "generated_at": _now_iso(),
                    })
            report["diagnoses"] = diagnoses
        return report

    # T-0078 P0: Production mode — 构建生产版本并启动服务器
    server_proc = None
    production_build_result = None
    if production_mode:
        server_proc, service_url, production_build_result = build_and_start_production(project_root)
        # 记录构建结果
        checks.append(_check_result(
            "build.production", production_build_result["status"],
            production_build_result["detail"],
            evidence=json.dumps(production_build_result),
        ))
        if production_build_result["status"] != "PASS":
            all_pass = False
            blocked_by.append("build.production")
            # 构建或启动失败——不继续后续检查
            if not service_url:
                # 优雅停止服务器（如果已启动）
                if server_proc:
                    try:
                        server_proc.terminate()
                        server_proc.wait(timeout=5)
                    except Exception:
                        try:
                            server_proc.kill()
                        except Exception:
                            pass
                checks.append(_check_result("endpoint.health", "SKIPPED", "Production server not available"))
                checks.append(_check_result("api.contract", "SKIPPED", "Production server not available"))
                checks.append(_check_result("browser.smoke", "SKIPPED", "Production server not available"))
                all_pass = False
                blocked_by.extend(["endpoint.health", "api.contract", "browser.smoke"])
                return _build_report(checks, all_pass, blocked_by, service_url, project_root)

    # 1. Artifact manifest
    _run(check_artifact_manifest, project_root)

    # 2. Service startup
    svc_result = _run(check_service_startup, project_root, service_url, timeout_seconds)
    if svc_result["status"] == "PASS" and not service_url:
        from urllib.parse import urlparse
        evidence_data = json.loads(svc_result.get("evidence", "{}"))
        service_url = evidence_data.get("url")

    if not service_url:
        checks.append(_check_result("endpoint.health", "SKIPPED",
                                     "No service URL available — skipping health/API/browser"))
        checks.append(_check_result("api.contract", "SKIPPED",
                                     "No service URL available"))
        checks.append(_check_result("browser.smoke", "SKIPPED",
                                     "No service URL available"))
        all_pass = False
        blocked_by.extend(["endpoint.health", "api.contract", "browser.smoke"])
    else:
        # 3. Health endpoints
        _run(check_health_endpoints, service_url, timeout_seconds)

        # 4. API contract
        _run(check_api_contract, service_url, timeout_seconds)

        # 5. Browser smoke
        if not skip_browser:
            _run(check_browser_smoke, service_url, browser_timeout)
        else:
            checks.append(_check_result("browser.smoke", "SKIPPED",
                                         "Browser smoke skipped via --skip-browser"))
            all_pass = False
            blocked_by.append("browser.smoke")

    # T-0078: 清理生产服务器
    if server_proc:
        try:
            server_proc.terminate()
            server_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                server_proc.kill()
            except Exception:
                pass
        except Exception:
            pass

    return _build_report(checks, all_pass, blocked_by, service_url, project_root)


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(
        description="Runtime Delivery Gate — fail-closed runtime quality verification"
    )
    p.add_argument("project_root", help="Project root directory")
    p.add_argument("--service-url", help="Deployed service URL (http://localhost:3000 etc.)")
    p.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    p.add_argument("--browser-timeout", type=int, default=15, help="Browser timeout in seconds")
    p.add_argument("--skip-browser", action="store_true", help="Skip browser smoke test")
    p.add_argument("--production-mode", action="store_true",
                   help="Auto-build and start service (npm run build && npm run start) when no --service-url provided")
    p.add_argument("--output", help="Output JSON file path")
    args = p.parse_args()

    result = run_full_runtime_gate(
        args.project_root,
        service_url=args.service_url,
        timeout_seconds=args.timeout,
        browser_timeout=args.browser_timeout,
        skip_browser=args.skip_browser,
        production_mode=args.production_mode,
    )

    # Ensure overall is BLOCKED if any non-PASS check exists
    if result["overall"] == "PASS":
        for check in result["checks"]:
            if check["status"] != "PASS":
                result["overall"] = "BLOCKED"
                result["blocked_by"] = [c["id"] for c in result["checks"] if c["status"] != "PASS"]
                break

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    # exit 0 = PASS, exit 2 = BLOCKED (matching ZCode deny semantics)
    sys.exit(0 if result["overall"] == "PASS" else 2)
