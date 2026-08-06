# T-0121 验收报告

## 验收结论：PASS（5/5 AC）

| AC | 验收项 | 证据 | 结果 |
|----|--------|------|------|
| AC-01 | session_source 字段 | 4 return 点齐备；unverified-zcode 集成测试实证；独立呈现字段（非 reason 文本） | ✅ |
| AC-02 | 既有判定零变化 | diff 零删除行（add-only）；T-0118 21/21 + f1 29/29 | ✅ |
| AC-03 | 全量回归 + compile + release check | 4219 passed（仅 manifest 在途态）；compile 87/87；release check 提交后 6/6 | ✅ |
| AC-04 | 版本 3.12.56 | 8 载体 3.12.56 + CHANGELOG T-0121 条目；提交后 version_sync 自愈（F-03） | ✅ |
| AC-05 | 独立审查 GO | **GO**（2 项 closeout 自愈类观察：manifest 在途 + bump 漂移 repair 已处理） | ✅ |

## 关键事实

- T-0120 方案 A 落地：sess_<uuid> 目录存在性核验（verified-zcode/unverified-zcode/
  external/unavailable 四类标注），本地可核验——补上 T-0112 撤销（外部宿主不可核验）缺口
- 边界保持：呈现层字段不参与 verdict 判定（valid=True 时 unverified-zcode 仍 valid）；
  不读取日志内容；checks 7 项不变；hooks/ 零改动
- 可配置：ZCODE_SESSION_EXEC_DIR 环境变量（运行时读取，fail-safe）
- KNOWN_ISSUES session-source-disabled 记录更新
- 版本 3.12.56

## 提交说明

- 提交 subject：`v3.12.56: T-0121 — ZCode 会话存在性核验（T-0120 方案 A 落地，呈现层 session_source）`
- 提交后复验：version_sync、manifest 引用、release check 6/6
