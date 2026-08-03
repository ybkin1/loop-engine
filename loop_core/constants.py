"""Loop Core 共享常量表 — 魔法数字集中化（T-0110 批 A，M-1~17 清单落地）。

本模块是 loop_core 各模块（及 tools/、scripts/ 消费方）的命名常量单一来源：
截断族（M-10/M-11）、超时族（D3-6/D3-8）、阈值族（M-7/M-8/M-9）、治理工具
exit code 族（M-2）。

已落地于既有具名常量、不重复迁移（集中化模板，见
.ai/evidence/T-0110/fixes/batch-a-constants.md 落地表）：
- M-5  git timeout 族：context_packager.GIT_TIMEOUT_*（T-0107 D2-8）
- M-6  IntentRouter.MEDIUM_RISK_ESCALATION_MIN（T-0107 D2-2，类级具名）
- M-12 context_packager.MAX_TOTAL_CHARS（T-0107 D3-2 死护栏修复）
- M-13 context_packager.ROLE_CONTEXT 角色上限表（T-0107 D2-1）
- M-14 observability.DEFAULT_MAX_LINES/BYTES/ARCHIVES（先例模板）
- M-15 validate_state.MAX_CONTRACT_AGE_DAYS（先例模板）
- M-16 .ai/slo.yaml score_caps（T-0109 F1；与 evidence_state.DEFAULT_SCORE_CAPS
  同源，本批核对一致）
- M-17 evals.MAX_CAPTURE_CHARS / DEFAULT_EXEC_TIMEOUT（先例模板）

hook 侧常量（EXIT_PASS/EXIT_BLOCK、hook timeout 族、治理路径白名单）见
hooks/scripts/loop_enforcement_constants.py（M-1/M-3/M-4 落点）。

语义契约：本模块只含常量与纯截断辅助函数，导入零副作用（可被
hooks/tools/scripts 独立消费，不拉起任何运行时依赖）。
"""
from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════
# exit code 族（M-2：validate_state/close_session 返回码；validate_state
# 语义 T-0101 三处约定对齐 0/2/3）。消费方接线受 allowed_paths 约束时
# 保留原字面量（显式豁免），本表为共享引用唯一登记处。
# ══════════════════════════════════════════════════════════════════════
EXIT_OK = 0                 # 成功（validate_state "[ok] state is usable" / close_session 稳定）
EXIT_VALIDATION_FAILED = 2  # 校验失败 / fail-closed 阻断（validate_state 真实治理损坏、
                            # close_session 未稳定；hook 裁决 EXIT_BLOCK 同值）
EXIT_IDLE_BLOCKED = 3       # validate_state idle 合法阻塞态（NO_ACTIVE_TASK，T-0101 分流）

# ══════════════════════════════════════════════════════════════════════
# 截断族（M-10/D1-5、D1-6；M-11/D1-8、D2-7）
# ══════════════════════════════════════════════════════════════════════
SNIPPET_MAX_CHARS = 100               # M-10/D1-5 违规 snippet 截断上限（security_scanner/design_reviewer）
FAILED_STDERR_MAX_CHARS = 500         # M-10/D1-6 失败 stderr 截断上限（executor 编译门日志）
AUDIT_STDOUT_TAIL_CHARS = 4000        # M-11/D2-7 自审计 stdout 尾部保留（loop_self_audit.run）
AUDIT_STDERR_TAIL_CHARS = 2000        # M-11/D2-7 自审计 stderr 尾部保留（loop_self_audit.run）
AUDIT_SUMMARY_STDOUT_TAIL_CHARS = 800  # M-11 LLM 摘要 stdout 尾部保留（build_llm_summary）
AUDIT_SUMMARY_STDERR_TAIL_CHARS = 400  # M-11 LLM 摘要 stderr 尾部保留（build_llm_summary）
TRUNCATION_ELLIPSIS = "…"             # D1-5/6/8 统一截断省略号标记

# ══════════════════════════════════════════════════════════════════════
# 超时族（D3-6/D3-8 git 命令；对齐 evals.py git_commit 同款 timeout=10）
# ══════════════════════════════════════════════════════════════════════
GIT_DIFF_NAME_ONLY_TIMEOUT_SECONDS = 10  # D3-6 role_checkers `git diff --name-only` 超时
GIT_SHORT_SHA_TIMEOUT_SECONDS = 10       # D3-8 `git rev-parse --short HEAD` 超时（loop_self_audit/evals 同值）
AUDIT_RUN_TIMEOUT_SECONDS = 300          # loop_self_audit.run 子进程默认超时（原字面量 300）

# ══════════════════════════════════════════════════════════════════════
# 阈值族（M-7/D2-3、M-8/D2-4、M-9/D2-5）
# ══════════════════════════════════════════════════════════════════════
CONFIDENCE_CONFLICT_MIN_DOMAINS = 4        # M-7/D2-3 置信度惩罚：域数 ≥ 4 且风险因素 ≤ 2 时生效
CONFIDENCE_CONFLICT_MAX_RISK_FACTORS = 2   # M-7/D2-3 置信度惩罚：风险因素上界
KEYWORD_BOUNDARY_MAX_LEN = 3               # M-8/D2-4 词边界策略：len(kw) > 3 → 子串匹配（≤ 3 → 词边界）
USER_GATE_MIN_DISTINCT_ROLES = 3           # M-9/D2-5 USER_GATE 升级：≥ 3 个不同角色（veto_escalation）


def truncate_with_marker(text: str, limit: int,
                         marker: str = TRUNCATION_ELLIPSIS) -> str:
    """前缀截断并带统一省略号标记（D1-5/D1-6 约定）。

    len(text) <= limit → 原文返回（零变化）；否则保留前
    (limit - len(marker)) 个字符并追加 marker，总长恰为 limit。
    前置条件：limit >= len(marker)。
    """
    if len(text) <= limit:
        return text
    return text[: limit - len(marker)] + marker


def tail_with_marker(text: str, limit: int,
                     marker: str = TRUNCATION_ELLIPSIS) -> str:
    """保留尾部并带统一省略号标记（D1-8/D2-7 约定）。

    len(text) <= limit → 原文返回（零变化）；否则 marker 置于开头、
    保留最后 (limit - len(marker)) 个字符（头部被裁掉，标记指示截断）。
    前置条件：limit >= len(marker)。
    """
    if len(text) <= limit:
        return text
    return marker + text[-(limit - len(marker)):]
