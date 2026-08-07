# T-0153: 手机 PWA 叠加层设计（candidate 原型）

> 交付物：T-0153（AC-01~AC-06）
> 日期：2026-08-07
> 性质：candidate 原型 —— 仓库内实现（web/），**不连接真实 NordRelay**。

## 1. 架构总览

```
┌─ 手机（PWA，独立移动端页面） ─┐      ┌─ NordRelay 侧（外部，需 gate）─┐
│ index.html / app.js / style.css │      │  /api/sessions                │
│ api.js（mock | real 适配层）    │ ───▶ │  /api/sessions/:id            │
│ sw.js（离线壳）                 │      │  /api/events（SSE）           │
│ manifest.json（可安装）         │      │  账号体系 / apiToken          │
└────────────────────────────────┘      └───────────────────────────────┘
```

- **独立页面**：不依赖 NordRelay 桌面 WebUI（自绘深色移动 UI）
- **API 适配层**：`api.js` 统一契约，`mode: 'mock'` 默认；切 `real` 需
  用户 gate（外部边界）
- **SSE**：`/api/events` EventSource 封装 → 实时事件 toast + 消息追加

## 2. 功能映射（面试题能力复用）

| 功能 | 实现 | 对应模板资产 |
|------|------|-------------|
| 工作区首页（/api/sessions 分组） | mock 三会话按 workspace 分组渲染 | capacity/load-test 无关 |
| 会话列表/详情 | 卡片列表 + 消息流 | — |
| 实时事件（SSE） | EventSource 封装 + toast + 追加渲染 | — |
| 发消息 | POST messages（mock 追加） | consistency（幂等：消息 id 去重待真实对接） |
| abort | POST abort（mock 返回 aborted） | stability（快失败/熔断语义对齐） |
| 切模型 | POST model（mock 更新） | — |

## 3. 设备配对设计（二维码 → 一次性登录码 → 持久 token）

> **本任务仅设计**；真实配对服务实现属外部边界（需用户单独 gate）。

```
1. 手机端显示二维码（QR 内容 = 配对请求 {device_id, pub_key, exp}）
2. 桌面 WebUI 扫码确认 → NordRelay 生成一次性登录码（short-lived, 5min）
3. 手机回填登录码 → NordRelay 校验 → 签发持久 token（apiToken 机制）
4. 手机本地安全存储 token（WebCrypto 加密 + 不落明文）→ 后续 API 请求携带
```

**安全考量**：
- 一次性登录码：单次使用 + 5 分钟过期 + 设备绑定（device_id）
- 持久 token：服务端可撤销（revoke 即失效）；手机端加密存储
- 二维码：仅含配对请求（无敏感信息）；防重放（exp + nonce）
- 传输：仅 HTTPS（公网反代必须 TLS；本地开发 http 仅 mock）

## 4. 外部边界（本任务未做，需用户 gate）

- 连接真实 NordRelay 实例（api.js mode 切 real）
- 公网反代（Caddy / Cloudflare Tunnel）暴露 PWA
- WSS relay 替代 SSE（如需双向/持久连接）
- 真实设备配对服务（二维码/登录码/token 签发）

## 5. 验收对照

| AC | 结果 |
|----|------|
| AC-01 PWA 骨架可本地运行 | web/ 五文件（manifest/SW/html/js/css） |
| AC-02 mock API 客户端 | api.js（sessions 分组/详情/发消息/abort/切模型） |
| AC-03 SSE 消费封装 | api.js subscribeEvents + app.js 渲染 |
| AC-04 设备配对设计 | 本文 §3（二维码→登录码→token + 安全考量） |
| AC-05 冒烟测试 | tests/test_t0153_pwa_prototype.py（结构 + mock 逻辑） |
| AC-06 独立审查 GO | 外部边界未越界核验 |
