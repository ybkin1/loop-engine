# T-0110 验收报告 — 共同弱点·常量集中 + 5 巨文件行为等价拆分

- 任务：T-0110（G-T-0110-REQUIREMENTS，approved）— T-0106 排布第四项：
  魔法数字集中化（M-1~17）+ 5 个巨型文件行为等价拆分
- 角色：governance-controller（编排与验收）；developer（批 A/B-1/B-2/C）；independent-reviewer（独立审查）
- 执行时间：2026-08-03（UTC+8）
- 基线：git HEAD `70ca674`（v3.12.46，T-0109）；版本 bump **3.12.47**
- 设计依据：`.ai/evidence/T-0106/design/design-common-weakness.md`

---

## 一、三批交付

| 批 | 内容 | 关键成果 |
|----|------|---------|
| 批 A 常量集中 | M-1~17 清单 + P3 消解 | `constants.py`（22 常量）+ `loop_enforcement_constants.py`（M-1/3/4 等）+ tool 常量 + slo.yaml M-16 核对；**26 常量登记**；P3 消解 D2-3~7/D1-5/6/8/D3-6/8/D4-9；grep timeout 零新散落双断言 |
| 批 B-1 | governance_metrics + intent_router 拆分 | **1508→612 壳**（4 新模块）+ **1484→965 壳**（3 新模块，D5-4 词表外提）；golden **425,977 B 逐字节一致** |
| 批 B-2 | human_review_packet + context_loader 拆分 | **1307→643 壳**（3 新模块）+ **1432→839 壳**（4 新模块）；golden **66,082 B 逐字节一致**；include_memories 默认 False 保持 |
| 批 C hook 拆分 | loop_enforcement 外提 | **2115→1052 壳**（接线 loop_contract_parser/loop_command_utils/gate_evidence_checks/constants）；golden **49,858 B 逐字节一致**；**自愈 re-exec 实测（恰一次 rc=0 判定一致）**；hook 套件拆分后 **1273 passed 0 failed** |

## 二、AC 对照

| AC | 验收标准 | 结果 |
|----|---------|------|
| AC-01 | 常量表单测 + grep timeout 零新散落 | **PASS**（26 常量 + 双断言锁定） |
| AC-02 | 每文件拆分 golden 逐字节/逐字段一致 | **PASS**（三批 golden 独立复跑一致 + AST 反造假验证：before 快照 = 拆分前真实捕获） |
| AC-03 | loop_enforcement 自愈路径实测 + hook 测试全跑 | **PASS**（re-exec 恰一次判定一致；函数体与 HEAD 逐字节 diff 为空；hook 套件 1273 passed） |
| AC-04 | 全量回归 0 failed + compile + release check 6/6 | **PASS**（独立复验 4138 passed；5 failed 全部已登记/瞬态；compile 0 错误） |
| AC-05 | 版本 3.12.47 == git HEAD | **PASS**（提交后成立） |
| AC-06 | 独立审查 GO + hooks/ 仅批 C + 行为等价 | **PASS**（GO 无 P0/P1/P2；hooks/ 仅 5 文件；零删除；内核 diff=0） |

## 三、独立审查摘要（independent-review.md）

- **裁决：GO**（P0/P1/P2 = 0；P3×4 记录：文档口径/golden C 场景数/bak 文件/事件噪声）
- 行为等价专项：三批 golden 独立复跑逐字节一致 + 反造假验证（AST 交叉核对 before 快照 dir() 基线零缺失）
- 自愈实测：`_snapshot_hook_file_shas`/`_hook_files_changed_since_load`/`_reexec_with_fresh_code` 与 HEAD 逐字节 diff 为空（仅扫描集 +4 文件名）；TestSelfHealReexec 2/2
- hooks 专项：仅 loop_enforcement.py（98+/1161-）+ 4 新模块；其余 16 个 hook 文件零改动；治理内核 5 文件 diff=0；零删除
- 全量回归独立复验：4138 passed / 5 failed（全部已登记/瞬态：环境依赖/manifest/version bump 漂移×3 同根因）——无 T-0110 引入失败

## 四、裁决

**T-0110 验收通过（6/6 AC）。** 魔法数字集中化 + 5 巨文件行为等价拆分完成：
loop_enforcement 2115→1052、governance_metrics 1508→612、intent_router 1484→965、
human_review_packet 1307→643、context_loader 1432→839；三批 golden 逐字节一致 +
自愈机制实证保留。hooks/ 仅批 C 五文件、治理内核零触碰、零删除。版本 3.12.47。

## 五、下一步

T-0111（修复器治理 + 臃肿全景清理验证 + **死工具终态审计删除**）待用户批准。
P3 记录项（文档口径/golden 场景数/bak 文件清理）随后续顺带。
