'use strict';

/* ============ утилиты ============ */
const $app = document.getElementById('app');
const STATUS = { processing: 'Обработка', draft_created: 'Черновик', confirmed: 'Подтверждено', failed: 'Ошибка' };
const STAGES = {
  queued: 'В очереди',
  diarizing: 'Определяем, кто говорит',
  transcribing: 'Распознаём речь',
  structuring: 'Разбираем диалог и роли',
  generating: 'Готовим заключение и памятку',
};
const AUDIO_STAGES = ['queued', 'diarizing', 'transcribing', 'structuring', 'generating'];
const TEXT_STAGES = ['queued', 'generating'];
const SECTIONS = [
  ['complaints', 'Жалобы'], ['anamnesis', 'Анамнез'], ['symptoms_duration', 'Симптомы и сроки'],
  ['examination', 'Объективные данные'], ['diagnosis', 'Диагноз'], ['treatment_plan', 'План лечения'],
  ['recommendations', 'Рекомендации'],
];

const state = {
  token: sessionStorage.getItem('aqyl_token'),
  user: JSON.parse(sessionStorage.getItem('aqyl_user') || 'null'),
};
let cleanup = null; // таймеры и обработчики текущей страницы

/** Создание DOM без innerHTML: любые данные (в т.ч. речь пациента) вставляются только как текст. */
function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  let value;
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'value') value = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  if (value !== undefined) el.value = value;
  return el;
}

function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z');
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}
const money = (v) => '$' + Number(v).toFixed(4);

function toast(message, bad) {
  const el = h('div', { class: 'toast' + (bad ? ' bad' : '') }, message);
  document.getElementById('toasts').append(el);
  setTimeout(() => el.remove(), bad ? 7000 : 3500);
}

class ApiError extends Error {
  constructor(status, message, code) { super(message); this.status = status; this.code = code; }
}

async function api(path, { method = 'GET', body, form, raw } = {}) {
  const headers = {};
  if (state.token) headers.Authorization = 'Bearer ' + state.token;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
  let res;
  try { res = await fetch('/api' + path, { method, headers, body: payload }); }
  catch { throw new ApiError(0, 'Нет связи с сервером. Проверьте подключение.'); }
  if (res.status === 401 && state.token) { logout(true); throw new ApiError(401, 'Сессия истекла. Войдите снова.'); }
  if (!res.ok) {
    let msg = 'Ошибка ' + res.status, code;
    try {
      const data = await res.json();
      const d = data.detail;
      if (typeof d === 'string') msg = d;
      else if (d && d.message) { msg = d.message; code = d.code; }
      else if (Array.isArray(d) && d[0]) msg = 'Проверьте поля формы: ' + (d[0].msg || '');
    } catch { /* тело не JSON */ }
    throw new ApiError(res.status, msg, code);
  }
  if (res.status === 204) return null;
  return raw ? res : res.json();
}

function logout(expired) {
  state.token = null; state.user = null;
  sessionStorage.removeItem('aqyl_token'); sessionStorage.removeItem('aqyl_user');
  location.hash = '#/login';
  if (expired) toast('Сессия истекла. Войдите снова.', true);
}

function confirmDialog({ title, body, okText = 'Подтвердить', danger }) {
  return new Promise((resolve) => {
    const dlg = h('dialog', null,
      h('h2', null, title), h('div', { class: 'dlg-body' }, body),
      h('div', { class: 'row' },
        h('button', { class: 'btn', onclick: () => dlg.close('no') }, 'Отмена'),
        h('button', { class: 'btn ' + (danger ? 'danger' : 'primary'), onclick: () => dlg.close('yes') }, okText)));
    dlg.addEventListener('close', () => { dlg.remove(); resolve(dlg.returnValue === 'yes'); });
    document.body.append(dlg);
    dlg.showModal();
  });
}

function autosize(t) { t.style.height = 'auto'; t.style.height = t.scrollHeight + 'px'; }

function badge(status) { return h('span', { class: 'badge ' + status }, STATUS[status] || status); }

async function download(path, filename) {
  const res = await api(path, { raw: true });
  const url = URL.createObjectURL(await res.blob());
  const a = h('a', { href: url, download: filename });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

/* ============ каркас ============ */
function shell(active, ...content) {
  const navItem = (href, label, key) => h('a', { href, 'aria-current': active === key ? 'page' : null }, label);
  return h('div', null,
    h('header', { class: 'topbar' },
      h('a', { class: 'brand', href: '#/' }, 'Aqyl', h('span', null, 'Med'), ' AI'),
      h('nav', { class: 'nav' },
        navItem('#/', 'Приёмы', 'list'), navItem('#/new', 'Новый приём', 'new'),
        state.user.role === 'admin' ? navItem('#/admin', 'Администрирование', 'admin') : null),
      h('div', { class: 'who' }, state.user.full_name,
        h('button', { onclick: () => logout(false) }, 'Выйти'))),
    h('main', { class: 'page' }, content));
}

function mount(node) { $app.replaceChildren(node); window.scrollTo(0, 0); }

/* ============ вход ============ */
function loginPage() {
  const err = h('div', { class: 'error-text', role: 'alert' });
  const email = h('input', { type: 'email', required: true, autocomplete: 'username' });
  const password = h('input', { type: 'password', required: true, autocomplete: 'current-password' });
  const btn = h('button', { class: 'btn primary', type: 'submit' }, 'Войти');
  const form = h('form', {
    class: 'card narrow',
    onsubmit: async (e) => {
      e.preventDefault(); err.textContent = ''; btn.disabled = true;
      try {
        const data = await api('/auth/login', { method: 'POST', body: { email: email.value, password: password.value } });
        state.token = data.access_token; state.user = data.user;
        sessionStorage.setItem('aqyl_token', state.token); sessionStorage.setItem('aqyl_user', JSON.stringify(state.user));
        location.hash = '#/';
      } catch (ex) { err.textContent = ex.message; } finally { btn.disabled = false; }
    },
  },
    h('h1', null, 'AqylMed AI'),
    h('p', { class: 'muted' }, 'Помощник врача: превращает запись приёма в черновик заключения.'),
    h('label', { class: 'field' }, h('span', null, 'Email'), email),
    h('label', { class: 'field' }, h('span', null, 'Пароль'), password),
    err, btn);
  mount(h('div', { class: 'page' }, form));
  email.focus();
}

/* ============ список приёмов ============ */
async function listPage() {
  const search = h('input', { type: 'search', placeholder: 'Поиск по пациенту или врачу' });
  const filter = h('select', { 'aria-label': 'Статус' },
    h('option', { value: '' }, 'Все статусы'),
    ...Object.entries(STATUS).map(([v, l]) => h('option', { value: v }, l)));
  const holder = h('div');
  mount(shell('list',
    h('div', { class: 'page-head' }, h('h1', null, 'Приёмы'), h('a', { class: 'btn primary', href: '#/new' }, 'Новый приём')),
    h('div', { class: 'toolbar' }, search, filter), holder));

  let timer, debounce;
  const load = async () => {
    try {
      const q = new URLSearchParams({ limit: '100' });
      if (search.value.trim()) q.set('q', search.value.trim());
      if (filter.value) q.set('status', filter.value);
      const data = await api('/consultations?' + q);
      holder.replaceChildren(data.items.length ? table(data.items) : h('div', { class: 'card empty' },
        search.value || filter.value ? 'Ничего не найдено.' : 'Приёмов пока нет. Загрузите запись или вставьте текст разговора.'));
      clearTimeout(timer);
      if (data.items.some((c) => c.status === 'processing')) timer = setTimeout(load, 4000);
    } catch (ex) { holder.replaceChildren(h('div', { class: 'alert bad' }, ex.message)); }
  };
  search.addEventListener('input', () => { clearTimeout(debounce); debounce = setTimeout(load, 300); });
  filter.addEventListener('change', load);
  cleanup = () => { clearTimeout(timer); clearTimeout(debounce); };
  load();

  function table(items) {
    return h('div', { class: 'scroll-x' }, h('table', { class: 'rows' },
      h('thead', null, h('tr', null, ['Дата приёма', 'Пациент', 'Врач', 'Источник', 'Статус'].map((t) => h('th', null, t)))),
      h('tbody', null, items.map((c) => h('tr', {
        class: 'click', tabindex: '0',
        onclick: () => (location.hash = '#/c/' + c.id),
        onkeydown: (e) => { if (e.key === 'Enter') location.hash = '#/c/' + c.id; },
      },
        h('td', null, c.consultation_date), h('td', null, c.patient_name), h('td', null, c.doctor_name),
        h('td', null, c.source === 'audio' ? 'Аудио' : 'Текст'), h('td', null, badge(c.status)))))));
  }
}

/* ============ новый приём ============ */
function newPage() {
  let mode = 'audio', recorded = null, recorder = null, stream = null, tick = null;
  const patient = h('input', { type: 'text', required: true, maxlength: '255', placeholder: 'Фамилия И. О.' });
  const date = h('input', { type: 'date', required: true, value: new Date().toISOString().slice(0, 10) });
  const fileInput = h('input', { type: 'file', accept: 'audio/*,.mp3,.m4a,.wav,.ogg,.webm,.flac,.mp4' });
  const text = h('textarea', { rows: '12', placeholder: 'Врач: Здравствуйте, что вас беспокоит?\nПациент: …' });
  const consent = h('input', { type: 'checkbox' });
  const err = h('div', { class: 'error-text', role: 'alert' });
  const submit = h('button', { class: 'btn primary', type: 'submit' }, 'Создать черновик заключения');
  const modeBox = h('div');
  const seg = h('div', { class: 'segmented', role: 'group', 'aria-label': 'Источник разговора' });

  const recLabel = h('span', { class: 'muted' }, 'Запись с микрофона');
  const dot = h('span', { class: 'rec-dot' });
  const recBtn = h('button', { type: 'button', class: 'btn', onclick: toggleRecord }, 'Начать запись');
  const preview = h('audio', { controls: true, hidden: true });

  function drawMode() {
    seg.replaceChildren(
      h('button', { type: 'button', 'aria-pressed': mode === 'audio', onclick: () => { mode = 'audio'; drawMode(); } }, 'Аудиозапись'),
      h('button', { type: 'button', 'aria-pressed': mode === 'text', onclick: () => { mode = 'text'; drawMode(); } }, 'Готовый текст'));
    modeBox.replaceChildren(mode === 'audio'
      ? h('div', null,
        h('div', { class: 'recorder' }, dot, recLabel, recBtn),
        preview,
        h('label', { class: 'field' }, h('span', null, 'Или загрузите файл'), fileInput,
          h('div', { class: 'help' }, 'WAV, MP3, M4A, OGG, FLAC, WebM. Обработка занимает 1–3 минуты.')),
        h('label', { class: 'field' }, h('span', null, 'Согласие'),
          h('label', null, consent, ' Пациент дал согласие на запись и обработку разговора')))
      : h('label', { class: 'field' }, h('span', null, 'Текст разговора'), text,
        h('div', { class: 'help' }, 'Каждую реплику с новой строки, с пометкой «Врач:» или «Пациент:».')));
  }

  async function toggleRecord() {
    if (recorder && recorder.state === 'recording') { recorder.stop(); return; }
    if (!navigator.mediaDevices || !window.MediaRecorder) { err.textContent = 'Браузер не поддерживает запись. Загрузите готовый файл.'; return; }
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch { err.textContent = 'Нет доступа к микрофону. Разрешите его в браузере (нужен HTTPS или localhost).'; return; }
    err.textContent = '';
    const chunks = [];
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    recorder.onstop = () => {
      clearInterval(tick); stream.getTracks().forEach((t) => t.stop()); dot.classList.remove('live');
      const type = recorder.mimeType || 'audio/webm';
      const ext = type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : 'webm';
      recorded = new File(chunks, 'recording.' + ext, { type });
      preview.src = URL.createObjectURL(recorded); preview.hidden = false;
      recBtn.textContent = 'Записать заново'; recLabel.textContent = 'Запись готова';
    };
    recorder.start(); dot.classList.add('live'); recBtn.textContent = 'Остановить';
    const t0 = Date.now();
    tick = setInterval(() => {
      const s = Math.floor((Date.now() - t0) / 1000);
      recLabel.textContent = `Идёт запись ${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
    }, 500);
  }

  const form = h('form', {
    class: 'card',
    onsubmit: async (e) => {
      e.preventDefault(); err.textContent = ''; submit.disabled = true;
      try {
        let res;
        if (mode === 'audio') {
          const file = fileInput.files[0] || recorded;
          if (!file) throw new Error('Запишите разговор или выберите файл.');
          if (!consent.checked) throw new Error('Подтвердите согласие пациента на запись.');
          const fd = new FormData();
          fd.append('patient_name', patient.value); fd.append('consultation_date', date.value);
          fd.append('consent_confirmed', 'true'); fd.append('file', file, file.name);
          res = await api('/consultations/audio', { method: 'POST', form: fd });
        } else {
          res = await api('/consultations/text', { method: 'POST',
            body: { patient_name: patient.value, consultation_date: date.value, dialogue_text: text.value } });
        }
        location.hash = '#/c/' + res.id;
      } catch (ex) { err.textContent = ex.message; submit.disabled = false; }
    },
  },
    seg,
    h('div', { class: 'grid-2' },
      h('label', { class: 'field' }, h('span', null, 'Пациент'), patient),
      h('label', { class: 'field' }, h('span', null, 'Дата приёма'), date)),
    modeBox, err, submit);
  drawMode();
  cleanup = () => { clearInterval(tick); if (stream) stream.getTracks().forEach((t) => t.stop()); };
  mount(shell('new',
    h('div', { class: 'page-head' }, h('h1', null, 'Новый приём')),
    h('div', null, form),
    h('p', { class: 'muted small' }, 'Результат — черновик. Он не попадает в карту, пока вы его не проверите и не подтвердите.')));
}

/* ============ страница приёма ============ */
async function detailPage(id) {
  mount(shell('', h('div', { class: 'muted' }, 'Загрузка…')));
  let c;
  try { c = await api('/consultations/' + id); }
  catch (ex) { mount(shell('', h('div', { class: 'alert bad' }, ex.message), h('a', { href: '#/' }, 'К списку приёмов'))); return; }
  if (c.status === 'processing') return processingView(c);
  renderDetail(c);
}

function processingView(c) {
  const order = c.source === 'audio' ? AUDIO_STAGES : TEXT_STAGES;
  const list = h('ul', { class: 'stages' });
  const draw = (stage) => {
    const idx = order.indexOf(stage);
    list.replaceChildren(...order.map((s, i) => h('li', { class: i < idx ? 'done' : i === idx ? 'now' : '' }, STAGES[s])));
  };
  draw(c.progress_stage);
  mount(shell('',
    h('div', { class: 'page-head' }, h('div', { class: 'title-row' }, h('h1', null, c.patient_name), badge('processing'))),
    h('div', { class: 'card' }, h('h2', null, 'Готовим черновик'),
      h('p', { class: 'muted' }, 'Страницу можно закрыть — обработка продолжится на сервере.'), list)));
  let stopped = false;
  const poll = async () => {
    if (stopped) return;
    try {
      const s = await api(`/consultations/${c.id}/status`);
      if (s.status !== 'processing') { detailPage(c.id); return; }
      draw(s.progress_stage);
    } catch (ex) { if (ex.status === 404) return; }
    if (!stopped) setTimeout(poll, 2000);
  };
  setTimeout(poll, 1500);
  cleanup = () => { stopped = true; };
}

function parseTurns(textValue) {
  const turns = [];
  for (const line of (textValue || '').split('\n')) {
    const m = line.match(/^\s*(Врач|Пациент|Неизвестный)\s*:\s*(.*)$/);
    if (m) turns.push({ role: m[1], text: m[2] });
    else if (line.trim()) { if (turns.length) turns[turns.length - 1].text += ' ' + line.trim(); else turns.push({ role: '', text: line.trim() }); }
  }
  return turns;
}

function renderDetail(c) {
  const editable = c.can_edit;
  const doc = c.document || {};
  const fields = {}; // имя -> textarea
  let memoArea = null;
  let dirty = false;
  let tab = 'dialogue';
  let audioUrl = null;

  const markDirty = () => { dirty = true; saveBtn.disabled = false; saveBtn.textContent = 'Сохранить правки'; };
  const area = (value, onInput) => {
    const t = h('textarea', { rows: '2', oninput: () => { autosize(t); markDirty(); onInput && onInput(); } }, value || '');
    t.value = value || '';
    requestAnimationFrame(() => autosize(t));
    return t;
  };

  const flagged = new Set();
  if (editable && doc.diagnosis && /не указан/i.test(doc.diagnosis)) flagged.add('diagnosis');

  const sheetSections = c.document ? SECTIONS.map(([key, title]) => {
    const body = editable
      ? (fields[key] = area(doc[key]))
      : h('div', { class: 'body' }, doc[key] || 'не указано');
    return h('div', { class: 'section' + (flagged.has(key) ? ' flag' : '') }, h('h3', null, title), body);
  }) : [];
  if (c.document) {
    const miss = editable ? (fields.missing_information = area((doc.missing_information || []).join('\n'))) :
      h('div', { class: 'body' }, (doc.missing_information || []).join('\n') || 'нет');
    sheetSections.push(h('div', { class: 'section' + (editable && (doc.missing_information || []).length ? ' flag' : '') },
      h('h3', null, 'Требует уточнения'), miss,
      editable ? h('div', { class: 'help' }, 'По одному пункту в строке.') : null));
  }

  const memoBlock = c.memo ? h('div', { class: 'memo' }, h('h2', null, 'Памятка пациенту'),
    editable ? (memoArea = area(c.memo.memo_text)) : h('div', { class: 'body' }, c.memo.memo_text)) : null;
  if (memoBlock && !editable) memoBlock.lastChild.style.whiteSpace = 'pre-wrap';

  const sheet = h('article', { class: 'sheet' },
    h('div', { class: 'sheet-head' },
      h('div', null, h('h1', null, 'Медицинское заключение'),
        h('div', { class: 'sheet-meta' }, h('b', null, c.patient_name), ' — приём ', c.consultation_date)),
      h('div', { class: 'sheet-meta' }, 'Врач: ', h('b', null, c.doctor_name), h('br'),
        c.status === 'confirmed' ? `Подтверждено: ${c.confirmed_by || ''}, ${fmtDate(c.confirmed_at)}` : 'Черновик, не подтверждён')),
    sheetSections, memoBlock,
    h('p', { class: 'disclaimer' }, 'Подготовлено с помощью AqylMed AI. Документ должен быть проверен врачом.'));

  /* ---- панель действий ---- */
  const saveBtn = h('button', { class: 'btn', disabled: true, onclick: save }, 'Сохранено');
  const confirmBtn = h('button', { class: 'btn ok', onclick: confirmDoc }, 'Подтвердить заключение');
  const actions = h('div', { class: 'actionbar' },
    h('a', { class: 'btn', href: '#/' }, 'К списку'),
    editable ? [saveBtn, confirmBtn] : null,
    c.status === 'confirmed' ? h('button', { class: 'btn', onclick: reopen }, 'Вернуть к редактированию') : null,
    h('span', { class: 'spacer' }),
    c.document ? [
      h('button', { class: 'btn', onclick: () => download(`/consultations/${c.id}/export?format=docx`, `zaklyuchenie_${c.id}.docx`).catch((e) => toast(e.message, true)) }, 'Скачать Word'),
      h('button', { class: 'btn', onclick: () => window.print() }, 'Печать'),
    ] : null);

  async function save(silent) {
    try {
      let updated = c;
      const body = {};
      for (const [key] of SECTIONS) if (fields[key] && fields[key].value !== (doc[key] || '')) body[key] = fields[key].value;
      if (fields.missing_information) {
        const list = fields.missing_information.value.split('\n').map((s) => s.trim()).filter(Boolean);
        if (list.join('\n') !== (doc.missing_information || []).join('\n')) body.missing_information = list;
      }
      if (Object.keys(body).length) updated = await api(`/consultations/${c.id}/document`, { method: 'PUT', body });
      if (memoArea && memoArea.value !== c.memo.memo_text) updated = await api(`/consultations/${c.id}/memo`, { method: 'PUT', body: { memo_text: memoArea.value } });
      dirty = false; saveBtn.disabled = true; saveBtn.textContent = 'Сохранено';
      Object.assign(c, updated); Object.assign(doc, updated.document || {}); if (c.memo && updated.memo) c.memo.memo_text = updated.memo.memo_text;
      if (silent !== true) toast('Правки сохранены');
      return true;
    } catch (ex) { toast(ex.message, true); return false; }
  }

  async function confirmDoc() {
    const warnings = (doc.validation_warnings || []);
    const ok = await confirmDialog({
      title: 'Подтвердить заключение?',
      okText: 'Подтверждаю',
      body: h('div', null,
        h('p', null, 'Вы подтверждаете, что проверили текст и несёте ответственность за его содержание.'),
        warnings.length ? h('div', { class: 'alert warn' }, `Остались непроверенные значения (${warnings.length}). Откройте вкладку «Проверка».`) : null),
    });
    if (!ok) return;
    if (dirty && !(await save(true))) return;
    try { renderDetail(await api(`/consultations/${c.id}/confirm`, { method: 'POST' })); toast('Заключение подтверждено'); }
    catch (ex) { toast(ex.message, true); }
  }
  async function reopen() {
    if (!(await confirmDialog({ title: 'Вернуть к редактированию?', body: 'Подтверждение будет снято, действие попадёт в журнал.', okText: 'Вернуть' }))) return;
    try { renderDetail(await api(`/consultations/${c.id}/reopen`, { method: 'POST' })); } catch (ex) { toast(ex.message, true); }
  }

  async function regenerate() {
    const run = async (confirmOverwrite) => api(`/consultations/${c.id}/regenerate`, { method: 'POST', body: { confirm_overwrite: confirmOverwrite } });
    try {
      try { await run(dirty); }
      catch (ex) {
        if (ex.code !== 'edits_would_be_lost') throw ex;
        if (!(await confirmDialog({ title: 'Заменить правки?', body: 'Новый черновик заменит текст заключения и памятки, который вы уже исправили.', okText: 'Заменить', danger: true }))) return;
        await run(true);
      }
      detailPage(c.id);
    } catch (ex) { toast(ex.message, true); }
  }

  /* ---- боковая панель ---- */
  const panel = h('div', { class: 'tabpanel' });
  const tabs = h('div', { class: 'tabs', role: 'tablist' });
  const warningCount = (doc.validation_warnings || []).length;
  function drawTabs() {
    const mk = (key, label, count) => h('button', { role: 'tab', 'aria-selected': tab === key, onclick: () => { tab = key; drawTabs(); drawPanel(); } },
      label, count ? h('span', { class: 'tab-count' }, count) : null);
    tabs.replaceChildren(mk('dialogue', 'Диалог'), mk('audio', 'Запись'), mk('check', 'Проверка', warningCount || null));
  }

  function drawPanel() {
    if (tab === 'dialogue') panel.replaceChildren(dialogueTab());
    else if (tab === 'audio') panel.replaceChildren(audioTab());
    else panel.replaceChildren(checkTab());
  }

  function dialogueTab() {
    const wrap = h('div', { class: 'dialogue' });
    const canEditDialogue = c.status === 'draft_created' || c.status === 'failed';
    const view = h('div');
    const drawView = () => view.replaceChildren(...(parseTurns(c.dialogue_text).length
      ? parseTurns(c.dialogue_text).map((t) => h('div', { class: 'turn' + (t.role === 'Врач' ? ' doc' : '') }, t.role ? h('b', null, t.role) : null, t.text))
      : [h('p', { class: 'muted' }, 'Диалог недоступен.')]));
    drawView();
    wrap.append(view);
    if (canEditDialogue && c.dialogue_text) {
      const edit = h('textarea', { rows: '14' }); edit.value = c.dialogue_text; edit.hidden = true;
      const btnEdit = h('button', { class: 'btn', onclick: () => { edit.hidden = !edit.hidden; view.hidden = !edit.hidden; btnEdit.textContent = edit.hidden ? 'Править текст' : 'Закрыть редактор'; btnSave.hidden = edit.hidden; } }, 'Править текст');
      const btnSave = h('button', { class: 'btn', hidden: true, onclick: async () => {
        try { Object.assign(c, await api(`/consultations/${c.id}/dialogue`, { method: 'PUT', body: { dialogue_text: edit.value } })); drawView(); edit.hidden = true; view.hidden = false; btnSave.hidden = true; btnEdit.textContent = 'Править текст'; toast('Диалог сохранён. Нажмите «Обновить заключение».'); }
        catch (ex) { toast(ex.message, true); } } }, 'Сохранить диалог');
      const btnSwap = h('button', { class: 'btn', onclick: async () => {
        try { Object.assign(c, await api(`/consultations/${c.id}/swap-roles`, { method: 'POST' })); edit.value = c.dialogue_text; drawView(); toast('Роли «Врач» и «Пациент» поменялись местами'); }
        catch (ex) { toast(ex.message, true); } } }, 'Поменять роли');
      wrap.append(edit, h('div', { class: 'toolbar' }, btnEdit, btnSave, btnSwap),
        h('div', { class: 'help' }, 'Если ИИ перепутал, кто врач, а кто пациент, поменяйте роли и обновите заключение.'),
        h('button', { class: 'btn primary', onclick: regenerate }, 'Обновить заключение по диалогу'));
    }
    return wrap;
  }

  function audioTab() {
    const box = h('div');
    if (!c.audio.available) {
      box.append(h('p', { class: 'muted' }, c.source === 'audio'
        ? `Запись удалена${c.audio.deleted_at ? ' ' + fmtDate(c.audio.deleted_at) : ''} (срок хранения или по запросу).`
        : 'Приём создан из текста, аудио нет.'));
      return box;
    }
    const player = h('audio', { controls: true, preload: 'none' });
    const load = h('button', { class: 'btn', onclick: async () => {
      load.disabled = true;
      try { const res = await api(`/consultations/${c.id}/audio`, { raw: true }); audioUrl = URL.createObjectURL(await res.blob()); player.src = audioUrl; player.play(); load.hidden = true; }
      catch (ex) { toast(ex.message, true); load.disabled = false; } } }, 'Загрузить запись для прослушивания');
    box.append(h('p', { class: 'muted small' }, `Длительность: ${c.audio.duration_seconds ? Math.round(c.audio.duration_seconds / 60 * 10) / 10 + ' мин' : '—'}. Каждое прослушивание фиксируется в журнале.`), player, load);
    if (c.status !== 'processing') {
      box.append(h('div', null, h('button', { class: 'btn danger', onclick: async () => {
        if (!(await confirmDialog({ title: 'Удалить аудиозапись?', body: 'Файл будет удалён без возможности восстановления. Текст и заключение сохранятся.', okText: 'Удалить', danger: true }))) return;
        try { await api(`/consultations/${c.id}/audio`, { method: 'DELETE' }); c.audio.available = false; c.audio.deleted_at = new Date().toISOString(); drawPanel(); toast('Запись удалена'); }
        catch (ex) { toast(ex.message, true); } } }, 'Удалить запись')));
    }
    return box;
  }

  function checkTab() {
    const box = h('div');
    const w = doc.validation_warnings || [];
    box.append(w.length
      ? h('div', { class: 'alert warn' }, h('b', null, 'Проверьте значения по записи'), h('ul', null, w.map((x) => h('li', null, x))))
      : h('div', { class: 'alert ok' }, 'Все числа и дозировки из заключения найдены в диалоге.'));
    if (!c.dialogue_text) box.append(h('p', { class: 'muted' }, 'Нет диалога для сверки.'));
    if ((doc.missing_information || []).length) box.append(h('div', { class: 'alert info' }, h('b', null, 'ИИ не нашёл в разговоре'), h('ul', null, doc.missing_information.map((x) => h('li', null, x)))));
    if (c.transcript_notes) box.append(h('div', { class: 'alert info' }, h('b', null, 'Заметки по расшифровке'), h('div', { class: 'small' }, c.transcript_notes.split('\n').map((l) => h('div', null, l)))));
    box.append(h('p', { class: 'muted small' }, 'Проверка автоматическая и не заменяет вашу: она ищет только числа с единицами измерения.'));
    return box;
  }

  /* ---- сборка ---- */
  const banner = c.status === 'failed'
    ? h('div', { class: 'alert bad banner' }, h('b', null, 'Обработка не удалась. '), c.error_message || '', ' ',
      h('button', { class: 'btn', onclick: regenerate }, 'Повторить обработку'))
    : null;

  const side = h('aside', { class: 'side' }, tabs, panel);
  drawTabs(); drawPanel();
  cleanup = () => { if (audioUrl) URL.revokeObjectURL(audioUrl); window.onbeforeunload = null; };
  window.onbeforeunload = () => (dirty ? 'Есть несохранённые правки' : undefined);

  mount(shell('',
    h('div', { class: 'page-head' }, h('div', { class: 'title-row' }, h('h1', null, c.patient_name), badge(c.status))),
    banner,
    c.document
      ? h('div', null, h('div', { class: 'detail' }, sheet, side), actions)
      : h('div', { class: 'detail' }, h('div', { class: 'card' }, 'Заключение ещё не создано.'), side)));
}

/* ============ администрирование ============ */
async function adminPage() {
  let tab = 'usage';
  const body = h('div');
  const tabs = h('div', { class: 'segmented' });
  const draw = () => {
    tabs.replaceChildren(...[['usage', 'Расходы'], ['users', 'Пользователи'], ['audit', 'Журнал'], ['system', 'Система']]
      .map(([k, l]) => h('button', { 'aria-pressed': tab === k, onclick: () => { tab = k; draw(); } }, l)));
    body.replaceChildren(h('div', { class: 'muted' }, 'Загрузка…'));
    ({ usage: usageTab, users: usersTab, audit: auditTab, system: systemTab })[tab]().then((n) => body.replaceChildren(n))
      .catch((ex) => body.replaceChildren(h('div', { class: 'alert bad' }, ex.message)));
  };
  mount(shell('admin', h('div', { class: 'page-head' }, h('h1', null, 'Администрирование')), tabs, body));
  draw();

  async function usageTab() {
    const month = h('input', { type: 'text', value: new Date().toISOString().slice(0, 7), pattern: '\\d{4}-\\d{2}', 'aria-label': 'Месяц ГГГГ-ММ' });
    const holder = h('div');
    const load = async () => {
      const s = await api('/admin/usage?month=' + encodeURIComponent(month.value));
      const max = Math.max(...s.by_day.map((d) => d.cost_usd), 0.000001);
      holder.replaceChildren(
        h('div', { class: 'kpis' },
          h('div', { class: 'kpi' }, h('div', { class: 'muted small' }, 'Расходы за месяц'), h('div', { class: 'v' }, money(s.total_cost_usd)),
            s.budget_usd ? h('div', { class: 'bar' + (s.budget_used_percent >= 90 ? ' hot' : '') }, h('i', { 'data-w': Math.min(100, s.budget_used_percent) })) : null,
            h('div', { class: 'small muted' }, s.budget_usd ? `Лимит $${s.budget_usd.toFixed(2)}, использовано ${s.budget_used_percent}%` : 'Лимит не задан')),
          h('div', { class: 'kpi' }, h('div', { class: 'muted small' }, 'Обработано приёмов'), h('div', { class: 'v' }, s.consultations_processed)),
          h('div', { class: 'kpi' }, h('div', { class: 'muted small' }, 'Средняя стоимость приёма'), h('div', { class: 'v' }, s.avg_cost_per_consultation_usd == null ? '—' : money(s.avg_cost_per_consultation_usd)))),
        h('div', { class: 'scroll-x' }, h('table', { class: 'rows' },
          h('thead', null, h('tr', null, ['Тип', 'Провайдер', 'Модель', 'Минут аудио', 'Токены вход / выход', 'Стоимость'].map((t) => h('th', null, t)))),
          h('tbody', null, s.by_model.length ? s.by_model.map((m) => h('tr', null, h('td', null, m.kind === 'stt' ? 'Речь' : 'Текст'), h('td', null, m.provider), h('td', null, m.model),
            h('td', null, m.audio_minutes || '—'), h('td', null, m.kind === 'llm' ? `${m.input_tokens} / ${m.output_tokens}` : '—'), h('td', null, money(m.cost_usd))))
            : h('tr', null, h('td', { colspan: '6', class: 'empty' }, 'За этот месяц расходов нет'))))),
        s.by_day.length ? h('p', { class: 'muted small' }, 'По дням: ' + s.by_day.map((d) => `${d.day.slice(8)}-е — ${money(d.cost_usd)}`).join('; ')) : null);
      holder.querySelectorAll('i[data-w]').forEach((i) => { i.style.width = i.dataset.w + '%'; });
      void max;
    };
    month.addEventListener('change', () => load().catch((e) => toast(e.message, true)));
    await load();
    return h('div', null, h('label', { class: 'field' }, h('span', null, 'Месяц (ГГГГ-ММ)'), month), holder);
  }

  async function usersTab() {
    const users = await api('/admin/users');
    const err = h('div', { class: 'error-text', role: 'alert' });
    const f = { email: h('input', { type: 'email', required: true }), name: h('input', { type: 'text', required: true }),
      pass: h('input', { type: 'password', required: true, autocomplete: 'new-password' }),
      role: h('select', null, h('option', { value: 'doctor' }, 'Врач'), h('option', { value: 'admin' }, 'Администратор')) };
    const form = h('form', { class: 'card', onsubmit: async (e) => {
      e.preventDefault(); err.textContent = '';
      try { await api('/admin/users', { method: 'POST', body: { email: f.email.value, full_name: f.name.value, password: f.pass.value, role: f.role.value } }); toast('Пользователь создан'); draw(); }
      catch (ex) { err.textContent = ex.message; } } },
      h('h2', null, 'Новый пользователь'),
      h('div', { class: 'inline-form' }, h('label', { class: 'field' }, h('span', null, 'Email'), f.email), h('label', { class: 'field' }, h('span', null, 'ФИО'), f.name),
        h('label', { class: 'field' }, h('span', null, 'Пароль'), f.pass), h('label', { class: 'field' }, h('span', null, 'Роль'), f.role),
        h('button', { class: 'btn primary', type: 'submit' }, 'Создать')), err);
    const table = h('div', { class: 'scroll-x' }, h('table', { class: 'rows' },
      h('thead', null, h('tr', null, ['Email', 'ФИО', 'Роль', 'Последний вход', ''].map((t) => h('th', null, t)))),
      h('tbody', null, users.map((u) => h('tr', null, h('td', null, u.email), h('td', null, u.full_name), h('td', null, u.role === 'admin' ? 'Администратор' : 'Врач'),
        h('td', null, fmtDate(u.last_login_at) || '—'),
        h('td', null, h('button', { class: 'btn' + (u.is_active ? ' danger' : ''), onclick: async () => {
          try { await api('/admin/users/' + u.id, { method: 'PATCH', body: { is_active: !u.is_active } }); draw(); } catch (ex) { toast(ex.message, true); } } }, u.is_active ? 'Отключить' : 'Включить')))))));
    return h('div', { class: 'stack' }, form, table);
  }

  async function auditTab() {
    const data = await api('/admin/audit?limit=200');
    return h('div', { class: 'scroll-x' }, h('table', { class: 'rows' },
      h('thead', null, h('tr', null, ['Время', 'Пользователь', 'Действие', 'Объект', 'Детали', 'IP'].map((t) => h('th', null, t)))),
      h('tbody', null, data.items.map((a) => h('tr', null, h('td', null, fmtDate(a.created_at)), h('td', null, a.user_email || '—'), h('td', null, a.action),
        h('td', null, a.entity_type ? `${a.entity_type} #${a.entity_id ?? ''}` : '—'), h('td', { class: 'small' }, a.details || ''), h('td', { class: 'small' }, a.ip_address || ''))))));
  }

  async function systemTab() {
    const s = await api('/admin/system');
    const row = (label, ok, extra) => h('tr', null, h('td', null, label), h('td', null, ok === null ? extra : h('span', { class: 'badge ' + (ok ? 'confirmed' : 'failed') }, ok ? 'Да' : 'Нет'), ok !== null && extra ? ' ' + extra : ''));
    return h('div', { class: 'stack' },
      h('table', { class: 'rows' }, h('tbody', null,
        row('Распознавание речи', s.stt_key_configured, `${s.stt_provider}: ${s.stt_model}`),
        row('Языковая модель', s.llm_key_configured, s.llm_model),
        row('Диаризация (кто говорит)', s.diarization_enabled ? s.hf_token_configured : null, s.diarization_enabled ? '' : 'выключена, роли определяет языковая модель'),
        row('ffmpeg установлен', s.ffmpeg_available),
        row('Хранение аудио', null, s.audio_retention_days ? `${s.audio_retention_days} дн.` : 'без ограничения'),
        row('Удалять аудио после обработки', s.delete_audio_after_processing),
        row('Месячный лимит расходов', null, s.monthly_budget_usd ? '$' + s.monthly_budget_usd : 'не задан'))),
      h('div', null, h('button', { class: 'btn', onclick: async () => {
        try { const r = await api('/admin/retention/purge', { method: 'POST' }); toast(`Удалено записей: ${r.deleted_files}`); } catch (ex) { toast(ex.message, true); } } }, 'Удалить просроченные аудиозаписи сейчас')));
  }
}

/* ============ маршрутизация ============ */
function route() {
  if (cleanup) { cleanup(); cleanup = null; }
  const hash = location.hash || '#/';
  if (!state.token) { if (hash !== '#/login') { location.hash = '#/login'; return; } return loginPage(); }
  if (hash === '#/login') { location.hash = '#/'; return; }
  let m;
  if (hash === '#/') return listPage();
  if (hash === '#/new') return newPage();
  if ((m = hash.match(/^#\/c\/(\d+)$/))) return detailPage(Number(m[1]));
  if (hash === '#/admin' && state.user.role === 'admin') return adminPage();
  location.hash = '#/';
}
window.addEventListener('hashchange', route);
route();
