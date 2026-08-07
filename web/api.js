/**
 * NordRelay Mobile — API 客户端 + SSE 消费（T-0153 candidate 原型）
 *
 * 边界：本文件是**原型适配层**，默认 MOCK 模式（内存数据），不连接真实
 * NordRelay 实例。真实对接需用户单独 gate（外部边界）。
 *
 * 接口契约（与 NordRelay WebUI 对齐的假设契约，真实字段以对接时为准）：
 *   GET  /api/sessions            → [{id, workspace, title, status, model, updated_at}]
 *   GET  /api/sessions/:id        → {id, messages: [{role, content, ts}], model, status}
 *   POST /api/sessions/:id/messages {content} → {id, role:'user', ts}
 *   POST /api/sessions/:id/abort  → {aborted: true}
 *   POST /api/sessions/:id/model  {model} → {model}
 *   GET  /api/events (SSE)        → event: {type:'message'|'status'|'model', session_id, ...}
 */
const API = {
  mode: 'mock', // 'mock' | 'real'（real 需 gate 后才允许切换）

  async request(path, opts = {}) {
    if (this.mode === 'mock') return Mock.handle(path, opts);
    const r = await fetch(path, {
      headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
      ...opts,
    });
    if (!r.ok) throw new Error(`API ${r.status}: ${path}`);
    return r.json();
  },

  listSessions() { return this.request('/api/sessions'); },
  getSession(id) { return this.request(`/api/sessions/${id}`); },
  sendMessage(id, content) {
    return this.request(`/api/sessions/${id}/messages`, { method: 'POST', body: JSON.stringify({ content }) });
  },
  abort(id) { return this.request(`/api/sessions/${id}/abort`, { method: 'POST' }); },
  switchModel(id, model) {
    return this.request(`/api/sessions/${id}/model`, { method: 'POST', body: JSON.stringify({ model }) });
  },

  /** SSE 消费封装：EventSource 或 mock 定时器，统一 onEvent 回调。 */
  subscribeEvents(onEvent) {
    if (this.mode === 'mock') return Mock.subscribe(onEvent);
    const es = new EventSource('/api/events');
    es.onmessage = (e) => onEvent(JSON.parse(e.data));
    return () => es.close();
  },
};

/* ── Mock 实现（内存数据，模拟 NordRelay 行为） ─────────────────────── */
const Mock = {
  sessions: [
    { id: 's1', workspace: 'loop-engine', title: 'T-0153 PWA 原型', status: 'active', model: 'deepseek-v4', updated_at: '2026-08-07T20:10:00+08:00' },
    { id: 's2', workspace: 'loop-engine', title: 'T-0152 收尾', status: 'idle', model: 'deepseek-v4', updated_at: '2026-08-07T19:50:00+08:00' },
    { id: 's3', workspace: 'personal', title: '笔记整理', status: 'idle', model: 'claude-sonnet', updated_at: '2026-08-07T18:00:00+08:00' },
  ],
  messages: {
    s1: [
      { role: 'user', content: '做一个手机端 PWA 原型', ts: '2026-08-07T20:00:00+08:00' },
      { role: 'assistant', content: '好的，我来创建 web/ 目录原型。', ts: '2026-08-07T20:01:00+08:00' },
    ],
  },

  async handle(path, opts) {
    await delay(120);
    const m = path.match(/^\/api\/sessions(?:\/([^/]+))?(?:\/(messages|abort|model))?$/);
    if (!m) throw new Error(`mock: 未知路径 ${path}`);
    const [, id, action] = m;
    if (!id && !action) return { sessions: this.sessions };
    if (id && !action) {
      const s = this.sessions.find((x) => x.id === id);
      return { ...s, messages: this.messages[id] || [] };
    }
    if (action === 'messages') {
      const body = JSON.parse(opts.body || '{}');
      this.messages[id] = this.messages[id] || [];
      const msg = { role: 'user', content: body.content, ts: now() };
      this.messages[id].push(msg);
      return msg;
    }
    if (action === 'abort') return { aborted: true, id };
    if (action === 'model') {
      const body = JSON.parse(opts.body || '{}');
      const s = this.sessions.find((x) => x.id === id);
      if (s) s.model = body.model;
      return { model: body.model, id };
    }
    throw new Error('mock: 未支持操作');
  },

  subscribe(onEvent) {
    // mock SSE：模拟 assistant 消息流
    const t = setInterval(() => {
      onEvent({
        type: 'message',
        session_id: 's1',
        role: 'assistant',
        content: `[mock] ${new Date().toLocaleTimeString()} 心跳事件`,
        ts: now(),
      });
    }, 5000);
    return () => clearInterval(t);
  },
};

function delay(ms) { return new Promise((r) => setTimeout(r, ms)); }
function now() { return new Date().toISOString(); }

window.API = API;
