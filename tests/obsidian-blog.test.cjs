const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { createHash } = require('node:crypto');
const test = require('node:test');
const { JSDOM } = require('jsdom');
const bridge = require('../scripts/create-blog-post.js');

const ROOT = path.resolve(__dirname, '..');
const PLUGIN = path.join(ROOT, '.obsidian/plugins/secemp-blog/main.js');
const settle = () => new Promise(resolve => setImmediate(resolve));
const digest = value => createHash('sha256').update(value).digest('hex');

function boot(t) {
  const dom = new JSDOM('<!doctype html><html><body></body></html>');
  t.after(() => dom.window.close());
  const notices = [], created = [], opened = [], calls = [], urls = [];
  const document = dom.window.document;
  dom.window.open = url => urls.push(url);
  class Plugin {
    constructor(app) { this.app = app; this.commands = []; }
    addCommand(command) { this.commands.push(command); }
    addRibbonIcon(icon, label, action) { this.ribbon = { icon, label, action }; }
  }
  class Modal {
    constructor(app) {
      this.app = app;
      this.container = document.createElement('section');
      this.titleEl = document.createElement('h2');
      this.contentEl = document.createElement('div');
      this.container.append(this.titleEl, this.contentEl);
    }
    open() { document.body.append(this.container); this.onOpen(); }
    close() { this.onClose(); this.container.remove(); }
  }
  class Notice { constructor(text) { notices.push(text); } }
  class MarkdownView {}
  const file = { path: 'content/note.md' };
  let current = 'original note';
  const app = {
    vault: {
      adapter: { getBasePath: () => ROOT },
      create: async (filename, body) => {
        const result = { path: filename, body };
        created.push(result);
        return result;
      },
      process: async (target, callback) => { assert.equal(target, file); current = callback(current); },
    },
    workspace: {
      getActiveFile: () => file,
      getActiveViewOfType: () => ({ file, save: async () => calls.push('save') }),
      getLeaf: () => ({ openFile: async target => opened.push(target) }),
    },
  };
  const module = { exports: {} };
  const requireStub = name => name === 'obsidian' ? { Plugin, Modal, Notice, MarkdownView } : require(name);
  vm.runInNewContext('(function(require,module,exports){' + fs.readFileSync(PLUGIN, 'utf8') + '\n})',
                     { document, window: dom.window })(requireStub, module, module.exports);
  const plugin = new module.exports(app);
  plugin.onload();
  plugin.bridge = {
    runAuthoring: async args => {
      calls.push(Array.from(args));
      if (args[0] === '--prepare-post') return { path: 'content/new-post.md', content: 'prepared YAML' };
      if (args[0] === '--preview-url') return { status: 'hidden', url: 'http://localhost:4010/note/' };
      if (args[0] === '--preview') return { directory: '/fixture/preview', port: 4010, url: 'http://localhost:4010/note/' };
      return { original_sha256: digest(current), content: 'updated metadata' };
    },
    startPreviewServer: async () => ({ close: () => calls.push('close server') }),
  };
  t.after(() => plugin.onunload());
  return { plugin, dom, document, app, file, notices, created, opened, calls, urls,
           current: () => current, edit: value => { current = value; } };
}

function submit(ui, modal) {
  modal.contentEl.querySelector('form').dispatchEvent(new ui.dom.window.Event('submit', { bubbles: true, cancelable: true }));
}

test('every configured blog hotkey names an actual registered command', t => {
  const ui = boot(t);
  const hotkeys = JSON.parse(fs.readFileSync(path.join(ROOT, '.obsidian/hotkeys.json')));
  const commands = new Set(ui.plugin.commands.map(c => 'secemp-blog:' + c.id));
  // Every checked-in shortcut must resolve to a command provided by the enabled plugin.
  for (const id of Object.keys(hotkeys)) assert.ok(commands.has(id), id);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(ROOT, '.obsidian/community-plugins.json'))), ['secemp-blog']);
  assert.ok(ui.document.body.classList.contains('secemp-blog-focus'));
});

test('cancelling the title dialog creates no placeholder file', async t => {
  const ui = boot(t);
  const modal = ui.plugin.newPost();
  modal.contentEl.querySelector('button[type=button]').click();
  await settle();
  assert.equal(ui.created.length, 0);
  assert.equal(ui.calls.length, 0);
});

test('New Post prepares once, then creates and opens exactly that note', async t => {
  const ui = boot(t);
  const modal = ui.plugin.newPost();
  modal.contentEl.querySelector('input').value = 'A title: café';
  submit(ui, modal);
  submit(ui, modal);
  await settle();
  assert.deepEqual(ui.calls, [['--prepare-post', '--title', 'A title: café']]);
  assert.equal(ui.created.length, 1);
  assert.equal(ui.created[0].body, 'prepared YAML');
  assert.deepEqual(ui.opened, ui.created);
});

test('cancel while preparation is running still creates no file', async t => {
  const ui = boot(t);
  let resolve;
  ui.plugin.bridge.runAuthoring = () => new Promise(done => { resolve = done; });
  const modal = ui.plugin.newPost();
  modal.contentEl.querySelector('input').value = 'Never create';
  submit(ui, modal);
  modal.close();
  resolve({ path: 'content/cancelled.md', content: 'unused' });
  await settle();
  assert.equal(ui.created.length, 0);
});

test('errors keep the creation dialog usable without an empty file', async t => {
  const ui = boot(t);
  ui.plugin.bridge.runAuthoring = async () => { throw new Error('Fix invalid metadata in another note'); };
  const modal = ui.plugin.newPost();
  modal.contentEl.querySelector('input').value = 'Valid title';
  submit(ui, modal);
  await settle();
  assert.match(modal.contentEl.querySelector('[role=alert]').textContent, /Fix invalid metadata/);
  assert.equal(modal.contentEl.querySelector('button[type=submit]').disabled, false);
  assert.equal(ui.created.length, 0);
});

test('metadata writes reject edits made after the CLI read the note', async t => {
  const ui = boot(t);
  const old = digest(ui.current());
  ui.plugin.bridge.runAuthoring = async () => {
    ui.edit('Typing continued');
    return { original_sha256: old, content: 'stale transform' };
  };
  await assert.rejects(ui.plugin.transform(ui.file, ['--convert', ui.file.path]), /changed while processing/);
  assert.equal(ui.current(), 'Typing continued');
});

test('visibility preserves the current selection and edits locally without publishing', async t => {
  const ui = boot(t);
  const modal = await ui.plugin.visibility();
  const select = modal.contentEl.querySelector('select');
  assert.equal(select.value, 'hidden');
  select.value = 'draft';
  submit(ui, modal);
  await settle();
  assert.deepEqual(ui.calls.at(-1), ['--set-status', ui.file.path, '--status', 'draft', '--dry-run']);
  assert.equal(ui.current(), 'updated metadata');
  assert.match(ui.notices.at(-1), /saved locally/);
});

test('preview saves the editor, builds once, and reuses only its own server', async t => {
  const ui = boot(t);
  let starts = 0;
  ui.plugin.bridge.startPreviewServer = async () => { starts++; return { close: () => {} }; };
  await ui.plugin.preview();
  await ui.plugin.preview();
  assert.equal(starts, 1);
  assert.equal(ui.calls[0], 'save');
  assert.deepEqual(ui.urls, ['http://localhost:4010/note/', 'http://localhost:4010/note/']);
});

test('cancelling a pending visibility edit does not apply metadata changes', async t => {
  const ui = boot(t);
  const modal = await ui.plugin.visibility();
  let resolve;
  ui.plugin.bridge.runAuthoring = () => new Promise(done => { resolve = done; });
  submit(ui, modal);
  modal.close();
  resolve({ original_sha256: digest(ui.current()), content: 'cancelled edit' });
  await settle();
  assert.equal(ui.current(), 'original note');
  assert.equal(ui.notices.length, 0);
});

test('unloading during a build does not open a browser or leave a server running', async t => {
  const ui = boot(t);
  let resolve;
  ui.plugin.bridge.runAuthoring = () => new Promise(done => { resolve = done; });
  const pending = ui.plugin.preview();
  await settle();
  ui.plugin.onunload();
  resolve({ directory: '/fixture/preview', port: 4010, url: 'http://localhost:4010/note/' });
  await pending;
  assert.equal(ui.urls.length, 0);
  assert.equal(ui.plugin.previewServer, undefined);
});

test('real CLI bridge preserves shell metacharacters as title data and writes nothing', async () => {
  const title = 'Literal $(not-a-command) and "quotes"';
  const result = await bridge.runAuthoring(['--prepare-post', '--title', title]);
  assert.equal(result.title, title);
  assert.equal(fs.existsSync(path.join(ROOT, result.path)), false);
  assert.ok(result.content.startsWith('---\n'));
});

test('local preview server serves only generated files and rejects traversal and writes', async t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'secemp-preview-'));
  const output = path.join(directory, 'output');
  fs.mkdirSync(output);
  fs.writeFileSync(path.join(output, 'index.html'), '<h1>Preview fixture</h1>');
  fs.writeFileSync(path.join(directory, 'private.txt'), 'do not serve');
  fs.symlinkSync(path.join(directory, 'private.txt'), path.join(output, 'escape.txt'));
  const server = await bridge.startPreviewServer(output, 0);
  t.after(async () => {
    await new Promise(resolve => server.close(resolve));
    fs.rmSync(directory, { recursive: true, force: true });
  });
  const base = 'http://127.0.0.1:' + server.address().port;
  const response = await fetch(base + '/');
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.equal(await response.text(), '<h1>Preview fixture</h1>');
  const cases = [['/%2e%2e%2fprivate.txt', 403], ['/escape.txt', 403], ['/missing', 404]];
  // The two escape paths cannot expose the private fixture; an absent page stays 404.
  for (const [pathname, status] of cases) {
    const result = await fetch(base + pathname);
    assert.equal(result.status, status);
    assert.ok(!(await result.text()).includes('do not serve'));
  }
  const post = await fetch(base, { method: 'POST', body: 'nothing should change' });
  assert.equal(post.status, 405);
  await post.text();
});

test('writing stylesheet stays small and does not force application-wide colors', () => {
  const css = fs.readFileSync(path.join(ROOT, '.obsidian/snippets/blog-theme.css'), 'utf8');
  assert.ok(css.split('\n').length < 80);
  assert.ok(!css.includes('!important'));
  assert.ok(!css.includes('--background-primary'));
  assert.ok(!css.includes('.modal,'));
});
