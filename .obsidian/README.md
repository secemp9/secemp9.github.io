# Writing the blog in Obsidian

Open the **repository root** as a desktop Obsidian vault. The bundled **Blog**
plugin uses the same Python authoring code as the CLI. It does not commit, push,
or publish automatically.

## Setup

1. Install the Python dependencies using the setup commands in the root README.
2. Open this folder as a vault. Allow community plugins for this trusted repo
   and enable **Blog** under Settings → Community plugins.
3. Reload Obsidian after pulling these changes. Templater is no longer used.

No plugin download or npm build is needed. The commands require the repo's
`.venv` Python environment. The live website has no Obsidian dependency.

## Commands

| Command | Shortcut |
| --- | --- |
| Blog: New post | Ctrl/Cmd+Shift+N |
| Blog: Preview current note | Ctrl/Cmd+Shift+P |
| Blog: Set current note visibility | Ctrl/Cmd+Shift+B |
| Blog: Convert current note to properties | Command palette |
| Blog: Show/hide generated folders | Command palette |

**New post** asks for a title before creating anything, then opens an empty
post in `content/`. Cancelling leaves no placeholder note. Repeated titles get
distinct filenames **and slugs**. Ctrl/Cmd+N remains Obsidian's ordinary blank
note command.

Edit the title, date, tags, and status through the note's Properties panel.
The slug is assigned once: changing a title or renaming a note does not change
its public URL. Keep `date` and `slug` stable after sharing a link.

Existing Pelican-header posts still build unchanged. **Convert current note
to properties** changes only the header when you explicitly invoke it; it
preserves the body, date, slug, and publication status.

## Links and images

Paste images normally. They are stored in `content/images/`, and Obsidian
inserts ordinary relative Markdown links. Nested posts and pages are supported.

Use the normal link picker to link to another note. The vault is configured
to generate Markdown links, for example `[Another post](other-post.md)`, not
Wikilinks. The build resolves these to the destination's real blog URL.
Links to ordinary headings work too. External and site-root links are preserved.

Obsidian-only block references and note transclusions are not converted.
A real site preview is the authority for the published appearance.

## Preview

**Preview current note** saves the editor, builds a fresh Pelican preview in
`.preview/obsidian/`, and opens that note in the browser on localhost:4010.
No terminal server setup is needed. Run the command again after edits to rebuild.
The loopback-only server stops when the plugin unloads. It serves generated
files only, not the repository or your notes.

The existing `./serve.sh` workflow is also available for automatic rebuilds
while editing. See the root README for its production/sandbox modes.

Preview pages contain the configured **real payment links and crypto addresses**.
Do not submit test payments there; use `./serve.sh --sandbox` for Stripe testing.

## Visibility and publishing

| Status | After a successful deployment |
| --- | --- |
| `hidden` | Shareable at its regular URL, absent from listings, noindex |
| `draft` | Local preview only; no deployed HTML |
| `published` | Listed on the site and in feeds |

New posts and YAML notes without a status default to `hidden`.
Legacy Pelican headers without a status retain their historical public default.

Changing visibility edits the note locally. To deploy:

1. Preview the note and review `git diff -- content/`.
2. Stage the intended Markdown and attachments, then commit.
3. Push to `main` and check the GitHub Pages workflow.

Do not commit confidential notes or attachments: the GitHub repository is
public, regardless of a note's status. Unlisted is not private.

## Vault housekeeping

The vault uses the blog's warm charcoal, bone, and brass palette throughout,
with Newsreader for prose/headings and IBM Plex Mono for code. The Blog plugin
loads the bundled fonts offline; no system font installation or Google Fonts
connection is needed. Live Preview and reading mode share the typography,
heading rules, links, blockquotes, and code colors. Native controls keep their
normal layout and behavior, with the blog palette instead of white surfaces.

The writing column is **64rem (1024px)** at full size, versus the old 42rem,
and shrinks with its pane. Text starts at **20px**; change it under Settings →
Appearance → Font size. The public site's narrower reading measure is unchanged;
use Blog: Preview current note for its exact layout. Reload the vault once after
updating so the bundled fonts load. The `blog-theme` snippet must be enabled
under Appearance → CSS snippets.

Generated folders are hidden from the explorer by
default; the Show/hide command reveals them without deleting anything.

Workspace/session files are local and ignored by Git. The retired Templater
installation is retained locally but disabled and untracked. The old duplicate
template and its unused configuration have been removed; Git history retains
them. No existing article or page is automatically migrated.
