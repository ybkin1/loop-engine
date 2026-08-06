# T-0126 env-independent 测试修复

## 根因（KNOWN_ISSUES env-dependent 登记）

`test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed`
原实现不传 `service_url`，checker 探测 `http://localhost:{3000,3001,8080,8000}`。
`service.startup` 是否 PASS 取决于三重环境因素：

1. 本机端口 3000/8000 是否被无关进程监听（T-0107 e083f7b baseline 实证过 PASS 场景）；
2. `localhost` 解析顺序（getaddrinfo 返回 `::1` 优先，本机实测 IPv6 优先；
   urllib 对 IPv6 连接失败是否回退 IPv4 因环境而异）；
3. 系统代理配置。

任一组合变化都会翻转测试结果 → 环境依赖失败（非代码缺陷）。

## 修复（端口注入）

测试侧注入 `service_url`：

- `socket.socket(AF_INET, SOCK_STREAM).bind(("127.0.0.1", 0))` 获取随机可用端口；
- **绑定但不 listen**，保持 socket 存活直至断言完成 —— 对端连接必被
  `ConnectionRefused`（Windows 同 Linux 语义），端口不可能被他人复用；
- `run_full_runtime_gate(service_url=f"http://127.0.0.1:{port}")` 显式 IPv4 地址，
  绕过 localhost 解析歧义；
- `finally: blocker.close()` 释放。

checker 代码零改动：`check_service_startup` 本就支持 `service_url` 注入
（默认行为不变，未传时仍探测常见端口）。

## 实证（2026-08-06）

| 场景 | 旧行为（无注入） | 新行为（注入） |
|------|------------------|----------------|
| 端口空闲（本机） | PASS 断言通过（碰巧） | 确定性 FAIL，断言通过 |
| 0.0.0.0:3000/8000 双栈占用 | FAIL（urllib 未回退 IPv4） | 确定性 FAIL，断言通过 |
| ::1:3000/8000 占用（模拟） | PASS（KNOWN_ISSUES 根因） | 确定性 FAIL，断言通过 |

结论：注入方案与端口占用、地址族解析、代理配置完全无关，AC-01 成立。

## 语义保持

- `overall == "BLOCKED"`、`execution_mode == "SIMULATED_MAIN_SESSION"`、
  `agent_takeover is False`、除 `artifact.manifest` 外无 PASS —— fail-closed
  断言原样保留，未掩盖任何真实缺陷。
- checker 判定逻辑（BLOCKING_STATUSES/诊断链）零改动。
