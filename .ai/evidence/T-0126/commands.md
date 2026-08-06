# T-0126 commands

## 执行命令记录

```bash
# 1. 修复 env-dependent 测试（端口注入）
#    tests/test_deployment_quality_checker.py::test_runtime_report_is_simulated_and_fail_closed
#    注入 service_url：bind("127.0.0.1", 0) 拿随机端口 + 绑定不监听（连接必被拒）
#    finally 释放 socket。checker 代码零改动（check_service_startup 本就支持注入）。

# 2. 复现与实证（2026-08-06）
C:/Python312/python.exe -m pytest tests/test_deployment_quality_checker.py -q   # 4 passed
#    模拟占用 0.0.0.0:3000/8000（双栈 HTTP 200）：旧断言环境依赖、新断言确定性 FAIL
#    根因链：localhost 解析 getaddrinfo 返回 ::1 优先 + urllib 不回退 IPv4
#    + 端口占用状态 —— 三重环境因素叠加（T-0107 baseline 曾实证 PASS 场景）

# 3. KNOWN_ISSUES Open 区收口
#    env-dependent / Large-module-split-candidates×2 / T-0117 / ROLE_CHALLENGES / T-0104
#    → Recently Closed（5 条）；session-source-disabled / seeded defects / E2E 保留

# 4. 全量回归 + compile + bump
C:/Python312/python.exe -m pytest tests/ -q                          # 含 env-dependent 全绿
C:/Python312/python.exe .ai/checkers/compile_gate.py . --output .ai/evidence/T-0126/compile-evidence.json
C:/Python312/python.exe scripts/release.py bump --to 3.12.61 --title "T-0126 — env-dependent 测试修复 + KNOWN_ISSUES 收口"

# 5. 独立审查 + 验收 + release check + 提交推送
```

## 修复要点

- 端口来源可注入（service_url 参数），checker 判定语义零改动（AC-02）
- 绑定不监听（bind 不 listen）比 bind-then-close 更稳：端口不可能被复用、连接必被拒
- 显式 127.0.0.1 绕过 localhost 的 IPv6/IPv4 解析歧义（本机 getaddrinfo 返回 ::1 优先）
- fail-closed 断言原样保留（overall=BLOCKED / SIMULATED_MAIN_SESSION / 除 artifact.manifest 外无 PASS）
