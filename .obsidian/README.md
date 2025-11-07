# Obsidian Vault Configuration for Jekyll Blog

This Obsidian vault is configured to work with your Jekyll blog structure.

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

1. Create a new file in `_posts` folder:
   - Press `Ctrl+N` (or `Cmd+N` on Mac) to create a new note
   - Or click "New Note" button
   - Make sure you're in the `_posts` folder (or it will be created there automatically)
2. The file will start as "Untitled" - that's fine!
3. Apply the template:
   - Press `Ctrl+Shift+N` (or `Cmd+Shift+N` on Mac)
   - Or Command Palette → "Templater: Create new note from template"
   - Select `blog-post` template
4. Enter your post title when prompted
5. **The template automatically:**
   - Renames the file to `YYYY-MM-DD-slug.md` (with today's date)
   - Fills in proper Jekyll frontmatter with title and date
   - Opens file ready for editing

**Example:**
- You create "Untitled" file
- Apply template, enter: "My Awesome Post"
- File automatically renamed to: `2025-11-07-my-awesome-post.md` ✅

**Alternative: Pre-name the file with date**

1. Create a new file in `_posts` folder
2. Name it: `YYYY-MM-DD-your-title.md` (e.g., `2025-11-07-my-post.md`)
3. Apply the template (Ctrl+Shift+N → select blog-post)
4. The template will extract the date from filename and prompt for title

## Quick Reference

| Method | Steps | Date Auto-Added? |
|--------|-------|------------------|
| Template (Recommended) | Create file → Apply template → Enter title | ✅ Yes |
| Pre-named file | Name file with date → Apply template | ✅ Yes (extracted from filename) |

## Configuration Details

- **New files default location**: `_posts/` folder
- **Template location**: `Templates/blog-post.md`
- **Script location**: `scripts/create-blog-post.js`
- **Attachment folder**: `assets/img/`
- **Date format**: `YYYY-MM-DD` (matches Jekyll convention)

## Troubleshooting

**Template not renaming file?**
1. Make sure you're applying the template to a file (not creating from template)
2. The file should be in `_posts/` folder
3. If filename is already correct (has date prefix), it won't rename

**Date not in filename?**
- Make sure you're applying the template AFTER creating the file
- The template will automatically rename "Untitled" files
- If you pre-name the file with a date, it will use that date

**Template not appearing?**
1. Check Settings → Templater → Template folder location
2. Verify it's set to: `Templates`
3. Reload Obsidian (Ctrl+R)
