const { Plugin, Modal, Notice, MarkdownView, parseYaml, editorInfoField, editorLivePreviewField } = require('obsidian');
const { StateField, StateEffect, EditorState, Prec } = require('@codemirror/state');
const { EditorView, Decoration, WidgetType } = require('@codemirror/view');
const path = require('node:path');
const fs = require('node:fs');
const { createHash } = require('node:crypto');

class FormModal extends Modal {
  constructor(app, title, fields, action) {
    super(app);
    this.heading = title;
    this.fields = fields;
    this.action = action;
    this.cancelled = false;
    this.busy = false;
  }

  onOpen() {
    this.titleEl.textContent = this.heading;
    this.contentEl.innerHTML = '<form class="secemp-blog-form"><div class="secemp-blog-fields"></div><p class="secemp-blog-error" role="alert"></p><div class="secemp-blog-buttons"><button type="button">Cancel</button><button class="mod-cta" type="submit">Save</button></div></form>';
    const form = this.contentEl.querySelector('form');
    const fields = this.contentEl.querySelector('.secemp-blog-fields');
    this.fields(fields);
    form.querySelector('button[type=button]').addEventListener('click', () => this.close());
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (this.busy) return;
      this.busy = true;
      const submit = form.querySelector('button[type=submit]');
      submit.disabled = true;
      try {
        await this.action(form, () => this.cancelled);
        this.close();
      } catch (error) {
        if (!this.cancelled) form.querySelector('[role=alert]').textContent = error.message;
      } finally {
        this.busy = false;
        submit.disabled = false;
      }
    });
    form.querySelector('input, select')?.focus();
  }

  onClose() {
    this.cancelled = true;
    this.contentEl.replaceChildren();
  }
}

module.exports = class BlogPlugin extends Plugin {
  onload() {
    this.unloaded = false;
    const adapter = this.app.vault.adapter;
    if (typeof adapter.getBasePath !== 'function') {
      throw new Error('Blog commands require the repository opened as a desktop vault.');
    }
    this.root = adapter.getBasePath();
    this.bridge = require(path.join(this.root, 'scripts/create-blog-post.js'));
    this.document = document;
    this.blogFonts = [];
    this.fontsReady = this.loadFonts();
    this.document.body.classList.add('secemp-blog-vault', 'secemp-blog-focus');
    const { createArticleView } = require(path.join(this.root, '.obsidian/plugins/secemp-blog/article-view.js'));
    this.articleView = createArticleView({ StateField, StateEffect, EditorState, Prec, EditorView,
      Decoration, WidgetType, parseYaml, editorInfoField, editorLivePreviewField });
    this.registerEditorExtension(this.articleView.extension);
    this.registerMarkdownPostProcessor(async (element, context) => {
      if (!/^content\/(?!images\/|extra\/).+\.md$/i.test(context.sourcePath)) return;
      const file = this.app.vault.getAbstractFileByPath(context.sourcePath);
      if (!file) return;
      const text = await this.app.vault.cachedRead(file);
      if (!this.unloaded) this.articleView.renderReading(element, text, context.getSectionInfo(element));
    });
    this.addCommand({ id: 'new-post', name: 'New post', callback: () => this.newPost() });
    this.addCommand({ id: 'preview-note', name: 'Preview current note', callback: () => this.run(() => this.preview()) });
    this.addCommand({ id: 'set-visibility', name: 'Set current note visibility', callback: () => this.run(() => this.visibility()) });
    this.addCommand({ id: 'convert-properties', name: 'Convert current note to properties', callback: () => this.run(async () => {
      const file = await this.activeNote();
      await this.transform(file, ['--convert', file.path]);
      new Notice('Properties converted. The body and publication status are unchanged.');
    }) });
    this.addCommand({ id: 'toggle-generated-files', name: 'Show/hide project files', callback: () => {
      this.document.body.classList.toggle('secemp-blog-focus');
    } });
    this.addRibbonIcon('file-plus', 'New blog post', () => this.newPost());
  }

  onunload() {
    this.unloaded = true;
    this.previewServer?.close();
    // Every registered bundled face belongs to this plugin and is removed on unload.
    for (const font of this.blogFonts || []) this.document.fonts.delete(font);
    this.document?.body.classList.remove('secemp-blog-vault', 'secemp-blog-focus');
  }

  async loadFonts() {
    const faces = [
      ['Newsreader', 'Newsreader-Regular.ttf', 'normal', '200 800'],
      ['Newsreader', 'Newsreader-Italic.ttf', 'italic', '200 800'],
      ['IBM Plex Mono', 'IBMPlexMono-Regular.ttf', 'normal', '400'],
      ['IBM Plex Mono', 'IBMPlexMono-Medium.ttf', 'normal', '500'],
    ];
    try {
      const loaded = await Promise.all(faces.map(async ([family, file, style, weight]) => {
        const bytes = await fs.promises.readFile(path.join(this.root, '.obsidian/plugins/secemp-blog/fonts', file));
        const font = new this.document.defaultView.FontFace(family, bytes, { style, weight, display: 'swap' });
        return font.load();
      }));
      if (this.unloaded) return;
      this.blogFonts = loaded;
      // All four faces load from the vault, without a network request or system font install.
      for (const font of loaded) this.document.fonts.add(font);
    } catch (error) {
      if (!this.unloaded) new Notice('Blog fonts could not load; using fallback fonts. ' + error.message, 10000);
    }
  }

  async run(action) {
    try { await action(); } catch (error) { new Notice(error.message, 10000); }
  }

  newPost() {
    const modal = new FormModal(this.app, 'New blog post', (container) => {
      container.innerHTML = '<label>Title<input name="title" type="text" required autocomplete="off"></label><p>Starts unlisted. Nothing is uploaded or published by this command.</p>';
    }, async (form, cancelled) => {
      const title = form.querySelector('[name=title]').value.trim();
      if (!title) throw new Error('Enter a title.');
      const plan = await this.bridge.runAuthoring(['--prepare-post', '--title', title], this.root);
      if (cancelled() || this.unloaded) return;
      const file = await this.app.vault.create(plan.path, plan.content);
      const leaf = this.app.workspace.getLeaf('tab');
      await leaf.openFile(file);
      const editor = leaf.view?.editor;
      if (editor) editor.setCursor(editor.lastLine(), 0);
    });
    modal.open();
    return modal;
  }

  async activeNote() {
    const file = this.app.workspace.getActiveFile();
    if (!file || !/^content\/.+\.md$/i.test(file.path) || /^content\/(images|extra)\//.test(file.path)) {
      throw new Error('Open a Markdown post or page inside content/ first.');
    }
    const view = this.app.workspace.getActiveViewOfType(MarkdownView);
    if (view?.file === file) await view.save();
    return file;
  }

  async transform(file, args, cancelled = () => false) {
    const result = await this.bridge.runAuthoring([...args, '--dry-run'], this.root);
    if (cancelled() || this.unloaded) return false;
    await this.app.vault.process(file, (current) => {
      const hash = createHash('sha256').update(current, 'utf8').digest('hex');
      if (hash !== result.original_sha256) {
        throw new Error('The note changed while processing. Retry; your edits were not overwritten.');
      }
      return result.content;
    });
    return true;
  }

  async visibility() {
    const file = await this.activeNote();
    const info = await this.bridge.runAuthoring(['--preview-url', file.path], this.root);
    const modal = new FormModal(this.app, 'Note visibility', (container) => {
      container.innerHTML = '<label>Status<select name="status"><option value="hidden">Unlisted — shareable URL after deployment</option><option value="draft">Draft — local preview only</option><option value="published">Published — listed on the site</option></select></label><p>This edits metadata only. Review, commit, and push separately to deploy. Source committed to the public repository is never private.</p>';
      container.querySelector('select').value = info.status;
    }, async (form, cancelled) => {
      const saved = await this.transform(file, ['--set-status', file.path, '--status', form.querySelector('select').value], cancelled);
      if (saved) new Notice('Visibility saved locally. Review, commit, and push when ready to deploy.');
    });
    modal.open();
    return modal;
  }

  async preview() {
    if (this.previewing) return;
    this.previewing = true;
    try {
      const file = await this.activeNote();
      const result = await this.bridge.runAuthoring(['--preview', file.path], this.root);
      if (this.unloaded) return;
      if (!this.previewServer) {
        this.previewServer = await this.bridge.startPreviewServer(result.directory, result.port);
      }
      if (this.unloaded) {
        this.previewServer.close();
        return;
      }
      window.open(result.url, '_blank', 'noopener');
    } finally {
      this.previewing = false;
    }
  }
};
module.exports.FormModal = FormModal;
