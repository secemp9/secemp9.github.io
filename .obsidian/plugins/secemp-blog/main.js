const { Plugin, Modal, Notice, MarkdownView } = require('obsidian');
const path = require('node:path');
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
    this.document.body.classList.add('secemp-blog-vault', 'secemp-blog-focus');
    this.addCommand({ id: 'new-post', name: 'New post', callback: () => this.newPost() });
    this.addCommand({ id: 'preview-note', name: 'Preview current note', callback: () => this.run(() => this.preview()) });
    this.addCommand({ id: 'set-visibility', name: 'Set current note visibility', callback: () => this.run(() => this.visibility()) });
    this.addCommand({ id: 'convert-properties', name: 'Convert current note to properties', callback: () => this.run(async () => {
      const file = await this.activeNote();
      await this.transform(file, ['--convert', file.path]);
      new Notice('Properties converted. The body and publication status are unchanged.');
    }) });
    this.addCommand({ id: 'toggle-generated-files', name: 'Show/hide generated folders', callback: () => {
      this.document.body.classList.toggle('secemp-blog-focus');
    } });
    this.addRibbonIcon('file-plus', 'New blog post', () => this.newPost());
  }

  onunload() {
    this.unloaded = true;
    this.previewServer?.close();
    this.document?.body.classList.remove('secemp-blog-vault', 'secemp-blog-focus');
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
      await this.app.workspace.getLeaf('tab').openFile(file);
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
