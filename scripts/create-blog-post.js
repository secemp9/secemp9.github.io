// Templater User Script: Create Blog Post with Auto-Date (Pelican)
// This version works WITHOUT requiring an active editor
// Usage: Run via Command Palette -> "Templater: Run templater user script" -> select "create-blog-post"

module.exports = async function(tp) {
  try {
    // Access app - try multiple methods
    let app;
    if (tp && tp.app) {
      app = tp.app;
    } else if (typeof window !== 'undefined' && window.app) {
      app = window.app;
    } else if (this && this.app) {
      app = this.app;
    }

    if (!app) {
      new Notice("Error: Could not access Obsidian app. Please open any file first.");
      return;
    }

    const vault = app.vault;
    const workspace = app.workspace;
    const postsFolder = "content";

    const titleInput = await tp.system.prompt("Post title");
    const title = titleInput ? titleInput.trim() : "";
    if (!title) {
      new Notice("Post creation cancelled: title required.");
      return;
    }

    function slugify(text) {
      return text
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
    }

    const datePrefix = tp.date.now("YYYY-MM-DD");
    const timeStr = tp.date.now("HH:mm");
    const rawSlug = slugify(title);
    const baseSlug = rawSlug || "post";
    let filename = `${datePrefix}-${baseSlug}`;
    let filepath = `${postsFolder}/${filename}.md`;

    // Ensure posts folder exists
    const folderExists = await vault.adapter.exists(postsFolder);
    if (!folderExists) {
      await vault.createFolder(postsFolder);
    }

    // Handle existing file conflicts
    let suffix = 2;
    while (await vault.adapter.exists(filepath)) {
      const choice = await tp.system.suggester(
        ["Cancel", `Use ${filename}-${suffix}.md`],
        [null, `${suffix}`],
        false,
        `A post named ${filename}.md already exists.`
      );
      if (!choice) {
        new Notice("Post creation cancelled: file already exists.");
        return;
      }
      filename = `${datePrefix}-${baseSlug}-${choice}`;
      filepath = `${postsFolder}/${filename}.md`;
      suffix += 1;
    }

    // Pelican metadata format (Key: Value, no YAML delimiters)
    const content = `Title: ${title}
Date: ${datePrefix} ${timeStr}
Tags:
Slug: ${baseSlug}

Write your post content here in markdown!
`;

    const file = await vault.create(filepath, content);

    // Open file in a new leaf (works without active editor)
    const leaf = workspace.getLeaf(true);
    await leaf.openFile(file);

    new Notice(`Created ${filename}.md in ${postsFolder}/`);
  } catch (error) {
    new Notice(`Error creating post: ${error.message}`);
    console.error("Blog post creation error:", error);
  }
};
