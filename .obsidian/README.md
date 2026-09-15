# Obsidian Vault Configuration for Pelican Blog

This Obsidian vault is configured to work with your Pelican blog structure.

## Setup Instructions

### 1. Install Templater Plugin
1. Open Obsidian Settings (gear icon)
2. Go to **Community plugins**
3. Click **Browse** and search for "Templater"
4. Click **Install**, then **Enable**
5. **IMPORTANT**: Go to Settings → Templater → User Script Functions
   - Set "User Scripts Folder" to: `scripts`
   - Reload Obsidian (Ctrl+R or Cmd+R)

### 2. Creating New Blog Posts

**✅ AUTOMATIC METHOD - Use Template (Recommended):**

1. Create a new file in `content` folder:
   - Press `Ctrl+N` (or `Cmd+N` on Mac) to create a new note
   - Or click "New Note" button
   - Make sure you're in the `content` folder (or it will be created there automatically)
2. The file will start as "Untitled" - that's fine!
3. Apply the template:
   - Press `Ctrl+Shift+N` (or `Cmd+Shift+N` on Mac)
   - Or Command Palette → "Templater: Create new note from template"
   - Select `blog-post` template
4. Enter your post title when prompted
5. **The template automatically:**
   - Renames the file to `YYYY-MM-DD-slug.md` (with today's date)
   - Fills in proper Pelican metadata with title and date
   - Adds `Status: hidden`, so the deployed post is unlisted until you publish it
   - Opens file ready for editing

**Example:**
- You create "Untitled" file
- Apply template, enter: "My Awesome Post"
- File automatically renamed to: `2025-11-07-my-awesome-post.md` ✅

**Alternative: Pre-name the file with date**

1. Create a new file in `content` folder
2. Name it: `YYYY-MM-DD-your-title.md` (e.g., `2025-11-07-my-post.md`)
3. Apply the template (Ctrl+Shift+N → select blog-post)
4. The template will extract the date from filename and prompt for title

## Quick Reference

| Method | Steps | Date Auto-Added? |
|--------|-------|------------------|
| Template (Recommended) | Create file → Apply template → Enter title | ✅ Yes |
| Pre-named file | Name file with date → Apply template | ✅ Yes (extracted from filename) |

## Configuration Details

- **New files default location**: `content/` folder
- **Template location**: `Templates/blog-post.md`
- **Script location**: `scripts/create-blog-post.js` (at vault root)
- **Attachment folder**: `content/images/`
- **Date format**: `YYYY-MM-DD` (matches Pelican convention)

## Pelican Metadata Format

Pelican uses Key: Value format (NOT YAML):

```
Title: My Post Title
Date: 2025-01-26 14:30
Status: hidden
Tags: python, web
Slug: my-post-title

Your content here...
```

## Preview and Publish

Both the template and `scripts/create-blog-post.js` create posts with
`Status: hidden`. They are generated at their regular URL when you push to
`main`, but do not appear in the blog listings, feeds, or page navigation, and
include `noindex` for search engines.

1. Preview locally with `./serve.sh`, or `./serve.sh --production --port 4002`
   to check production settings on localhost.
2. Commit and push the hidden post to `main`; after deployment, share its URL.
3. When ready, change `Status: hidden` to `Status: published`, commit, and push.
   Keep the date and slug unchanged to preserve the shared URL.

Use `Status: draft` for a local draft: this site's production settings suppress
draft HTML. Unlisted posts and drafts are not confidential: a public GitHub
repository still exposes committed source, images, and history. `noindex` is a
search instruction, not a password, and removing an already indexed URL takes a
recrawl. See [the site README](../README.md#what-unlisted-means) for the limits.

## Troubleshooting

**Template not renaming file?**
1. Make sure you're applying the template to a file (not creating from template)
2. The file should be in `content/` folder
3. If filename is already correct (has date prefix), it won't rename

**Date not in filename?**
- Make sure you're applying the template AFTER creating the file
- The template will automatically rename "Untitled" files
- If you pre-name the file with a date, it will use that date

**Template not appearing?**
1. Check Settings → Templater → Template folder location
2. Verify it's set to: `Templates`
3. Reload Obsidian (Ctrl+R)
