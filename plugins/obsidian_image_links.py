"""Make Obsidian-pasted image links work on the published Pelican site.

This repo doubles as an Obsidian vault. With the vault settings in
.obsidian/app.json (attachmentFolderPath: "content/images", markdown links,
relative link format), pasting an image into a post in content/ produces:

    ![](images/Pasted%20image%2020260101123456.png)

That renders in Obsidian (relative to the note), but Pelican would copy it
verbatim into article pages at /YYYY/MM/DD/slug/, where the relative path is
broken. This plugin rewrites relative <img> srcs to Pelican's {static}
syntax before intrasite link substitution runs, so Pelican resolves them
against content/images/ (and warns if the file does not exist):

    images/foo.png          -> {static}/images/foo.png
    content/images/foo.png  -> {static}/images/foo.png
    foo.png (bare filename) -> {static}/images/foo.png

Absolute (/images/...), external (http...), {static}/{attach}/{filename},
anchor, and data: URLs are left untouched.
"""
import re

from pelican import signals

_IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_SRC_ATTR = re.compile(r"(\bsrc\s*=\s*)([\"'])(.*?)\2", re.IGNORECASE)

# Leave these alone: scheme:, protocol-relative, site-absolute, Pelican
# placeholders ({static}, {attach}, {filename}, ...), anchors, queries.
_SKIP = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.\-]*:|//|/|\{|#|\?)")


def _rewrite_src(match):
    prefix, quote, path = match.groups()
    if not path or _SKIP.match(path):
        return match.group(0)
    if path.startswith("./"):
        path = path[2:]
    if path.startswith("content/"):
        path = path[len("content/"):]
    if not path.startswith("images/"):
        # Bare filename (Obsidian "shortest" link format): attachments
        # always land in content/images/.
        path = "images/" + path
    return "{}{}{{static}}/{}{}".format(prefix, quote, path, quote)


def _rewrite_img_tag(match):
    return _SRC_ATTR.sub(_rewrite_src, match.group(0))


def process_content(content):
    html = getattr(content, "_content", None)
    if not isinstance(html, str) or "<img" not in html:
        return
    content._content = _IMG_TAG.sub(_rewrite_img_tag, html)


def register():
    signals.content_object_init.connect(process_content)
