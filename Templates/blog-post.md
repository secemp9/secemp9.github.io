<%*
// Get current filename
const currentFilename = tp.file.title;
const dateMatch = currentFilename.match(/^(\d{4}-\d{2}-\d{2})-(.+)$/);
let title, dateStr, slug, finalFilename;

// Generate slug from title helper function
function slugify(text) {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

if (dateMatch) {
  // Filename already has date prefix - ask if user wants to update
  const datePart = dateMatch[1];
  const slugPart = dateMatch[2];
  const suggestedTitle = slugPart.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  // Prompt for new title
  title = await tp.system.prompt("Post title", suggestedTitle) || suggestedTitle;

  // Ask if user wants to update the date to today
  const updateDate = await tp.system.suggester(
    ["Keep existing date", "Update to today's date"],
    [false, true],
    false,
    `Current date in filename: ${datePart}. Update to today?`
  );

  if (updateDate) {
    // Update to today's date
    const datePrefix = tp.date.now("YYYY-MM-DD");
    slug = slugify(title);
    finalFilename = `${datePrefix}-${slug}`;
    dateStr = datePrefix + ' ' + tp.date.now("HH:mm");
  } else {
    // Keep existing date but update title slug
    slug = slugify(title);
    finalFilename = `${datePart}-${slug}`;
    dateStr = datePart + ' ' + tp.date.now("HH:mm");
  }

  // Rename if filename changed
  if (currentFilename !== finalFilename) {
    await tp.file.rename(finalFilename);
  }
} else {
  // Filename doesn't have date - prompt for title and generate date-prefixed filename
  title = await tp.system.prompt("Post title");
  if (!title) {
    title = "Untitled Post";
  }

  const datePrefix = tp.date.now("YYYY-MM-DD");
  slug = slugify(title);
  finalFilename = `${datePrefix}-${slug}`;
  dateStr = datePrefix + ' ' + tp.date.now("HH:mm");

  // Rename the file if it's not already the correct name
  if (currentFilename !== finalFilename) {
    await tp.file.rename(finalFilename);
  }
}
-%>
Title: <% title %>
Date: <% dateStr %>
Tags:
Slug: <% slug %>

Write your post content here in markdown!

