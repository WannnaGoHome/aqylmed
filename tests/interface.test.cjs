const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('app/static/app.js', 'utf8');
const detailCode = source.slice(source.indexOf('function renderDetail('), source.indexOf('/* ============ администрирование'));
function setup(api) {
  const nodes = [], events = [], downloads = [], prompts = [];
  class Node {
    constructor(tag, props, children) {
      this.tag = tag; this.children = children.flat(Infinity); this.style = {};
      this.textContent = this.children.filter(x => typeof x === 'string').join('');
      this.value = ''; Object.assign(this, props || {}); nodes.push(this);
    }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    addEventListener(key, fn) { this['on' + key] = fn; }
  }
  const context = vm.createContext({
    h: (tag, props, ...children) => new Node(tag, props, children),
    SECTIONS: [['complaints', 'Жалобы']], TRANSLATIONS: {}, state: {locale:'ru'},
    api, rawText: x => String(x ?? ''), tr: x => x, toast: x => events.push(x),
    badge: x => x, parseTurns: () => [], fmtDate: x => x, autosize() {}, requestAnimationFrame() {},
    mount() {}, shell() {}, cleanup: null, hasUnsavedChanges: null,
    window: {addEventListener() {}, removeEventListener() {}, print() {}},
    confirmDialog: async value => { prompts.push(value); return false; },
    download: async (...args) => downloads.push(args), URL, detailPage() {},
  });
  vm.runInContext(detailCode, context);
  const c = {id:1, can_edit:true, status:'draft_created', document:{complaints:'old',missing_information:[]},
    dialogue_text:'Transcript', patient_name:'Test', doctor_name:'Test', audio:{available:false}};
  context.renderDetail(c);
  return {context, nodes, c, downloads, prompts, events,
    field: nodes.find(x => x.tag === 'textarea'),
    button: name => nodes.find(x => x.tag === 'button' && x.textContent === name)};
}

test('edits typed during save remain unsaved and duplicate clicks share one request', async () => {
  let resolve, calls = 0;
  const ui = setup(async () => { calls++; return new Promise(r => { resolve = r; }); });
  const button = ui.button('Сохранено');
  ui.field.value = 'first'; ui.field.oninput();
  const first = button.onclick(), second = button.onclick();
  assert.equal(first, second);
  await Promise.resolve();
  ui.field.value = 'second'; ui.field.oninput();
  resolve({...ui.c, document:{complaints:'first',missing_information:[]}});
  await first;
  assert.equal(calls, 1); assert.equal(ui.context.hasUnsavedChanges(), true);
  assert.equal(ui.field.value, 'second'); assert.equal(button.disabled, false);
});

test('reverted edits do not leave save permanently busy', async () => {
  let calls = 0;
  const ui = setup(async () => { calls++; return ui.c; });
  const button = ui.button('Сохранено');
  ui.field.value = 'old'; ui.field.oninput();
  await button.onclick();
  assert.equal(ui.context.hasUnsavedChanges(), false);
  assert.equal(calls, 0);
});

test('Word export waits for pending edits and does not export after a failed save', async () => {
  const sequence = [];
  const ui = setup(async () => { sequence.push('save'); return {...ui.c, document:{complaints:'new',missing_information:[]}}; });
  ui.field.value = 'new'; ui.field.oninput();
  await ui.button('Скачать Word').onclick();
  assert.deepEqual(sequence, ['save']); assert.equal(ui.downloads.length, 1);
  const failed = setup(async () => { throw new Error('offline'); });
  failed.field.value = 'new'; failed.field.oninput();
  await failed.button('Скачать Word').onclick();
  assert.equal(failed.downloads.length, 0); assert.equal(failed.context.hasUnsavedChanges(), true);
});

test('regeneration requires confirmation before discarding local changes', async () => {
  let calls = 0;
  const ui = setup(async () => { calls++; });
  ui.field.value = 'new'; ui.field.oninput();
  await ui.button('Обновить заключение по диалогу').onclick();
  assert.equal(ui.prompts.length, 1); assert.equal(calls, 0);
  assert.equal(ui.context.hasUnsavedChanges(), true);
});

test('pagination reaches later records and stale search responses cannot replace results', async () => {
  const nodes = [], requests = [], timers = [];
  class Node {
    constructor(tag, props, children) { this.tag = tag; this.value = ''; this.children = children.flat(Infinity); this.textContent = children.filter(x => typeof x === 'string').join(''); Object.assign(this, props || {}); nodes.push(this); }
    replaceChildren(...items) { this.children = items; }
    addEventListener(key, fn) { this['on' + key] = fn; }
    setAttribute() {} removeAttribute() {}
  }
  const context = vm.createContext({
    h: (tag, props, ...children) => new Node(tag, props, children), STATUS:{draft_created:'Черновик'},
    shell() {}, mount() {}, rawText:x=>x, badge:x=>x, tr:x=>x, URLSearchParams,
    api: path => new Promise(resolve => requests.push({path,resolve})),
    setTimeout: fn => { timers.push(fn); return timers.length; }, clearTimeout() {},
    cleanup:null, location:{},
  });
  const code = source.slice(source.indexOf('async function listPage()'), source.indexOf('/* ============ новый приём'));
  vm.runInContext(code, context); await context.listPage();
  const item = {id:1, patient_name:'Old', doctor_name:'Test', status:'draft_created'};
  requests[0].resolve({total:60, items:Array.from({length:25},(_,i)=>({...item,id:i+1}))});
  await new Promise(setImmediate);
  const next = nodes.find(n=>n.textContent==='Далее'); assert.equal(next.disabled,false);
  next.onclick(); assert.match(requests[1].path,/offset=25/);
  const search = nodes.find(n=>n.type==='search'); search.value='New'; search.oninput();
  timers.at(-1)(); assert.match(requests[2].path,/offset=0/); assert.match(requests[2].path,/q=New/);
  requests[2].resolve({total:1,items:[{...item,patient_name:'New'}]}); await new Promise(setImmediate);
  const renderedNodes=nodes.length;
  requests[1].resolve({total:60,items:[item]}); await new Promise(setImmediate);
  assert.equal(nodes.length,renderedNodes); assert.equal(next.disabled,true);
  assert.ok(nodes.some(n=>n.textContent==='1–1 / 1'));
  context.cleanup();
});

test('cancelled navigation keeps the document and its cleanup handlers intact', () => {
  let cleanupCount=0, target;
  const context=vm.createContext({
    state:{token:'test'},hasUnsavedChanges:()=>true,
    window:{confirm:()=>false},tr:x=>x,location:{hash:'#/'},displayedHash:'#/c/3',
    history:{replaceState:(_a,_b,value)=>{target=value;}},cleanup:()=>{cleanupCount++;},
  });
  const code=source.slice(source.indexOf('function route() {'),source.indexOf("window.addEventListener('hashchange'"));
  vm.runInContext(code,context);context.route();
  assert.equal(target,'#/c/3');assert.equal(cleanupCount,0);assert.equal(context.hasUnsavedChanges(),true);
});
