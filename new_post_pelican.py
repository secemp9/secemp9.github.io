#!/usr/bin/env python3
"""Create, import, list, or remove Pelican posts."""
import os
import re
import argparse
from datetime import datetime
from pathlib import Path

CONTENT_DIR = Path("content")

def slugify(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def parse_pelican_metadata(content: str) -> dict:
    """Parse Pelican Key: Value metadata from content."""
    lines = content.split('\n')
    meta = {}
    content_start = 0
    for i, line in enumerate(lines):
        if ':' in line and not line.startswith(' '):
            key, _, value = line.partition(':')
            meta[key.strip().lower()] = value.strip()
            content_start = i + 1
        elif line.strip() == '':
            content_start = i + 1
            break
        else:
            break
    return meta, '\n'.join(lines[content_start:])

def list_posts():
    """List all posts in content directory."""
    posts = sorted(CONTENT_DIR.glob("*.md"))
    if not posts:
        print("No posts found.")
        return
    print(f"{'Date':<12} | {'Status':<10} | {'Title'}")
    print("-" * 60)
    for post in posts:
        content = post.read_text()
        meta, _ = parse_pelican_metadata(content)
        title = meta.get('title', '(no title)')
        date = meta.get('date', '????-??-??').split()[0]
        status = meta.get('status', 'published')
        print(f"{date:<12} | {status:<10} | {title}")

def remove_post(slug_or_filename: str):
    """Remove a post by slug or filename."""
    posts = list(CONTENT_DIR.glob("*.md"))
    matches = [f for f in posts if slug_or_filename in f.name]
    if not matches:
        print(f"No post found matching '{slug_or_filename}'.")
        return
    for match in matches:
        match.unlink()
        print(f"Removed post: {match}")

def create_post(title: str, tags: list = None, category: str = None, status: str = 'hidden'):
    """Create a new post, unlisted until explicitly published."""
    slug = slugify(title)
    date = datetime.now().strftime("%Y-%m-%d")
    datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    filename = f"{date}-{slug}.md"
    filepath = CONTENT_DIR / filename

    if filepath.exists():
        print(f"A post for today with this title already exists: {filepath}")
        return

    lines = [
        f"Title: {title}",
        f"Date: {datetime_str}",
        f"Status: {status}",
    ]
    if tags:
        lines.append(f"Tags: {', '.join(tags)}")
    if category:
        lines.append(f"Category: {category}")
    lines.append(f"Slug: {slug}")
    lines.append("")
    lines.append("Write your post content here in markdown!")
    lines.append("")
    lines.append("Paste images directly in Obsidian: they are saved to content/images/ and")
    lines.append("embedded as `![](images/file.png)`, which renders both here and on the")
    lines.append("published site. For a hero image at the top of the post, add a metadata")
    lines.append("line above (no blank lines before it): `Image: images/file.png`")

    filepath.write_text('\n'.join(lines))
    print(f"New post created: {filepath}")

def import_post(src_path: str, title: str = None, status: str = None):
    """Import an existing markdown file as a Pelican post."""
    src = Path(src_path)
    if not src.exists():
        print(f"File not found: {src_path}")
        return

    content = src.read_text()

    # Try to extract title from filename if not provided
    if not title:
        match = re.match(r'(\d{4}-\d{2}-\d{2})-(.+)\.md$', src.name)
        if match:
            title = match.group(2).replace('-', ' ').title()
        else:
            title = input("Enter post title: ").strip()

    if not title:
        print("Title cannot be empty.")
        return

    slug = slugify(title)
    date = datetime.now().strftime("%Y-%m-%d")
    datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    filename = f"{date}-{slug}.md"
    filepath = CONTENT_DIR / filename

    if filepath.exists():
        print(f"A post for this date and title already exists: {filepath}")
        return

    # Check if content already has Pelican metadata
    metadata, _ = parse_pelican_metadata(content)
    if 'title' not in metadata:
        # Add Pelican metadata
        meta_lines = [
            f"Title: {title}",
            f"Date: {datetime_str}",
            f"Slug: {slug}",
            f"Status: {status or 'hidden'}",
            "",
            "",
        ]
        content = '\n'.join(meta_lines) + content
    elif status is not None or 'status' not in metadata:
        # Change only the metadata header; body text and other fields stay intact.
        separator = re.search(r'\n[ \t]*\n', content)
        header_end = separator.start() if separator else len(content)
        header, body = content[:header_end], content[header_end:]
        header, replacements = re.subn(
            r'^status\s*:[^\n]*$', f"Status: {status or 'hidden'}", header,
            count=1, flags=re.IGNORECASE | re.MULTILINE,
        )
        if not replacements:
            header = header.rstrip() + f"\nStatus: {status or 'hidden'}"
        content = header + body

    filepath.write_text(content)
    print(f"Imported post: {filepath}")

def main():
    parser = argparse.ArgumentParser(description="Create, import, list, or remove Pelican posts.")
    parser.add_argument('--from-file', help='Path to an existing markdown file to import as a post.')
    parser.add_argument('--title', help='Specify the post title.')
    parser.add_argument('--tags', help='Comma-separated tags.')
    parser.add_argument('--category', help='Post category.')
    parser.add_argument(
        '--status', choices=('hidden', 'published', 'draft'),
        help='Visibility: new posts default to hidden; imports retain an explicit status.',
    )
    parser.add_argument('--list', action='store_true', help='List all posts.')
    parser.add_argument('--remove', help='Remove a post by slug or filename.')
    args = parser.parse_args()

    # Ensure content directory exists
    CONTENT_DIR.mkdir(exist_ok=True)

    if args.list:
        list_posts()
        return

    if args.remove:
        remove_post(args.remove)
        return

    if args.from_file:
        import_post(args.from_file, args.title, args.status)
        return

    # Create new post
    title = args.title or input("Enter post title: ").strip()
    if not title:
        print("Title cannot be empty.")
        return

    tags = [t.strip() for t in args.tags.split(',')] if args.tags else None
    create_post(title, tags, args.category, args.status or 'hidden')

if __name__ == "__main__":
    main()
