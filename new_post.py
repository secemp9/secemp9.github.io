import os
from datetime import datetime
import yaml
import argparse

def slugify(text):
    import unicodedata
    import re
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

POSTS_DIR = "_posts"

def parse_filename_for_title_and_date(filename):
    import re
    base = os.path.basename(filename)
    match = re.match(r'(\d{4}-\d{2}-\d{2})-(.+)\.md$', base)
    if match:
        date, slug = match.groups()
        title = slug.replace('-', ' ').title()
        return date, title
    return None, None

def ensure_front_matter(content, title, date):
    # Check if content starts with front matter
    if content.lstrip().startswith('---'):
        return content  # Already has front matter
    front_matter = {
        'layout': 'post',
        'title': title,
        'date': date,
        'tags': []
    }
    fm = '---\n' + yaml.dump(front_matter, default_flow_style=False, sort_keys=False) + '---\n\n'
    return fm + content

def list_posts():
    posts = sorted([f for f in os.listdir(POSTS_DIR) if f.endswith('.md')])
    if not posts:
        print("No posts found.")
        return
    print(f"{'Date':<12} | {'Title'}")
    print("-"*50)
    for post in posts:
        date, title = parse_filename_for_title_and_date(post)
        if not title:
            # Try to read from front matter
            with open(os.path.join(POSTS_DIR, post), 'r') as f:
                try:
                    fm = list(yaml.safe_load_all(f))[0]
                    title = fm.get('title', '(no title)')
                except Exception:
                    title = '(no title)'
        print(f"{date or '????-??-??':<12} | {title}")

def remove_post(slug_or_filename):
    # Try to match by filename or slug
    posts = [f for f in os.listdir(POSTS_DIR) if f.endswith('.md')]
    matches = [f for f in posts if slug_or_filename in f]
    if not matches:
        print(f"No post found matching '{slug_or_filename}'.")
        return
    for match in matches:
        os.remove(os.path.join(POSTS_DIR, match))
        print(f"Removed post: {match}")

def main():
    parser = argparse.ArgumentParser(description="Create, import, list, or remove Jekyll posts.")
    parser.add_argument('--from-file', help='Path to an existing markdown file to import as a post.')
    parser.add_argument('--title', help='Specify the post title (used with --from-file).')
    parser.add_argument('--list', action='store_true', help='List all posts in _posts/.')
    parser.add_argument('--remove', help='Remove a post by slug or filename.')
    args = parser.parse_args()

    if args.list:
        list_posts()
        return
    if args.remove:
        remove_post(args.remove)
        return

    if args.from_file:
        src_path = args.from_file
        if not os.path.isfile(src_path):
            print(f"File not found: {src_path}")
            exit(1)
        with open(src_path, 'r') as f:
            content = f.read()
        # Try to parse date and title from filename
        date, title = parse_filename_for_title_and_date(src_path)
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        # Use --title if provided, else fallback to filename or prompt
        if args.title:
            title = args.title
        if not title:
            title = input("Enter post title: ").strip()
        datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
        slug = slugify(title)
        filename = f"{date}-{slug}.md"
        filepath = os.path.join(POSTS_DIR, filename)
        if os.path.exists(filepath):
            print(f"A post for this date and title already exists: {filepath}")
            exit(1)
        post_content = ensure_front_matter(content, title, datetime_str)
        with open(filepath, 'w') as f:
            f.write(post_content)
        print(f"Imported post: {filepath}")
    else:
        title = args.title or input("Enter post title: ").strip()
        if not title:
            print("Title cannot be empty.")
            exit(1)
        slug = slugify(title)
        date = datetime.now().strftime("%Y-%m-%d")
        datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
        filename = f"{date}-{slug}.md"
        filepath = os.path.join(POSTS_DIR, filename)
        if os.path.exists(filepath):
            print(f"A post for today with this title already exists: {filepath}")
            exit(1)
        front_matter = {
            'layout': 'post',
            'title': title,
            'date': datetime_str,
            'tags': []
        }
        with open(filepath, "w") as f:
            f.write('---\n')
            yaml.dump(front_matter, f, default_flow_style=False, sort_keys=False)
            f.write('---\n\n')
            f.write('Write your post content here in markdown!\n')
        print(f"New post created: {filepath}")

if __name__ == "__main__":
    main() 