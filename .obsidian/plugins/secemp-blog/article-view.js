// View-only article headers. The underlying Markdown and publication metadata never change.
function readHeader(text, parseYaml) {
  let metadata, end, format;
  const yaml = text.match(/^---\r?\n([\s\S]*?)\r?\n(?:---|\.\.\.)(?:\r?\n|$)/);
  if (yaml) {
    try { metadata = parseYaml(yaml[1]); } catch { return null; }
    end = yaml[0].length;
    format = 'yaml';
  } else {
    metadata = {};
    end = 0;
    let last;
    // Only the contiguous leading metadata block can be presented as a header.
    for (const line of text.split(/(?<=\n)/)) {
      if (!line.trim()) { end += line.length; break; }
      const match = line.match(/^([A-Za-z][A-Za-z0-9_-]*):[ \t]*(.*?)[\r\n]*$/);
      if (match) { last = match[1].toLowerCase(); metadata[last] = match[2]; }
      else if (/^[ \t]/.test(line) && last) metadata[last] += '\n' + line.trim();
      else return null;
      end += line.length;
    }
    format = 'legacy';
  }
  if (!metadata || typeof metadata !== 'object' || Array.isArray(metadata)) return null;
  metadata = Object.fromEntries(Object.entries(metadata).map(([key, value]) => [key.toLowerCase(), value]));
  if (typeof metadata.title !== 'string' || !metadata.title.trim()) return null;
  const date = metadata.date instanceof Date && !Number.isNaN(metadata.date.getTime())
    ? metadata.date.toISOString() : String(metadata.date || '');
  end += text.slice(end).match(/^(?:[ \t]*\r?\n)*/)[0].length;
  const bodyLine = text.slice(0, end).split('\n').length - 1;
  return { title: metadata.title, date: date.slice(0, 10),
           status: metadata.status || (format === 'yaml' ? 'hidden' : 'published'),
           end, format, bodyLine };
}

function headerElement(document, header, onToggle, editing = false) {
  const element = document.createElement('header');
  element.className = 'secemp-article-header';
  element.dataset.editing = String(editing);
  const meta = document.createElement('div');
  meta.className = 'secemp-article-meta';
  const date = document.createElement('span');
  date.textContent = [header.date, header.status === 'published' ? '' : header.status].filter(Boolean).join(' · ');
  meta.append(date);
  if (onToggle) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = editing ? 'Back to writing' : 'Edit details';
    button.addEventListener('click', onToggle);
    meta.append(button);
  }
  const title = document.createElement('h1');
  title.textContent = header.title;
  element.append(meta, title);
  return element;
}

function createArticleView(api) {
  const { StateField, StateEffect, EditorState, Prec, EditorView, Decoration, WidgetType,
          editorInfoField, editorLivePreviewField, parseYaml } = api;
  const editDetails = StateEffect.define();
  const isPost = state => /^content\/(?!images\/|extra\/).+\.md$/i.test(state.field(editorInfoField, false)?.file?.path || '');

  class ArticleHeader extends WidgetType {
    constructor(header, editing) { super(); this.header = header; this.editing = editing; }
    eq(other) { return this.editing === other.editing && JSON.stringify(this.header) === JSON.stringify(other.header); }
    toDOM(view) {
      return headerElement(view.dom.ownerDocument, this.header, () => {
        view.dispatch({ effects: editDetails.of(!this.editing),
                        selection: { anchor: this.editing ? this.header.end : 0 }, scrollIntoView: true });
        view.focus();
      }, this.editing);
    }
    ignoreEvent() { return true; }
  }

  function presentation(state, editing = false) {
    if (!isPost(state) || !state.field(editorLivePreviewField, false)) return { header: null, editing: false, decorations: Decoration.none };
    const header = readHeader(state.doc.toString(), parseYaml);
    if (!header) return { header: null, editing, decorations: Decoration.none };
    const widget = new ArticleHeader(header, editing);
    const decoration = editing
      ? Decoration.widget({ widget, block: true, side: -1 }).range(0)
      : Decoration.replace({ widget, block: true }).range(0, header.end);
    return { header, editing, decorations: Decoration.set([decoration]) };
  }

  const field = StateField.define({
    create: state => presentation(state),
    update(previous, transaction) {
      let editing = previous.editing;
      // Explicit detail actions take precedence over the cursor move they include.
      const toggle = transaction.effects.find(effect => effect.is(editDetails));
      if (toggle) editing = toggle.value;
      else if (transaction.selection && previous.header && transaction.newSelection.main.from >= previous.header.end) editing = false;
      return presentation(transaction.state, editing);
    },
    provide: value => EditorView.decorations.from(value, state => state.decorations),
  });

  const protectMetadata = EditorState.transactionFilter.of(transaction => {
    const current = transaction.startState.field(field, false);
    if (!transaction.docChanged || !current?.header || current.editing) return transaction;
    // File reloads, native property edits, undo and other programmatic updates must flow through.
    if (!transaction.isUserEvent('delete') && !transaction.isUserEvent('input')) return transaction;
    let touchesHeader = false;
    // A Backspace at the start of prose must not erase hidden publication metadata.
    transaction.changes.iterChangedRanges(from => { if (from < current.header.end) touchesHeader = true; });
    return touchesHeader ? [] : transaction;
  });

  function renderReading(element, text, section) {
    const header = readHeader(text, parseYaml);
    if (!header || !section || element.querySelector('.secemp-article-header')) return;
    if (header.format === 'legacy') {
      if (section.lineStart !== 0) return;
      const paragraph = element.firstElementChild;
      if (paragraph?.tagName !== 'P' || !/^title\s*:/i.test(paragraph.textContent)) return;
      paragraph.replaceWith(headerElement(element.ownerDocument, header));
    } else if (section.lineStart <= header.bodyLine && section.lineEnd >= header.bodyLine) {
      element.prepend(headerElement(element.ownerDocument, header));
    }
  }

  return { field, editDetails, renderReading,
           extension: Prec.highest([field, protectMetadata, EditorView.atomicRanges.of(view => {
             const value = view.state.field(field);
             return value.editing ? Decoration.none : value.decorations;
           })]) };
}

module.exports = { createArticleView, readHeader, headerElement };
