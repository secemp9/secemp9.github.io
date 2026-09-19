"""Resolve Markdown note links and attachments relative to their source note.

Local notes become Pelican {filename} references; attachments become {static}.
Existing Pelican references, external URLs and site-root URLs stay unchanged.
Resolved files must remain inside content/, including through symbolic links.
"""

from html import escape, unescape
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from markdown.extensions.toc import slugify
from pelican import signals
from pelican.generators import Generator


_TAG = re.compile(r'''<(?P<tag>img|a)\b(?:"[^"]*"|'[^']*'|[^'">])*>''', re.I)
_ATTR = re.compile(r'''(?P<prefix>\s+(?P<attr>src|href)\s*=\s*)(?P<quote>["'])(?P<url>.*?)(?P=quote)''', re.I)
_SKIP = re.compile(r'^(?:[A-Za-z][A-Za-z0-9+.\-]*:|//|/|\{|\?)')
_MARKDOWN = {'.md', '.markdown', '.mkd', '.mdown'}


def resolve_source_path(content, path, image=False):
    root = Path(content.settings['PATH']).resolve()
    source = Path(content.source_path).resolve()
    path = unquote(path)
    if '\\' in path or '\x00' in path:
        raise ValueError(f'Invalid attachment or note path: {path!r}')
    if path.startswith('content/'):
        candidate = root / path[len('content/'):]
    else:
        candidate = source.parent / path
        # Historical root-image and bare-filename links remain supported.
        if image and not candidate.exists():
            if path.startswith('images/'):
                candidate = root / path
            elif '/' not in path:
                candidate = root / 'images' / path
    candidate = candidate.resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f'Link escapes content/: {path!r} in {content.source_path}')
    return candidate.relative_to(root).as_posix()


def _rewrite_url(content, url, image):
    decoded = unescape(url)
    if not decoded or _SKIP.match(decoded):
        return url
    parts = urlsplit(decoded)
    if not parts.path:
        if parts.fragment and not parts.fragment.startswith('^'):
            return '#' + slugify(unquote(parts.fragment), '-')
        return url
    suffix = Path(unquote(parts.path)).suffix.lower()
    if not image and not suffix:
        return url  # Extensionless web routes are not note filenames.
    path = resolve_source_path(content, parts.path, image=image)
    kind = 'filename' if suffix in _MARKDOWN and not image else 'static'
    fragment = parts.fragment
    if kind == 'filename' and fragment and not fragment.startswith('^'):
        fragment = slugify(unquote(fragment), '-')
    target = urlunsplit(('', '', '{' + kind + '}/' + quote(path, safe='/'),
                        parts.query, fragment))
    return escape(target, quote=True)


def process_content(content):
    html = getattr(content, '_content', None)
    if not isinstance(html, str) or not getattr(content, 'source_path', None):
        return

    def rewrite_tag(tag):
        image = tag.group('tag').lower() == 'img'

        def rewrite_attribute(attribute):
            if attribute.group('attr').lower() != ('src' if image else 'href'):
                return attribute.group(0)
            url = _rewrite_url(content, attribute.group('url'), image)
            return attribute.group('prefix') + attribute.group('quote') + url + attribute.group('quote')

        return _ATTR.sub(rewrite_attribute, tag.group(0))

    content._content = _TAG.sub(rewrite_tag, html)


class DecodeStaticLinks(Generator):
    def generate_context(self):
        # Pelican 4.12 only decodes %20 while collecting static paths. Decode
        # once after every article/page and before StaticGenerator runs last.
        self.context['static_links'] = {
            unquote(unescape(path)) for path in self.context['static_links']
        }


def get_generators(pelican):
    return DecodeStaticLinks


def register():
    signals.content_object_init.connect(process_content)
    signals.get_generators.connect(get_generators)
