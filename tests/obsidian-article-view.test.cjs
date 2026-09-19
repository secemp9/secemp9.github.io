const assert = require('node:assert/strict');
const test = require('node:test');
const { JSDOM } = require('jsdom');
const stateAPI = require('@codemirror/state');
const viewAPI = require('@codemirror/view');
const parseYaml = require('js-yaml').load;
const { createArticleView, readHeader, headerElement } = require('../.obsidian/plugins/secemp-blog/article-view.js');

const legacy = 'Title: A real title\nDate: 2026-06-14 12:00:00\nSlug: keep-this-url\n\nBody stays intact.\n';
const yaml = '---\ntitle: A real title\ndate: 2026-06-14\nslug: keep-this-url\n---\n\nBody stays intact.\n';
function setup(doc = legacy, live = true, path = 'content/post.md') {
  const editorInfoField = stateAPI.StateField.define({ create: () => ({ file: { path } }), update: v => v });
  const editorLivePreviewField = stateAPI.StateField.define({ create: () => live, update: v => v });
  const presentation = createArticleView({ ...stateAPI, ...viewAPI, parseYaml, editorInfoField, editorLivePreviewField });
  const state = stateAPI.EditorState.create({ doc, extensions: [editorInfoField, editorLivePreviewField, presentation.extension] });
  return { state, ...presentation };
}

test('legacy and YAML headers render the metadata title without changing any source', () => {
  // Both supported formats retain their exact source, body and URL-bearing properties.
  for (const source of [legacy, yaml]) {
    const { state, field } = setup(source);
    const value = state.field(field);
    assert.equal(value.header.title, 'A real title');
    assert.equal(value.header.date, '2026-06-14');
    assert.equal(value.decorations.size, 1);
    assert.equal(state.doc.toString(), source);
    assert.ok(source.slice(value.header.end).includes('Body stays intact.'));
  }
});

test('details can be edited explicitly and collapse when returning to prose', () => {
  const { state, field, editDetails } = setup();
  const opened = state.update({ effects: editDetails.of(true), selection: { anchor: 0 } }).state;
  assert.equal(opened.field(field).editing, true);
  const edited = opened.update({ changes: { from: 7, to: 19, insert: 'Updated title' } }).state;
  assert.equal(edited.field(field).header.title, 'Updated title');
  const closed = edited.update({ selection: { anchor: edited.doc.length } }).state;
  assert.equal(closed.field(field).editing, false);
  assert.ok(closed.doc.toString().includes('Slug: keep-this-url'));
});

test('typing in prose works but Backspace cannot erase collapsed metadata', () => {
  const { state, field } = setup();
  const end = state.field(field).header.end;
  const guarded = state.update({ changes: { from: end - 1, to: end, insert: '' },
    annotations: stateAPI.Transaction.userEvent.of('delete.backward') }).state;
  assert.equal(guarded.doc.toString(), legacy);
  const typed = state.update({ changes: { from: end, insert: 'New prose. ' } }).state;
  assert.equal(typed.doc.toString(), legacy.slice(0, end) + 'New prose. ' + legacy.slice(end));
});

test('external metadata updates and undo are never blocked by the display-only header', () => {
  const { state, field } = setup();
  const updated = state.update({ changes: { from: 7, to: 19, insert: 'Updated externally' } }).state;
  assert.equal(updated.field(field).header.title, 'Updated externally');
  const undone = updated.update({ changes: { from: 0, to: updated.doc.length, insert: legacy },
    annotations: stateAPI.Transaction.userEvent.of('undo') }).state;
  assert.equal(undone.doc.toString(), legacy);
});

test('temporarily empty title while editing details does not collapse the editor', () => {
  const { state, field, editDetails } = setup();
  const opened = state.update({ effects: editDetails.of(true) }).state;
  const empty = opened.update({ changes: { from: 7, to: 19, insert: '' } }).state;
  assert.equal(empty.field(field).editing, true);
  const typed = empty.update({ changes: { from: 7, insert: 'New title' },
    annotations: stateAPI.Transaction.userEvent.of('input.type') }).state;
  assert.equal(typed.field(field).header.title, 'New title');
  assert.equal(typed.field(field).editing, true);
});

test('source mode and non-blog notes are never replaced or protected', () => {
  // Only Live Preview inside the blog content folder opts into presentation.
  for (const [live, path] of [[false, 'content/post.md'], [true, 'README.md'], [true, 'content/images/note.md']]) {
    const { state, field } = setup(legacy, live, path);
    assert.equal(state.field(field).decorations.size, 0);
    assert.ok(state.update({ changes: { from: 0, insert: 'x' } }).state.doc.toString().startsWith('x'));
  }
});

test('plain or malformed headers remain visible instead of being swallowed', () => {
  assert.equal(readHeader('Just prose\n\nTitle: not metadata', parseYaml), null);
  assert.equal(readHeader('---\ntitle: [broken\n---\nBody', parseYaml), null);
  assert.equal(readHeader('Date: 2026-06-14\n\nBody', parseYaml), null);
});

test('reading mode replaces only legacy metadata, preserving the body DOM', () => {
  const { renderReading } = setup();
  const dom = new JSDOM('<section><p>Title: A real title\nDate: 2026-06-14</p><p id="body">Body stays intact.</p></section>');
  const section = dom.window.document.querySelector('section');
  const body = section.querySelector('#body');
  renderReading(section, legacy, { lineStart: 0, lineEnd: 5 });
  assert.equal(section.querySelector('h1').textContent, 'A real title');
  assert.equal(section.querySelector('#body'), body);
  renderReading(section, legacy, { lineStart: 0, lineEnd: 5 });
  assert.equal(section.querySelectorAll('h1').length, 1);
  dom.window.close();
});

test('article title is text, never injected HTML', () => {
  const dom = new JSDOM();
  const header = headerElement(dom.window.document, { title: '<img src=x onerror=alert(1)>', date: '', status: 'hidden' });
  assert.equal(header.querySelector('img'), null);
  assert.equal(header.querySelector('h1').textContent, '<img src=x onerror=alert(1)>');
  dom.window.close();
});

test('YAML reading mode inserts a title after frontmatter and blank lines only once', () => {
  const { renderReading } = setup(yaml);
  const dom = new JSDOM('<section><p id="body">Body stays intact.</p></section>');
  const section = dom.window.document.querySelector('section');
  const body = section.querySelector('#body');
  assert.equal(readHeader(yaml, parseYaml).bodyLine, 6);
  renderReading(section, yaml, { lineStart: 6, lineEnd: 6 });
  assert.equal(section.querySelector('h1').textContent, 'A real title');
  assert.equal(section.querySelector('#body'), body);
  renderReading(section, yaml, { lineStart: 6, lineEnd: 6 });
  assert.equal(section.querySelectorAll('h1').length, 1);
  dom.window.close();
});

test('real CodeMirror view mounts the header and its detail controls without source mutations', t => {
  const dom = new JSDOM('<div id="editor"></div>', { pretendToBeVisual: true });
  const names = ['window', 'document', 'MutationObserver'];
  const originals = Object.fromEntries(names.map(name => [name, global[name]]));
  // CodeMirror uses these browser globals; no layout measurements are asserted in this DOM test.
  for (const name of names) global[name] = dom.window[name];
  const { state, field } = setup();
  const view = new viewAPI.EditorView({ state, parent: dom.window.document.querySelector('#editor') });
  t.after(() => {
    view.destroy(); dom.window.close();
    // Restore only the globals installed by this test.
    for (const name of names) {
      if (originals[name] === undefined) delete global[name];
      else global[name] = originals[name];
    }
  });
  assert.equal(view.dom.querySelector('h1').textContent, 'A real title');
  view.dom.querySelector('button').click();
  assert.equal(view.state.field(field).editing, true);
  assert.match(view.dom.textContent, /Title: A real title/);
  view.dom.querySelector('button').click();
  assert.equal(view.state.field(field).editing, false);
  assert.equal(view.state.doc.toString(), legacy);
});
