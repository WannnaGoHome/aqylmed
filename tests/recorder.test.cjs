const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('app/static/app.js', 'utf8');
const recorderCode = source.slice(source.indexOf('function newPage() {'), source.indexOf('/* ============ страница приёма'));

test('pause/resume keeps all chunks, excludes paused time and releases microphone', async () => {
  const nodes = [];
  const timers = [];
  let instance, stopped = false, now = 1000;
  class Node {
    constructor(tag, props, kids) {
      this.tag = tag; this.props = props || {}; this.children = kids.flat(Infinity);
      this.textContent = this.children.filter(x => typeof x === 'string').join('');
      this.dataset = {}; this.hidden = !!this.props.hidden;
      this.disabled = !!this.props.disabled; this.value = this.props.value || '';
      this.classList = { add() {}, remove() {} };
      Object.assign(this, this.props); nodes.push(this);
    }
    replaceChildren(...kids) { this.children = kids.flat(Infinity); }
  }
  class Recorder {
    constructor(stream) { instance = this; this.state = 'inactive'; this.mimeType = 'audio/webm'; }
    start() { this.state = 'recording'; }
    pause() { assert.equal(this.state, 'recording'); this.state = 'paused'; }
    resume() { assert.equal(this.state, 'paused'); this.state = 'recording'; }
    stop() { this.state = 'inactive'; this.ondataavailable({ data: new Blob(['after']) }); this.onstop?.(); }
  }
  const context = vm.createContext({
    h: (tag, props, ...kids) => new Node(tag, props, kids),
    documentTypePicker: () => new Node('select', { value: 'initial' }, []),
    navigator: { mediaDevices: { getUserMedia: async () => ({ getTracks: () => [{ stop() { stopped = true; } }] }) } },
    MediaRecorder: Recorder, window: { MediaRecorder: Recorder },
    File, Blob, URL: { createObjectURL: (file) => { context.savedFile = file; return 'blob:test'; }, revokeObjectURL() {} },
    Date: class extends Date { static now() { return now; } },
    setInterval: (fn) => { timers.push(fn); return 1; }, clearInterval() {},
    tr: x => x, mount() {}, shell: (...args) => args,
    cleanup: null, location: {},
  });
  vm.runInContext(recorderCode + '\nnewPage();', context);
  const start = nodes.find(n => n.textContent === 'Начать запись');
  const pause = nodes.find(n => n.textContent === 'Пауза');
  const submit = nodes.find(n => n.textContent === 'Создать черновик заключения');
  await start.onclick();
  assert.equal(submit.disabled, true);
  instance.ondataavailable({ data: new Blob(['before']) });
  now += 2000; pause.onclick();
  assert.equal(instance.state, 'paused'); assert.equal(pause.textContent, 'Продолжить');
  now += 10000; timers[0]();
  assert.ok(nodes.some(n => n.textContent === 'Запись приостановлена 0:02'));
  pause.onclick(); now += 1000; timers[0]();
  assert.ok(nodes.some(n => n.textContent === 'Идёт запись 0:03'));
  await start.onclick();
  assert.equal(await context.savedFile.text(), 'beforeafter');
  assert.equal(stopped, true); assert.equal(submit.disabled, false);
});
