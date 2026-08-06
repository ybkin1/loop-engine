# T-0120 commands

## 执行命令记录

```bash
# 1. 只读调研（candidate-only，零写入项目外数据）
ls C:/Users/Administrator/.zcode/cli/exec/                      # 646 会话目录
ls C:/Users/Administrator/.zcode/cli/exec/sess_<uuid>/          # call_*.log（stdout/stderr）
ls C:/Users/Administrator/.zcode/v2/                            # 配置/状态（非会话转录）
#    → 会话 = bash 工具执行日志（无结构化转录/verdict/findings）

# 2. 设计产出（.ai/evidence/T-0120/design/）
#    D-01-zcode-session-inventory.md（持久化位置/格式/元数据 + 与 Qoder 差异）
#    D-02-evidence-path.md（三方案：A 存在性核验（推荐）/B 日志哈希入链（不推荐）/C 不落地）
#    decision-packet.md（决策包交用户）

# 3. 校验（candidate-only 走完整流程）
C:/Python312/python.exe .ai/checkers/compile_gate.py . --output .ai/evidence/T-0120/compile-evidence.json
C:/Python312/python.exe .zcode/tools/validate_state.py --repair .
```

## 关键事实

- ZCode 会话数据：`~/.zcode/cli/exec/sess_<uuid>/call_*.log`（5.1G，646 会话，
  大量空目录）；无元数据文件、无 LLM 转录
- 与 Qoder 差异：本地原生可核验 vs 外部宿主不可控（T-0112 撤销核心）
- 方案 A 边界：存在性核验 = 呈现层提示（reason 标注），**不改变 verdict 判定、
  不把日志内容作验收证据**——T-0112 边界实质保持

## 遗留观察

- 版本保持 3.12.55（candidate-only 不 bump，T-0103/T-0106 同款）
- 落地与否待用户 gate 决策（决策包已交）
