#!/usr/bin/env python3
"""Shared authoring commands for the CLI and the repository's Obsidian plugin."""

import argparse
from contextlib import redirect_stdout
from datetime import datetime
import hashlib
from io import StringIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import unicodedata
from uuid import uuid4

from pelican import Pelican, signals
from pelican.contents import Article, Page
from pelican.readers import _filter_discardable_metadata, ensure_metadata_list
from pelican.settings import read_settings
from pelican.utils import get_date
import yaml

from plugins.obsidian_metadata import (
    ObsidianMarkdownReader, serialize_document, split_document,
)

ROOT = Path(__file__).resolve().parent
CONTENT_DIR = ROOT / "content"
PREVIEW_OUTPUT = ROOT / ".preview" / "obsidian"
STATUSES = ("hidden", "published", "draft")


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "post"


def parse_pelican_metadata(text):
    """Compatibility entry point; understands both legacy headers and YAML."""
    metadata, body, _ = split_document(text)
    return metadata, body


def _title(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("A post title is required")
    if re.search(r"[\x00-\x1f\x7f]", text):
        raise ValueError("A title must be one line without control characters")
    return text.strip()


def _read_note(path):
    with Path(path).open(encoding="utf-8", newline="") as source:
        return source.read()


def _note_path(value):
    path = Path(value)
    if not path.is_absolute():
        path = CONTENT_DIR.parent / path
    path = path.resolve()
    if not path.is_relative_to(CONTENT_DIR.resolve()) or path.suffix.lower() != ".md":
        raise ValueError("Choose a Markdown note inside content/")
    if not path.is_file():
        raise ValueError(f"Note does not exist: {value}")
    return path


def _note_records():
    # Each real Markdown note contributes its existing filename and declared metadata.
    for path in sorted(CONTENT_DIR.rglob("*.md")):
        relative = path.relative_to(CONTENT_DIR)
        if relative.parts[0] in {"images", "extra"}:
            continue
        metadata, _, format_name = split_document(_read_note(path))
        if format_name == "yaml":
            metadata.setdefault("status", "hidden")
        yield path, metadata


def _allocate_slug(base, day):
    occupied = set()
    # Existing date/slug pairs predict exactly which publication URLs are already owned.
    for path, metadata in _note_records():
        if path.relative_to(CONTENT_DIR).parts[0] == "pages":
            continue
        filename = re.fullmatch(re.escape(day) + r"-(.+)\.md", path.name)
        if filename:
            occupied.add(filename[1])
        if metadata.get("date") and metadata.get("title"):
            if get_date(str(metadata["date"])).strftime("%Y-%m-%d") == day:
                occupied.add(str(metadata.get("slug") or slugify(metadata["title"])))
    if base not in occupied:
        return base
    pattern = re.compile(re.escape(base) + r"-(\d+)$")
    suffixes = [int(match[1]) for item in occupied if (match := pattern.fullmatch(item))]
    # max + 1 is strictly greater than every occupied suffix; no candidate scan or overwrite.
    return f"{base}-{max([1, *suffixes]) + 1}"


def prepare_post(title, tags=None, category=None, status="hidden", metadata=None, body=""):
    title = _title(title)
    if status not in STATUSES:
        raise ValueError("status must be hidden, published, or draft")
    metadata = dict(metadata or {})
    if metadata.get("save_as") or metadata.get("url"):
        raise ValueError("Import posts with custom URL/save_as manually to avoid output collisions")
    metadata["title"] = title
    metadata.setdefault("date", datetime.now().astimezone().isoformat(timespec="minutes"))
    metadata["status"] = status
    day = get_date(str(metadata["date"])).strftime("%Y-%m-%d")
    base = str(metadata.get("slug") or slugify(title))
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", base):
        raise ValueError("New post slugs must use lowercase letters, numbers and single hyphens")
    slug = _allocate_slug(base, day)
    metadata["slug"] = slug
    metadata["tags"] = tags if tags is not None else ensure_metadata_list(metadata.get("tags", ""))
    metadata.setdefault("cssclasses", ["blog-post"])
    if category:
        metadata["category"] = category
    path = CONTENT_DIR / f"{day}-{slug}.md"
    return {
        "path": path.relative_to(CONTENT_DIR.parent).as_posix(),
        "title": title, "slug": slug, "status": status,
        "content": serialize_document(metadata, body if body else "\n"),
    }


def _create(plan):
    path = CONTENT_DIR.parent / plan["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects against another writer racing the allocation.
    with path.open("x", encoding="utf-8") as target:
        target.write(plan["content"])
    return {key: value for key, value in plan.items() if key != "content"}


def create_post(title, tags=None, category=None, status="hidden"):
    return _create(prepare_post(title, tags, category, status))


def import_post(src_path, title=None, status=None):
    source = Path(src_path)
    metadata, body, _ = split_document(_read_note(source))
    match = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)", source.stem)
    title = title or metadata.get("title") or (match[2].replace("-", " ") if match else source.stem)
    if match:
        metadata.setdefault("date", match[1])
    return _create(prepare_post(title, status=status or metadata.get("status", "hidden"),
                                metadata=metadata, body=body))


def transform_note(value, status=None, properties=False):
    path = _note_path(value)
    original = _read_note(path)
    metadata, body, format_name = split_document(original)
    if not metadata.get("title"):
        raise ValueError("This note has no title metadata; create a blog post or add its properties first")
    if status is not None and status not in STATUSES:
        raise ValueError("status must be hidden, published, or draft")
    if properties or format_name == "yaml":
        # Legacy headers defaulted to public; native YAML notes default to unlisted.
        default_status = "hidden" if format_name == "yaml" else "published"
        metadata["status"] = status or metadata.get("status", default_status)
        if "tags" in metadata:
            metadata["tags"] = ensure_metadata_list(metadata["tags"])
        if "authors" in metadata:
            metadata["authors"] = ensure_metadata_list(metadata["authors"])
        metadata.setdefault("cssclasses", ["blog-post"])
        transformed = serialize_document(metadata, body)
    elif status is not None:
        header = original[:len(original) - len(body)] if body else original
        header, count = re.subn(r"^status[ \t]*:[^\n]*", f"Status: {status}", header,
                               flags=re.I | re.M, count=1)
        if not count:
            header = header.rstrip() + f"\nStatus: {status}\n\n"
        transformed = header + body
    else:
        transformed = original
    return {
        "path": path.relative_to(CONTENT_DIR.parent).as_posix(),
        "content": transformed,
        "original_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
        "status": status or metadata.get("status", "published"),
    }


def _write_transform(result):
    path = _note_path(result["path"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != result["original_sha256"]:
        raise ValueError("The note changed while processing; retry without overwriting your edits")
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=f".{path.name}.", delete=False) as temporary:
        temporary.write(result["content"])
        name = Path(temporary.name)
    os.chmod(name, path.stat().st_mode & 0o777)
    os.replace(name, path)
    return {key: value for key, value in result.items() if key not in {"content", "original_sha256"}}


def list_posts():
    return [
        {"path": path.relative_to(CONTENT_DIR.parent).as_posix(),
         "title": metadata.get("title", "(no title)"),
         "date": str(metadata.get("date", "")),
         "status": metadata.get("status", "published")}
        for path, metadata in _note_records()
    ]


def remove_post(value):
    """Move one exact match to recoverable vault trash; never substring-delete posts."""
    if "/" in value or "\\" in value:
        path = _note_path(value)
    else:
        matches = [path for path, metadata in _note_records()
                   if value in {path.name, path.stem, metadata.get("slug")}]
        if len(matches) != 1:
            raise ValueError("Removal needs one exact filename or unique slug, not a substring")
        path = matches[0]
    destination = CONTENT_DIR.parent / ".trash" / f"{uuid4().hex}-{path.name}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(path, destination)
    return {"path": path.relative_to(CONTENT_DIR.parent).as_posix(),
            "trash": destination.relative_to(CONTENT_DIR.parent).as_posix()}


def preview_info(value, port=4010, build=False):
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    path = _note_path(value)
    site = f"http://localhost:{port}"
    settings = read_settings(str(ROOT / "pelicanconf.py"), override={
        "PATH": str(CONTENT_DIR), "SITEURL": site, "RELATIVE_URLS": False,
        "OUTPUT_PATH": str(PREVIEW_OUTPUT), "CACHE_PATH": str(ROOT / "cache/obsidian"),
        "CACHE_CONTENT": False, "LOAD_CONTENT_CACHE": False,
        "DELETE_OUTPUT_DIRECTORY": True,
    })
    html, metadata = ObsidianMarkdownReader(settings).read(path)
    metadata = _filter_discardable_metadata(metadata)
    kind = Page if path.relative_to(CONTENT_DIR).parts[0] == "pages" else Article
    with signals.content_object_init.muted():
        note = kind(html, metadata=metadata, settings=settings, source_path=str(path))
    output = PurePosixPath(note.save_as)
    if not note.save_as or output.is_absolute() or ".." in output.parts:
        raise ValueError("This note has no safe local preview output path")
    if build:
        with redirect_stdout(StringIO()):
            Pelican(settings).run()
        if not (PREVIEW_OUTPUT / str(output)).is_file():
            raise ValueError("The preview build did not generate this note; check its metadata")
    route = str(output).removesuffix("index.html")
    from urllib.parse import quote
    return {"path": path.relative_to(CONTENT_DIR.parent).as_posix(),
            "url": f"{site}/{quote(route, safe='/')}",
            "directory": str(PREVIEW_OUTPUT), "port": port, "status": note.status}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--prepare-post", action="store_true", help="Return a new note without writing it")
    actions.add_argument("--from-file", help="Import Markdown as a post")
    actions.add_argument("--list", action="store_true")
    actions.add_argument("--remove", help="Move one exact note to .trash/")
    actions.add_argument("--convert", metavar="NOTE", help="Convert its header to Obsidian properties")
    actions.add_argument("--set-status", metavar="NOTE", help="Change only this note's visibility")
    actions.add_argument("--preview-url", metavar="NOTE", help="Return its actual local output URL")
    actions.add_argument("--preview", metavar="NOTE", help="Build a fresh local preview and return its URL")
    parser.add_argument("--title")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--category")
    parser.add_argument("--status", choices=STATUSES)
    parser.add_argument("--port", type=int, default=4010)
    parser.add_argument("--dry-run", action="store_true", help="Return a metadata edit without applying it")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.set_status and args.status is None:
        parser.error("--set-status requires --status")
    os.chdir(ROOT)
    try:
        if args.list:
            result = list_posts()
        elif args.remove:
            result = remove_post(args.remove)
        elif args.convert or args.set_status:
            result = transform_note(args.convert or args.set_status, args.status, bool(args.convert))
            if not args.dry_run:
                result = _write_transform(result)
        elif args.preview_url or args.preview:
            result = preview_info(args.preview_url or args.preview, args.port, bool(args.preview))
        elif args.from_file:
            result = import_post(args.from_file, args.title, args.status)
        else:
            title = args.title if args.title is not None else input("Post title: ")
            tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()] if args.tags else None
            creator = prepare_post if args.prepare_post else create_post
            result = creator(title, tags, args.category, args.status or "hidden")
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        elif isinstance(result, list):
            # Every listed note prints once, with its stored visibility.
            for record in result:
                print(f"{record['status']:<10} {record['path']}  {record['title']}")
        else:
            print(result.get("url") or result.get("trash") or result["path"])
        return 0
    except (OSError, ValueError, yaml.YAMLError) as error:
        if args.json:
            print(json.dumps({"error": str(error)}, ensure_ascii=False))
        else:
            print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
