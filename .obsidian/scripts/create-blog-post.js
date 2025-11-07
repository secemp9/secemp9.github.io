// Templater User Script: Create Blog Post with Auto-Date
// Usage: Run via Command Palette -> "Templater: Run templater user script" -> select "create-blog-post"
// Or use hotkey Ctrl+Shift+B (Cmd+Shift+B on Mac)

const title = await tp.system.prompt("Post title");
if (!title) {
    return; // User cancelled
}

// Generate slug from title (similar to Python slugify)
function slugify(text) {
    return text
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '') // Remove diacritics
        .replace(/[^a-z0-9]+/g, '-') // Replace non-alphanumeric with hyphens
        .replace(/^-+|-+$/g, ''); // Remove leading/trailing hyphens
}

const date = tp.date.now("YYYY-MM-DD");
const slug = slugify(title);
const filename = `${date}-${slug}`;
const filepath = `_posts/${filename}.md`;

// Check if file already exists
const existingFile = tp.file.find_tfile(filepath);
if (existingFile) {
    const overwrite = await tp.system.suggester(
        ["Cancel", "Overwrite"],
        [false, true],
        false,
        `File ${filename}.md already exists. Overwrite?`
    );
    if (!overwrite) {
        return;
    }
}

// Get the template file
const templateFile = await tp.file.find_tfile("Templates/blog-post.md");
if (!templateFile) {
    await tp.system.prompt("Error: Template 'Templates/blog-post.md' not found!");
    return;
}

// Read template content
let templateContent = await app.vault.read(templateFile);

// Process the template manually since we have all the info
// Extract date from filename (we created it with date prefix)
const dateMatch = filename.match(/^(\d{4}-\d{2}-\d{2})-(.+)$/);
const datePart = dateMatch ? dateMatch[1] : tp.date.now("YYYY-MM-DD");
const dateStr = datePart + ' ' + tp.date.now("HH:mm:ss +0000");

// Process template: replace the template code with actual values
let processedContent = templateContent
    .replace(/<%[\s\S]*?%>/g, '') // Remove all template code blocks
    .replace(/---\s*layout: post\s*title: ".*?"\s*date: .*?\s*tags: \[\]\s*---/, 
        `---\nlayout: post\ntitle: "${title}"\ndate: ${dateStr}\ntags: []\n---`);

// If template processing didn't work as expected, manually construct frontmatter
if (!processedContent.includes('layout: post')) {
    processedContent = `---
layout: post
title: "${title}"
date: ${dateStr}
tags: []
---

Write your post content here in markdown!
`;
}

// Create the file with processed content
const newFile = await tp.file.create_new(processedContent, filepath, false);

// Open the new file
await app.workspace.openLinkText(newFile.path, "", true);

