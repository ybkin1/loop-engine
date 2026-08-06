# T-0120 验收报告

## 验收结论：PASS（5/5 AC）

| AC | 验收项 | 证据 | 结果 |
|----|--------|------|------|
| AC-01 | D-01 调研 | 持久化位置/格式/元数据 + 与 Qoder 差异；独立审查实测核对（647 会话、call_*.log、无 verdict/findings 结构） | ✅ |
| AC-02 | D-02 方案 + 一致性论证 | 三方案（A 存在性核验推荐/B 日志哈希不推荐/C 不落地）+ 与 T-0112 撤销理由（外部宿主不可核验）一致性论证；独立审查对照 task_graph/KNOWN_ISSUES 一手记录成立 | ✅ |
| AC-03 | 决策包交用户 | 方案对比/推荐理由/风险/用户决策点齐全 | ✅ |
| AC-04 | 产品代码零改动 | 独立审查 git 确认仅 .ai/；版本 3.12.55 未动（candidate-only 不 bump） | ✅ |
| AC-05 | 独立审查 GO | **GO**（2 处活数据/表述小偏差已补记，非阻塞） | ✅ |

## 关键事实

- ZCode 原生会话 = 本地 bash 工具日志（`~/.zcode/cli/exec/sess_<uuid>/call_*.log`），
  非审查内容证据（无 verdict/findings）——与 Qoder 外部转录的本质差异 = 本地可核验
- 推荐方案 A（会话存在性核验，呈现层）待用户 gate 决策；落地需独立任务
- candidate-only 完整流程：compile evidence + validate EXIT=0 + 独立审查 GO
- 版本保持 3.12.55（T-0103/T-0106 同款）

## 提交说明

- 提交 subject：`T-0120 — ZCode 原生会话证据路径设计（candidate-only，决策包交用户；版本保持 3.12.55）`
- 无版本 bump；提交后复验 manifest 引用
