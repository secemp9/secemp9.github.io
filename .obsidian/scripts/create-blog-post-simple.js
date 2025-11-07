// Simple Templater User Script: Create Blog Post with Auto-Date
// This version uses Templater's create_new_note_from_template command
// Usage: Run via Command Palette -> "Templater: Run templater user script" -> select "create-blog-post-simple"
// Or use hotkey (configured separately)

module.exports = async function(tp) {
    const title = await tp.system.prompt("Post title");
    if (!title) {
        return; // User cancelled
    }

    // Generate slug from title
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
    
    // Use Templater's create_new_note_from_template with templated filename
    const templateFile = await tp.file.find_tfile("Templates/blog-post.md");
    if (!templateFile) {
        await tp.system.prompt("Error: Template 'Templates/blog-post.md' not found!");
        return;
    }

    // Create file using Templater's method
    const newFile = await tp.file.create_new(
        await app.vault.read(templateFile),
        `_posts/${filename}.md`,
        false
    );

    // Process the template content with the correct title and date
    const dateStr = date + ' ' + tp.date.now("HH:mm:ss +0000");
    const processedContent = `---
layout: post
title: "${title}"
date: ${dateStr}
tags: []
---

Write your post content here in markdown!
`;

    await app.vault.modify(newFile, processedContent);
    await app.workspace.openLinkText(newFile.path, "", true);
};

