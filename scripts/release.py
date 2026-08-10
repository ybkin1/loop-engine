#!/usr/bin/env python3
"""
release.py — D8 发布/产物体系（T-0098，StaffDeck D8 对标）。

子命令:
    check     质量门前置：validate_state（真实校验器）+ compile + guard 健康
              + SLO 门禁 + 关键测试子集（test_version_consistency +
              test_loop_core）。任一失败 → 退出码 1 阻断。check 支持 idle
              稳态运行：validate_state 的 rc=3（NO_ACTIVE_TASK 合法阻塞态，
              无活动任务）视为通过并标注，不阻断。
    build     构建 wheel + sdist 到 dist/（python -m build；构建工具缺失 → 明确报错）。
    manifest  生成产物清单 dist/release-manifest.json + dist/SHA256SUMS
              （产物名 / sha256 / size / git_commit / 时间戳；sha256 可复验）。
    release   check + build + manifest + release 证据落盘
              （.ai/evidence/release/<version>/ 三件套）。
    smoke     临时 venv（tempfile）→ pip install dist/*.whl → import loop_engine/loop_core 验证。
    bump      版本同步机制（F-03/T-0100）：`bump --to <version>` 原子更新
              pyproject.toml + CHANGELOG.md 头部 + 全部版本载体
              （loop_core/__init__.py、src/loop_engine/__init__.py、README.md、
              docs/06-delivery.md、.zcode-plugin/plugin.json、
              .ai/version-manifest.yaml 投影）。提交流程约定：**先 bump 再提交**
              —— 提交 subject 中的版本号必须与 pyproject 一致（version_sync 检查）。

通用:
    --dry-run  只打印计划，不执行、不落盘。

设计要点（对齐 D8 对标 + 项目既有约束语义）:
    - pyproject.toml 是版本的唯一事实来源（test_version_consistency 同源）。
    - check 是 release 的前置质量门：失败即阻断（fail-closed），不生成任何证据。
    - release 证据中的 release-decision.request.json 仅为"候选"（status=requested）；
      真实 GO/NOGO 由用户 / delivery-manager 另行决策（hook 门禁只认
      release_decision.json 的 GO / 带 owners+deadline 的 CONDITIONAL_GO）。
    - 本脚本不执行真实发布/上传。

退出码: 0 成功；1 门禁失败 / 构建失败 / 环境不可用；2 用法错误（argparse）。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# CLI 直跑（python scripts/release.py）时确保 loop_core / 项目包可导入
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

VERSION_RE = re.compile(r"\bv?(\d+\.\d+\.\d+)\b")
PYPROJECT_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)
VALIDATE_STATE_SCRIPT = ".zcode/tools/validate_state.py"
VALIDATE_STATE_TIMEOUT = 120  # 秒；真实校验器含连续性/角色合同检查，超时 fail-closed
COMPILE_DIRS = ("loop_core", "src", "scripts", "hooks", "tools")
KEY_TESTS = ("tests/test_version_consistency.py", "tests/test_loop_core.py")
MANIFEST_NAME = "release-manifest.json"
SHA256SUMS_NAME = "SHA256SUMS"
DECISION_REQUEST_NAME = "release-decision.request.json"


# ── 版本 ────────────────────────────────────────────────────────────────

def load_version(root: Path) -> str:
    """pyproject.toml 是版本的唯一事实来源。"""
    content = (root / "pyproject.toml").read_text(encoding="utf-8")
    m = PYPROJECT_VERSION_RE.search(content)
    if not m:
        raise ValueError("pyproject.toml 中找不到 version 字段")
    return m.group(1)


def git_head_version(root: Path) -> str | None:
    """从 git HEAD 提交信息提取版本（无 tag 环境用提交信息作为版本来源）。"""
    proc = subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        cwd=str(root), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None
    m = VERSION_RE.search(proc.stdout.strip())
    return m.group(1) if m else None


def git_head_commit(root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(root), capture_output=True, text=True,
    )
    full = proc.stdout.strip() if proc.returncode == 0 else "unknown"
    return f"{full[:12]}" if full != "unknown" else full


# ── bump：版本同步机制（F-03/T-0100）───────────────────────────────────
# 提交流程约定：先 bump 再提交 —— bump 更新 pyproject/CHANGELOG/载体后，
# 提交 subject 使用同一版本号，version_sync 步骤（与 git HEAD 对齐，
# fail-closed）即通过。本机制不改动 version_sync 的判定语义。

STRICT_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _atomic_write(path: Path, content: str) -> None:
    """原子写：同目录临时文件 + os.replace（Windows 上 os.replace 同卷原子）。

    写失败时不留下半成品：临时文件被清理，目标文件保持原内容。
    """
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def _update_pyproject(content: str, version: str) -> str:
    new, n = PYPROJECT_VERSION_RE.subn(f'version = "{version}"', content, count=1)
    if n != 1:
        raise ValueError("pyproject.toml 中找不到 version 字段")
    return new


def _update_init_version(content: str, version: str) -> str:
    new, n = re.subn(r'(__version__\s*=\s*)"[^"]+"', rf'\g<1>"{version}"', content, count=1)
    if n != 1:
        raise ValueError("载体中找不到 __version__ 赋值")
    return new


def _update_readme_version(content: str, version: str) -> str:
    new, n = re.subn(r'\*\*v?\d+\.\d+\.\d+\*\*', f"**v{version}**", content, count=1)
    if n != 1:
        raise ValueError("README.md 中找不到版本行（**vX.Y.Z**）")
    return new


def _update_delivery_doc_version(content: str, version: str) -> str:
    """docs/06-delivery.md：更新头部版本行与『版本号』表格行（当前交付版本）。"""
    new = re.sub(r"> Loop Engine v\d+\.\d+\.\d+", f"> Loop Engine v{version}", content, count=1)
    new, n = re.subn(r"\|\s*版本号\s*\|\s*v\d+\.\d+\.\d+\s*\|",
                     f"| 版本号 | v{version} |", new, count=1)
    if n != 1:
        raise ValueError("docs/06-delivery.md 中找不到『版本号』表格行")
    return new


def _update_plugin_json_version(content: str, version: str) -> str:
    new, n = re.subn(
        r'("version"\s*:\s*)"[^"]+"', rf'\g<1>"{version}"', content, count=1
    )
    if n != 1:
        raise ValueError(".zcode-plugin/plugin.json 中找不到 version 字段")
    return new


def _update_version_manifest(content: str, version: str) -> str:
    """更新 .ai/version-manifest.yaml 的投影字段（历史快照保持不动）。"""
    out = content
    for key in ("project_release_version", "core_protocol_version", "plugin_version"):
        pattern = re.compile(rf"^{key}:\s*\"[^\"]*\"", re.MULTILINE)
        out, n = pattern.subn(f'{key}: "{version}"', out, count=1)
        if n != 1:
            raise ValueError(f"version-manifest.yaml 中找不到 {key} 字段")
    # consistency_check 块：仅更新版本值，历史快照（historical_snapshots）不动
    out, n = re.subn(
        rf"^(\s*(?:pyproject_toml|readme_md|loop_core_init|src_loop_engine_init|"
        rf"docs_06_delivery|plugin_json):\s*)\"[^\"]*\"",
        rf'\g<1>"{version}"',
        out, flags=re.MULTILINE,
    )
    if n == 0:
        raise ValueError("version-manifest.yaml 中找不到 consistency_check 版本值")
    return out


def _update_changelog(content: str, version: str, title: str = "") -> str:
    """CHANGELOG.md 头部新增版本条目（保留现有格式风格，降序在前）。

    标题缺省时使用通用说明；调用方可事后补充条目正文（heading 格式不变，
    test_version_consistency 只认第一个 `## vX.Y.Z` 与 pyproject 一致）。
    """
    heading_title = title or "版本同步（release.py bump 子命令）"
    today = datetime.now(timezone.utc).date().isoformat()
    entry = (
        f"## v{version} ({today}) — {heading_title}\n"
        f"\n"
        f"### Changed ({heading_title})\n"
        f"- 版本同步：release.py bump 更新 pyproject/CHANGELOG/版本载体（原子写）；"
        f"提交流程约定：先 bump 再提交（版本与 git HEAD 一致）\n"
    )
    # 插入到现有头部条目之前；空文件则直接作为首条目
    if content.startswith("# Changelog"):
        head, _, rest = content.partition("\n")
        return head + "\n\n" + entry + "\n" + rest.lstrip("\n")
    return entry + "\n" + content


# 版本载体清单：(相对路径, 更新函数, 是否透传 bump --title)。
# pyproject.toml 是唯一事实来源，其余载体必须与之一致（test_version_consistency 逐项校验）。
# T-0102 F-03：CHANGELOG 更新器透传 --title（T-0100 F-03 引入时 lambda 丢 title）。
VERSION_CARRIERS: tuple[tuple[str, object, bool], ...] = (
    ("pyproject.toml", _update_pyproject, False),
    ("CHANGELOG.md", _update_changelog, True),
    ("loop_core/__init__.py", _update_init_version, False),
    ("src/loop_engine/__init__.py", _update_init_version, False),
    ("README.md", _update_readme_version, False),
    ("docs/06-delivery.md", _update_delivery_doc_version, False),
    (".zcode-plugin/plugin.json", _update_plugin_json_version, False),
    (".ai/version-manifest.yaml", _update_version_manifest, False),
)


def cmd_bump(root: Path, version: str, dry_run: bool = False, title: str = "") -> int:
    """版本同步（F-03）：bump --to <version> 原子更新 pyproject/CHANGELOG/载体。

    - 版本格式严格校验（x.y.z）；非法 → 用法错误（exit 2）。
    - 载体逐个原子写（临时文件 + os.replace），任一失败 → 报错退出（不落半成品）。
    - 缺省载体的项目（如迷你测试根没有 README）→ 提示跳过，不阻断。
    """
    if not STRICT_VERSION_RE.match(version):
        print(f"[release] bump 失败：非法版本号 {version!r}（需要 x.y.z 格式）")
        return 2
    current = load_version(root)
    if version == current:
        print(f"[release] bump: pyproject 已是 {version}，无需更新")
        return 0
    if dry_run:
        _print_plan([
            f"版本同步 {current} -> {version}（原子写，先 bump 再提交）：",
            *[f"  {rel}" for rel, _, _ in VERSION_CARRIERS],
            "提交 subject 必须携带同一版本号，version_sync 检查方通过",
        ])
        return 0
    for rel_path, updater, use_title in VERSION_CARRIERS:
        path = root / rel_path
        if not path.exists():
            print(f"[release] bump: 跳过缺失载体 {rel_path}（不存在）")
            continue
        try:
            content = path.read_text(encoding="utf-8")
            new_content = (updater(content, version, title) if use_title
                           else updater(content, version))  # type: ignore[operator]
            _atomic_write(path, new_content)
        except ValueError as exc:
            print(f"[release] bump 失败：{rel_path}: {exc}（已更新的载体不回滚，"
                  "请人工核对后重试）")
            return 1
        except OSError as exc:
            print(f"[release] bump 失败：{rel_path}: {exc}")
            return 1
        print(f"[release] bump: 已更新 {rel_path} -> {version}")
    print("[release] bump 完成。约定：先 bump 再提交 —— 提交 subject 使用 "
          f"v{version}，与 pyproject 一致，version_sync 即通过。")
    return 0


# ── check：质量门前置 ───────────────────────────────────────────────────

def step_version_sync(root: Path) -> tuple[bool, str]:
    """pyproject 版本 == git HEAD 版本（不一致 → 阻断，防漂移发布）。"""
    version = load_version(root)
    git_ver = git_head_version(root)
    if git_ver is None:
        return False, "无法从 git HEAD 提交信息解析版本（git 不可用或提交信息无版本号）"
    if version != git_ver:
        return False, (
            f"版本漂移：pyproject={version} vs git HEAD={git_ver}。"
            "约定：先 bump 再提交 —— 运行 `release.py bump --to <版本>` 更新"
            " pyproject/CHANGELOG/载体后，提交 subject 使用同一版本号"
        )
    return True, f"pyproject={version} == git HEAD={git_ver}"


def step_validate_state(root: Path) -> tuple[bool, str]:
    """调用**真实校验器** .zcode/tools/validate_state.py。

    独立审查修复（P1-1）：此前为自定义轻量实现（仅 YAML 可解析 +
    version-manifest 与 pyproject 一致），对连续性漂移等盲视；现改为
    subprocess 直接运行真实校验器（含 state/task/待决门禁/治理不变量/
    ProjectContinuity/handoff/角色合同全量检查）。fail-closed：校验器
    缺失、超时或无法启动均视为门禁失败，不放松任何门禁语义。

    T-0101（idle 稳态语义分流）：校验器 rc 语义 —— 0 = state usable（PASS）；
    3 = idle 合法阻塞态（current_task_id=null，无活动任务，**非损坏**），
    check 支持 idle 稳态运行，视为通过并明确标注"合法阻塞态"；其他非 0
    （含 2 = 真实治理损坏）→ FAIL（fail-closed 语义不变）。
    """
    validator = root / VALIDATE_STATE_SCRIPT
    if not validator.exists():
        return False, f"真实校验器缺失: {VALIDATE_STATE_SCRIPT}（fail-closed 阻断）"
    try:
        proc = subprocess.run(
            [sys.executable, str(validator), str(root)],
            cwd=str(root), capture_output=True, text=True,
            timeout=VALIDATE_STATE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False, (
            f"validate_state.py 超时（>{VALIDATE_STATE_TIMEOUT}s，fail-closed 阻断）"
        )
    except OSError as exc:
        return False, f"无法运行 validate_state.py: {exc}（fail-closed 阻断）"
    if proc.returncode == 3:
        tail = (proc.stdout or proc.stderr).strip().splitlines()[-5:]
        return True, (
            "validate_state.py 通过（rc=3：idle 合法阻塞态，current_task_id=null，"
            "无活动任务，等待任务发起；非治理损坏）: " + " | ".join(tail)
        )
    if proc.returncode != 0:
        tail = (proc.stdout or proc.stderr).strip().splitlines()[-10:]
        return False, (
            f"validate_state.py 校验失败（exit={proc.returncode}）: "
            + " | ".join(tail)
        )
    return True, "validate_state.py 校验通过（真实校验器，含连续性/角色合同/handoff）"


def step_compile(root: Path) -> tuple[bool, str]:
    """compileall 运行时代码目录（业务源码语法门）。"""
    proc = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", *COMPILE_DIRS],
        cwd=str(root), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-3:]
        return False, "编译失败: " + " | ".join(tail)
    return True, f"compileall 通过（{', '.join(COMPILE_DIRS)}）"


def step_guard_health(root: Path) -> tuple[bool, str]:
    """Guard 健康检查（BROKEN/DORMANT 任一 → FAIL，AC-05 fail-closed）。

    T-0135: 附 missing/drift/recompute 发现计数（可见性；仍 report 级不阻断——
    连续性/状态一致性已由 validate_state 硬阻断）。
    """
    try:
        from loop_core.guard_health import GuardHealth
    except ImportError as exc:
        return False, f"无法导入 loop_core.guard_health: {exc}"
    try:
        health = GuardHealth(root)
        summary = health.summary()
        integrity = health.integrity_check()
    except Exception as exc:  # noqa: BLE001
        return False, f"guard 健康检查异常: {exc}"
    overall = summary.get("overall")
    if overall != "PASS":
        return False, (
            f"guard 健康 FAIL（checked={summary.get('guards_checked')} "
            f"alive={summary.get('alive')} broken={summary.get('broken')} "
            f"dormant={summary.get('dormant')}）"
        )
    n_missing = len(integrity.get("missing", []))
    n_drift = len(integrity.get("drift", []))
    n_recompute = len(integrity.get("recompute", []))
    # T-0135 可见性：report 级发现计数始终展示（0 也显示——确认检查在跑）
    msg = (f"guard 健康 PASS（{summary.get('guards_checked')} 个 guard 全部存活）"
           f" [report] missing={n_missing} drift={n_drift} recompute={n_recompute}")
    return True, msg


def step_slo_gate(root: Path) -> tuple[bool, str]:
    """SLO 门禁（T-0093 wave 2，B2 §1.5）：error budget 耗尽 → 阻断。

    独立审查增补（P1-1）：reviewer 建议 check 增补 SLO 检查。轻量接入
    loop_core.slo_gate.check_slo_gate —— budget HEALTHY/CONSUMING → PASS
    （CONSUMING 附警告）；FREEZE / 数据不足（fail-closed）/ 异常 → FAIL。
    本步骤只新增阻断条件，不放松任何门禁语义。releases=1 表示本次发布
    自身的 release_fee 计入预算（预算足够才放行）。
    """
    try:
        from loop_core.slo_gate import check_slo_gate
    except ImportError as exc:
        return False, f"无法导入 loop_core.slo_gate: {exc}（fail-closed 阻断）"
    try:
        result = check_slo_gate(root, releases=1)
    except Exception as exc:  # noqa: BLE001 — 门禁异常视为门禁失败
        return False, f"SLO 门禁执行异常（fail-closed）: {exc}"
    if not result.passed:
        return False, f"SLO 门禁阻断: {result.reason}"
    return True, f"SLO 门禁通过: {result.reason}"


def step_key_tests(root: Path) -> tuple[bool, str]:
    """关键测试子集：版本一致性 + loop_core 核心。

    独立审查决策（P1-1）：全量测试保持子集（check 为发布前快速门，全量
    在 CI/验收阶段已跑）；SLO 检查已作为独立步骤（step_slo_gate）增补，
    见 .ai/evidence/T-0098/release/design.md §4。
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *KEY_TESTS],
        cwd=str(root), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stdout or proc.stderr).strip().splitlines()[-5:]
        return False, "关键测试失败: " + " | ".join(tail)
    return True, "关键测试子集通过（test_version_consistency + test_loop_core）"


PREFLIGHT_STEPS = (
    "version_sync", "validate_state", "compile", "guard_health",
    "slo_gate", "key_tests", "mutation_gate", "mypy_gate",
)


def step_mypy_gate(root: Path) -> tuple[bool, str]:
    """A1 mypy 门禁（T-0168，fail-closed）。

    双模式：
      - src/（产品代码，12 文件）：全量硬门禁，必须 0 错误。
      - loop_core/.zcode/tools/hooks/scripts（治理/运行时，存量 95 key）：
        增量门禁——错误 key（path|code|msg 去行号）对比
        .ai/checkers/mypy-incremental-baseline.json 基线，**新增 key → FAIL**；
        存量错误允许逐步清理（基线文件缺失 → FAIL，没跑过就当不合格）。
    """
    import json
    import re

    # 1) src 全量硬门禁
    proc_src = subprocess.run(
        [sys.executable, "-m", "mypy", "src"],
        cwd=str(root), capture_output=True, text=True, timeout=300,
    )
    if proc_src.returncode != 0:
        tail = (proc_src.stdout or proc_src.stderr).strip().splitlines()[-3:]
        return False, "mypy src 失败（产品代码必须 0 错误）: " + " | ".join(tail)

    # 2) 增量门禁（存量目录）
    baseline_path = root / ".ai" / "checkers" / "mypy-incremental-baseline.json"
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        baseline_keys = set(baseline.get("baseline_keys", []))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return False, f"mypy 增量基线缺失/不可解析（fail-closed）: {exc}"

    pat = re.compile(r"^([^\s:]+\.py):\d+:\s*error:\s*(\S+)\s*(?:\[([^\]]+)\])?")
    current: set[str] = set()
    for t in baseline.get("targets", []):
        proc = subprocess.run(
            [sys.executable, "-m", "mypy", t],
            cwd=str(root), capture_output=True, text=True, timeout=300,
        )
        for line in (proc.stdout or "").splitlines():
            m = pat.match(line)
            if m:
                current.add(f"{m.group(1)}|{m.group(2)}|{m.group(3) or ''}")

    new_keys = current - baseline_keys
    if new_keys:
        sample = sorted(new_keys)[:5]
        return False, f"mypy 新增错误 {len(new_keys)} 个（基线 {len(baseline_keys)}）: " + " | ".join(sample)
    return True, f"mypy 门禁 PASS（src 0 错误；存量目录 {len(current)} key ≤ 基线 {len(baseline_keys)}）"


def step_mutation_gate(root: Path) -> tuple[bool, str]:
    """T-0128 变异检出门禁（fail-closed）。

    读取 .ai/evidence/observability/ 下 M1（确定性规则）/ M2（真实角色）
    检出报告；任一报告缺失/不可解析 → FAIL（没跑过就当不合格）；
    阈值：M1 >= 5/6 且 M2 >= 4/6。检出率是"测试/质量线程有效性"的度量，
    见 T-0132 D-02 M1（机器可复算：报告由 scan/verify 确定性生成）。
    """
    obs = root / ".ai" / "evidence" / "observability"
    try:
        m1 = json.loads((obs / "mutation-report-m1.json").read_text(encoding="utf-8"))
        m2 = json.loads((obs / "mutation-report-m2.json").read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        return False, f"变异检出报告缺失（fail-closed）: {exc.filename}"
    except (json.JSONDecodeError, OSError) as exc:
        return False, f"变异检出报告不可解析: {exc}"

    m1_detected = int(m1.get("detected", 0))
    m1_seeded = int(m1.get("seeded", 0))
    m2_detected = int(m2.get("detected", 0))
    m2_seeded = int(m2.get("seeded", 0))

    m1_ok = m1_detected >= 5 and m1_seeded >= 6
    m2_ok = m2_detected >= 4 and m2_seeded >= 6
    if m1_ok and m2_ok:
        return True, (
            f"变异检出 PASS: M1 {m1_detected}/{m1_seeded} >= 5/6, "
            f"M2 {m2_detected}/{m2_seeded} >= 4/6"
        )
    return False, (
        f"变异检出 FAIL: M1 {m1_detected}/{m1_seeded}（需>=5/6）, "
        f"M2 {m2_detected}/{m2_seeded}（需>=4/6）"
    )


def run_preflight(root: Path) -> tuple[bool, list[dict]]:
    """依次执行全部质量门前置步骤；任一失败 → 整体 FAIL（fail-closed）。

    步骤函数按名在调用时解析（支持测试注入/替换单个步骤）。
    """
    results: list[dict] = []
    ok = True
    for name in PREFLIGHT_STEPS:
        step = globals().get(f"step_{name}")
        if step is None:
            results.append({"name": name, "ok": False, "message": "步骤未注册"})
            ok = False
            break
        try:
            step_ok, message = step(root)
        except Exception as exc:  # noqa: BLE001 — 步骤自身异常也视为门禁失败
            step_ok, message = False, f"步骤异常: {exc}"
        results.append({"name": name, "ok": step_ok, "message": message})
        if not step_ok:
            ok = False
            break  # 短路：门禁失败即阻断，不再执行后续步骤
    return ok, results


# ── build ───────────────────────────────────────────────────────────────

def build_artifacts(root: Path, dist_dir: Path | None = None) -> tuple[bool, str]:
    """python -m build 生成 wheel + sdist 到 dist/。构建工具缺失 → 明确报错。"""
    if importlib.util.find_spec("build") is None:
        return False, (
            "构建工具缺失：未安装 build 模块。请先执行 "
            "`python -m pip install build`（或 `pip install build`）后重试"
        )
    dist_dir = dist_dir or (root / "dist")
    dist_dir.mkdir(parents=True, exist_ok=True)
    # 优先隔离构建；隔离环境不可用（如解释器缺 venv 模块 / 离线）时
    # 回退 --no-isolation 使用当前环境的 setuptools。
    for extra in ([], ["--no-isolation"]):
        proc = subprocess.run(
            [sys.executable, "-m", "build", *extra, "--outdir", str(dist_dir)],
            cwd=str(root), capture_output=True, text=True,
        )
        if proc.returncode == 0:
            mode = "isolated" if not extra else "no-isolation"
            return True, f"构建成功（{dist_dir}，mode={mode}）"
        last_err = (proc.stdout or proc.stderr).strip().splitlines()[-10:]
        if "isolation" not in proc.stdout.lower() and "venv" not in proc.stdout.lower() \
                and "isolation" not in proc.stderr.lower() and "venv" not in proc.stderr.lower():
            # 非隔离环境问题 → 无回退意义
            return False, "构建失败: " + " | ".join(last_err)
    return False, "构建失败: " + " | ".join(last_err)


# ── manifest ────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_artifacts(dist_dir: Path) -> list[Path]:
    """dist/ 下的发布产物：wheel（*.whl）+ sdist（*.tar.gz）。"""
    artifacts = sorted(list(dist_dir.glob("*.whl")) + list(dist_dir.glob("*.tar.gz")))
    return artifacts


def write_manifest(
    dist_dir: Path,
    version: str,
    git_commit: str,
    manifest_path: Path | None = None,
    sha256_path: Path | None = None,
) -> dict:
    """生成产物清单（release-manifest.json）+ SHA256SUMS。校验和可复验。"""
    dist_dir = Path(dist_dir)
    manifest_path = manifest_path or (dist_dir / MANIFEST_NAME)
    sha256_path = sha256_path or (dist_dir / SHA256SUMS_NAME)
    artifacts = []
    sums_lines: list[str] = []
    for path in collect_artifacts(dist_dir):
        digest = sha256_file(path)
        artifacts.append({
            "name": path.name,
            "path": str(path.relative_to(dist_dir.parent)),
            "sha256": digest,
            "size_bytes": path.stat().st_size,
        })
        sums_lines.append(f"{digest}  {path.name}")
    manifest = {
        "schema_version": 1,
        "version": version,
        "git_commit": git_commit,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "scripts/release.py (T-0098)",
        "artifacts": artifacts,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    # P2 修复：write_text 默认换行在 Windows 上会写成 CRLF，导致
    # `sha256sum -c` 失败；改为 bytes 写入保持 LF（sha256sum 兼容）。
    sha256_path.write_bytes(("\n".join(sums_lines) + "\n").encode("utf-8"))
    return manifest


# ── release 证据 ────────────────────────────────────────────────────────

def write_release_evidence(
    root: Path, version: str, git_commit: str, dist_dir: Path,
) -> Path:
    """release 证据三件套落盘：.ai/evidence/release/<version>/。"""
    version_dir = root / ".ai" / "evidence" / "release" / version
    version_dir.mkdir(parents=True, exist_ok=True)
    # 1) 候选决策（status=requested，真实 GO 需用户/delivery-manager 决策）
    decision_request = {
        "schema_version": 1,
        "version": version,
        "task_id": "T-0098",
        "status": "requested",
        "requested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "requested_by": "scripts/release.py (T-0098)",
        "owners": [],
        "deadline": None,
        "decision": None,
        "note": (
            "候选发布决策（requested）。真实 GO 需用户 / delivery-manager 另行决策："
            "decision=GO / CONDITIONAL_GO（带 owners+deadline）/ NOGO，"
            "写入 release_decision.json 后由 S6 发布门禁识别。"
        ),
    }
    (version_dir / DECISION_REQUEST_NAME).write_text(
        json.dumps(decision_request, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    # 2) + 3) 产物清单与校验和（从 dist/ 复制，保证与产物同源可复验）
    write_manifest(
        dist_dir, version, git_commit,
        manifest_path=version_dir / MANIFEST_NAME,
        sha256_path=version_dir / SHA256SUMS_NAME,
    )
    return version_dir


# ── smoke：临时 venv 冒烟安装 ───────────────────────────────────────────

def run_smoke(dist_dir: Path, version: str, python: str | None = None) -> dict:
    """临时 venv → pip install dist/*.whl → import 验证。

    返回 {status: PASS|FAIL|SKIP, detail: str, ...}。
    - 依赖安装优先全量；失败（如离线）则回退 --no-deps 仅装 wheel 本体。
    - 环境不可用（venv/pip 无法创建或调用）→ status=SKIP 并附原因。
    """
    python = python or sys.executable
    dist_dir = Path(dist_dir)
    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        return {"status": "FAIL", "detail": f"{dist_dir} 下没有 wheel 产物"}
    tmp_dir = Path(tempfile.mkdtemp(prefix="loop-release-smoke-"))
    try:
        venv_dir = tmp_dir / "venv"
        try:
            proc = subprocess.run(
                [python, "-m", "venv", str(venv_dir)], capture_output=True, text=True,
            )
        except OSError as exc:
            return {"status": "SKIP", "detail": f"环境不可用：无法调用 venv（{exc}）"}
        if proc.returncode != 0:
            return {
                "status": "SKIP",
                "detail": f"环境不可用：无法创建临时 venv（{proc.stderr.strip() or 'unknown'}）",
            }
        venv_py = (
            venv_dir / "Scripts" / "python.exe"
            if os.name == "nt" else venv_dir / "bin" / "python"
        )
        try:
            probe = subprocess.run(
                [str(venv_py), "-m", "pip", "--version"], capture_output=True, text=True,
            )
        except OSError as exc:
            return {"status": "SKIP", "detail": f"环境不可用：无法调用 venv pip（{exc}）"}
        if probe.returncode != 0:
            return {
                "status": "SKIP",
                "detail": f"环境不可用：venv 内无 pip（{probe.stderr.strip() or 'unknown'}）",
            }
        wheel = str(wheels[-1])
        no_deps = False
        install = subprocess.run(
            [str(venv_py), "-m", "pip", "install", "--disable-pip-version-check", wheel],
            capture_output=True, text=True,
        )
        if install.returncode != 0:
            no_deps = True
            install = subprocess.run(
                [str(venv_py), "-m", "pip", "install", "--no-deps",
                 "--disable-pip-version-check", wheel],
                capture_output=True, text=True,
            )
        if install.returncode != 0:
            tail = (install.stdout or install.stderr).strip().splitlines()[-5:]
            return {"status": "FAIL", "detail": "pip 安装失败: " + " | ".join(tail)}
        check = subprocess.run(
            [str(venv_py), "-c",
             "import loop_engine, loop_core; "
             "print('loop_engine', loop_engine.__version__); "
             "print('loop_core', loop_core.__version__)"],
            capture_output=True, text=True,
        )
        if check.returncode != 0:
            return {
                "status": "FAIL",
                "detail": "import 验证失败: " + (check.stderr or check.stdout).strip(),
            }
        lines = check.stdout.strip().splitlines()
        versions = dict(line.split(" ", 1) for line in lines if " " in line)
        if versions.get("loop_engine") != version:
            return {
                "status": "FAIL",
                "detail": f"版本不匹配：wheel 内 loop_engine={versions.get('loop_engine')} vs 期望 {version}",
            }
        return {
            "status": "PASS",
            "detail": (
                f"冒烟通过（{os.path.basename(wheel)}，{'--no-deps' if no_deps else 'full deps'}）："
                + "; ".join(lines)
            ),
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── 子命令入口 ──────────────────────────────────────────────────────────

def _print_plan(lines: list[str]) -> None:
    for line in lines:
        print(f"[release][dry-run] {line}")


def cmd_check(root: Path, dry_run: bool = False) -> int:
    print(f"[release] check 质量门前置（root={root}，version={load_version(root)}）")
    if dry_run:
        _print_plan(["将依次执行:", *[f"  {n}" for n in PREFLIGHT_STEPS]])
        return 0
    ok, results = run_preflight(root)
    for r in results:
        mark = "PASS" if r["ok"] else "FAIL"
        print(f"[release]   [{mark}] {r['name']}: {r['message']}")
    if not ok:
        print("[release] check 失败 → 发布阻断（质量门前置未通过）")
        return 1
    print("[release] check 通过（质量门前置全部 PASS）")
    return 0


def cmd_build(root: Path, dry_run: bool = False) -> int:
    dist_dir = root / "dist"
    if dry_run:
        _print_plan([f"python -m build --outdir {dist_dir}", "产物: wheel + sdist"])
        return 0
    ok, message = build_artifacts(root, dist_dir)
    print(f"[release] build: {message}")
    if not ok:
        return 1
    for path in collect_artifacts(dist_dir):
        print(f"[release]   {path.name} ({path.stat().st_size} bytes)")
    return 0


def cmd_manifest(root: Path, dry_run: bool = False) -> int:
    dist_dir = root / "dist"
    if dry_run:
        names = [p.name for p in collect_artifacts(dist_dir)] or ["<dist/ 暂无产物>"]
        _print_plan([
            f"对 dist/ 产物计算 sha256/size: {', '.join(names)}",
            f"写入 {dist_dir / MANIFEST_NAME} + {dist_dir / SHA256SUMS_NAME}",
        ])
        return 0
    artifacts = collect_artifacts(dist_dir)
    if not artifacts:
        print(f"[release] manifest: {dist_dir} 下没有产物（先运行 build）")
        return 1
    manifest = write_manifest(dist_dir, load_version(root), git_head_commit(root))
    print(f"[release] manifest: {len(manifest['artifacts'])} 个产物已登记 "
          f"（{dist_dir / MANIFEST_NAME} + {dist_dir / SHA256SUMS_NAME}）")
    return 0


def cmd_release(root: Path, dry_run: bool = False) -> int:
    version = load_version(root)
    dist_dir = root / "dist"
    evidence_dir = root / ".ai" / "evidence" / "release" / version
    if dry_run:
        _print_plan([
            f"1. check：质量门前置（{' / '.join(PREFLIGHT_STEPS)}）",
            f"2. build：python -m build --outdir {dist_dir}（wheel + sdist）",
            f"3. manifest：{dist_dir / MANIFEST_NAME} + {dist_dir / SHA256SUMS_NAME}",
            "4. release 证据落盘（三件套）:",
            f"   {evidence_dir / DECISION_REQUEST_NAME}（status=requested，候选决策）",
            f"   {evidence_dir / MANIFEST_NAME}",
            f"   {evidence_dir / SHA256SUMS_NAME}",
            "注：不执行真实发布/上传；GO 由用户另行决策。",
        ])
        return 0
    print(f"[release] 1/4 check 质量门前置（version={version}）")
    ok, results = run_preflight(root)
    for r in results:
        mark = "PASS" if r["ok"] else "FAIL"
        print(f"[release]   [{mark}] {r['name']}: {r['message']}")
    if not ok:
        print("[release] 质量门前置失败 → release 阻断（不构建、不落盘）")
        return 1
    print("[release] 2/4 build")
    ok, message = build_artifacts(root, dist_dir)
    print(f"[release]   {message}")
    if not ok:
        return 1
    print("[release] 3/4 manifest")
    git_commit = git_head_commit(root)
    manifest = write_manifest(dist_dir, version, git_commit)
    print(f"[release]   {len(manifest['artifacts'])} 个产物已登记")
    print("[release] 4/4 release 证据落盘")
    version_dir = write_release_evidence(root, version, git_commit, dist_dir)
    print(f"[release]   证据目录: {version_dir}")
    for name in (DECISION_REQUEST_NAME, MANIFEST_NAME, SHA256SUMS_NAME):
        print(f"[release]     {name}")
    print("[release] 完成。注意：release-decision.request.json 仅为候选，"
          "真实 GO/NOGO 需用户 / delivery-manager 决策。")
    return 0


def cmd_smoke(root: Path, dry_run: bool = False) -> int:
    dist_dir = root / "dist"
    version = load_version(root)
    if dry_run:
        _print_plan([
            f"临时 venv（tempfile）→ pip install {dist_dir}/*.whl → "
            "import loop_engine/loop_core 并比对版本",
        ])
        return 0
    result = run_smoke(dist_dir, version)
    print(f"[release] smoke: {result['status']} — {result['detail']}")
    if result["status"] == "PASS":
        return 0
    if result["status"] == "SKIP":
        print("[release] smoke 跳过（环境不可用，不阻断 release 流程本身）")
        return 0
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release.py",
        description="D8 发布/产物体系：check / build / manifest / release / smoke / bump（T-0098/T-0100）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不执行不落盘")
    sub = parser.add_subparsers(dest="command", required=True)

    check_parser = sub.add_parser("check", help="质量门前置（validate_state 真实校验器 + compile + guard 健康 + SLO 门禁 + 关键测试子集；版本漂移时先 bump 再提交）")
    # T-0100 F-03：兼容 `check --dry-run`（子命令后置标志）与 `--dry-run check`
    check_parser.add_argument("--dry-run", dest="check_dry_run", action="store_true",
                              help="只打印计划，不执行不落盘")
    sub.add_parser("build", help="构建 wheel + sdist 到 dist/")
    sub.add_parser("manifest", help="生成产物清单 + SHA256SUMS")
    sub.add_parser("release", help="check + build + manifest + release 证据落盘")
    sub.add_parser("smoke", help="临时 venv 冒烟安装验证")
    bump_parser = sub.add_parser(
        "bump", help="版本同步（原子更新 pyproject/CHANGELOG/载体；先 bump 再提交）"
    )
    bump_parser.add_argument("--to", required=True,
                             help="目标版本（x.y.z 格式）")
    bump_parser.add_argument("--title", default="",
                             help="CHANGELOG 新条目标题（缺省用通用说明）")

    args = parser.parse_args(argv)
    root = PROJECT_ROOT
    if args.command == "bump":
        return cmd_bump(root, args.to, dry_run=args.dry_run, title=args.title)
    if args.command == "check":
        # 兼容 `check --dry-run` 与 `--dry-run check` 两种写法
        return cmd_check(root, dry_run=args.dry_run or args.check_dry_run)
    handlers = {
        "build": cmd_build,
        "manifest": cmd_manifest,
        "release": cmd_release,
        "smoke": cmd_smoke,
    }
    return handlers[args.command](root, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
