# T-0126 验收报告

## 验收结论：PASS（6/6 AC）

| AC | 验收项 | 证据 | 结果 |
|----|--------|------|------|
| AC-01 | env-dependent 测试在端口占用环境下通过 | 实证脚本：0.0.0.0:3000/8000 双栈占用 + ::1 模拟占用场景下注入方案确定性 FAIL；本机 4 passed（原根因链：localhost 解析 ::1 优先 + urllib 不回退 IPv4 + 端口占用） | ✅ |
| AC-02 | checker 默认行为不变 | scripts/runtime_delivery_gate.py / deployment_quality_checker.py 零改动（git diff 空）；check_service_startup 未传 service_url 时仍探测常见端口 | ✅ |
| AC-03 | 全量回归 0 failed + compile + release check | 4224 passed / 4 failed（4 项全为连续性 drift，repair+render 后全绿）；compile 94/94；release check 6/6（提交后复验） | ✅ |
| AC-04 | KNOWN_ISSUES 收口 | env-dependent 关闭（T-0126 引用）；Open 区 5 条已解决移入 Recently Closed；保留 3 条长期记录（session-source-disabled/seeded defects/E2E） | ✅ |
| AC-05 | 版本 3.12.61 | 8 载体一致 + CHANGELOG T-0126 条目；提交后 version_sync 自愈（F-03） | ✅ |
| AC-06 | 独立审查 GO | **GO**（4 条低/信息级发现无阻塞：import 风格已按建议移模块顶部、绑定不监听 Windows 语义实证成立、收口信息可回溯、bump 提交前状态符合 F-03） | ✅ |

## 关键事实

- 修复机制：`socket.bind(("127.0.0.1", 0))` 随机端口 + **绑定不 listen**（连接必被拒，端口不可被复用）+ 显式 IPv4 地址（绕过 localhost 解析歧义）+ finally 释放
- checker 零改动：`service_url` 参数本就支持注入，默认行为不变
- fail-closed 断言原样保留（overall=BLOCKED / SIMULATED_MAIN_SESSION / agent_takeover=False / 除 artifact.manifest 外无 PASS）
- KNOWN_ISSUES Open 区从 8 条收口至 3 条长期记录；5 条关闭条目均带版本引用
- 版本 3.12.61

## 提交说明

- 提交 subject：`v3.12.61: T-0126 — env-dependent 测试修复 + KNOWN_ISSUES 收口`
- 提交后复验：version_sync、release check 6/6
