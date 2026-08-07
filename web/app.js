/* NordRelay Mobile — 应用逻辑（T-0153 candidate 原型） */
(() => {
  let currentSession = null;

  const $ = (id) => document.getElementById(id);
  const views = { workspaces: $('view-workspaces'), session: $('view-session') };

  /* ── 工作区首页：按 /api/sessions 分组 ─────────────────────────── */
  async function loadWorkspaces() {
    const { sessions } = await API.listSessions();
    const groups = {};
    for (const s of sessions) (groups[s.workspace] = groups[s.workspace] || []).push(s);
    const list = $('workspace-list');
    list.innerHTML = '';
    for (const [ws, items] of Object.entries(groups)) {
      const sec = document.createElement('section');
      sec.className = 'group';
      sec.innerHTML = `<h2 class="group-title">${esc(ws)}</h2>`;
      for (const s of items) {
        const card = document.createElement('div');
        card.className = 'session-card' + (s.status === 'active' ? ' active' : '');
        card.innerHTML = `
          <div class="sc-title">${esc(s.title)}</div>
          <div class="sc-meta">${esc(s.model)} · ${esc(s.status)}</div>`;
        card.onclick = () => openSession(s.id);
        sec.appendChild(card);
      }
      list.appendChild(sec);
    }
  }

  /* ── 会话详情 ─────────────────────────────────────────────────── */
  async function openSession(id) {
    currentSession = await API.getSession(id);
    $('session-title').textContent = currentSession.title;
    $('session-model').textContent = currentSession.model;
    $('model-select').value = currentSession.model;
    renderMessages(currentSession.messages || []);
    show('session');
  }

  function renderMessages(msgs) {
    const box = $('messages');
    box.innerHTML = '';
    for (const m of msgs) {
      const el = document.createElement('div');
      el.className = 'msg ' + (m.role === 'user' ? 'user' : 'assistant');
      el.textContent = m.content;
      box.appendChild(el);
    }
    box.scrollTop = box.scrollHeight;
  }

  /* ── 操作：发消息 / abort / 切模型 ────────────────────────────── */
  async function send() {
    const input = $('input-msg');
    const content = input.value.trim();
    if (!content || !currentSession) return;
    input.value = '';
    await API.sendMessage(currentSession.id, content);
    const s = await API.getSession(currentSession.id);
    renderMessages(s.messages || []);
  }

  async function abort() {
    if (!currentSession) return;
    await API.abort(currentSession.id);
    toast('已发送 abort');
  }

  async function switchModel() {
    if (!currentSession) return;
    const model = $('model-select').value;
    await API.switchModel(currentSession.id, model);
    $('session-model').textContent = model;
    toast(`模型切换为 ${model}`);
  }

  /* ── SSE 实时事件 ─────────────────────────────────────────────── */
  function subscribe() {
    API.subscribeEvents((ev) => {
      if (ev.session_id === currentSession?.id) {
        if (ev.type === 'message') {
          const s = currentSession;
          s.messages = s.messages || [];
          s.messages.push({ role: ev.role, content: ev.content, ts: ev.ts });
          renderMessages(s.messages);
        }
      }
      toast(`${ev.type}: ${(ev.content || '').slice(0, 40)}`);
    });
  }

  /* ── UI 辅助 ──────────────────────────────────────────────────── */
  function show(name) {
    views.workspaces.classList.toggle('hidden', name !== 'workspaces');
    views.session.classList.toggle('hidden', name !== 'session');
  }

  let toastTimer;
  function toast(text) {
    const el = $('event-toast');
    el.textContent = text;
    el.classList.remove('hidden');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.add('hidden'), 2500);
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  /* ── 绑定 ─────────────────────────────────────────────────────── */
  $('btn-reload').onclick = loadWorkspaces;
  $('btn-back').onclick = () => { currentSession = null; show('workspaces'); };
  $('btn-send').onclick = send;
  $('input-msg').addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
  $('btn-abort').onclick = abort;
  $('model-select').onchange = switchModel;

  loadWorkspaces();
  subscribe();
})();
