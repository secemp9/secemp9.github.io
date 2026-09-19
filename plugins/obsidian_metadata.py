"""Native Obsidian properties with unchanged handling of legacy Pelican posts."""

from datetime import date, datetime
from pathlib import Path
import re

from markdown import Markdown
from pelican import signals
from pelican.readers import MarkdownReader
import yaml


class PropertiesLoader(yaml.SafeLoader):
    """Reject duplicate properties, including differently-cased spellings."""


def _properties_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    # Each YAML property must have one unique, case-insensitive text key.
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or not key.strip():
            raise ValueError('Property names must be nonempty strings')
        key = key.strip().lower()
        if key in result:
            raise ValueError(f'Duplicate property: {key}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


PropertiesLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                                 _properties_mapping)


def normalize_properties(properties):
    """Return flat metadata accepted by Obsidian and Pelican."""
    if not isinstance(properties, dict):
        raise ValueError('Properties must be a YAML mapping, not a list or scalar')
    result = {}
    # Flat scalar properties and string lists retain values; nesting is rejected.
    for key, value in properties.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError('Property names must be nonempty strings')
        key = key.strip().lower()
        if key in result:
            raise ValueError(f'Duplicate property: {key}')
        if value is None:
            continue
        if isinstance(value, (date, datetime)):
            value = value.isoformat()
        if isinstance(value, dict) or (isinstance(value, list) and
                                      any(not isinstance(item, str) for item in value)):
            raise ValueError(f'Property {key!r} must be a scalar or a list of strings')
        if key in {'title', 'date', 'modified', 'status', 'slug', 'url', 'save_as', 'image', 'author', 'category', 'lang'}:
            if not isinstance(value, str):
                raise ValueError(f'Property {key!r} must be text or an ISO date')
            if key == 'status' and value not in {'hidden', 'published', 'draft'}:
                raise ValueError('status must be hidden, published, or draft')
        if key in {'tags', 'authors', 'cssclasses'} and not isinstance(value, (str, list)):
            raise ValueError(f'Property {key!r} must be text or a list of strings')
        result[key] = value
    return result


def split_document(text):
    """Return (metadata, exact body, format) for YAML, legacy headers, or plain Markdown."""
    text = text.removeprefix('\ufeff')
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == '---':
        # A YAML header ends at its first explicit closing delimiter.
        for index, line in enumerate(lines[1:], 1):
            if line.strip() in {'---', '...'}:
                raw = yaml.load(''.join(lines[1:index]), Loader=PropertiesLoader)
                return normalize_properties({} if raw is None else raw), ''.join(lines[index + 1:]), 'yaml'
        raise ValueError('YAML properties need a closing --- delimiter')

    metadata = {}
    last_key = None
    # Only the contiguous leading Key: Value block with a title is legacy metadata.
    for index, line in enumerate(lines):
        if not line.strip():
            if 'title' in metadata:
                return metadata, ''.join(lines[index + 1:]), 'legacy'
            break
        match = re.match(r'^([A-Za-z][A-Za-z0-9_-]*):[ \t]*(.*?)[\r\n]*$', line)
        if match:
            key, value = match.groups()
            key = key.lower()
            if key in metadata:
                raise ValueError(f'Duplicate property: {key}')
            metadata[key] = value
            last_key = key
        elif line[:1].isspace() and last_key:
            metadata[last_key] += '\n' + line.strip()
        else:
            break
    else:
        if 'title' in metadata:
            return metadata, '', 'legacy'
    return {}, text, 'plain'


def serialize_document(metadata, body=''):
    """Emit properties with no instructional filler and preserve the supplied body."""
    header = yaml.safe_dump(normalize_properties(metadata), allow_unicode=True,
                            sort_keys=False, default_flow_style=False, width=1000)
    return '---\n' + header + '---\n' + body


class ObsidianMarkdownReader(MarkdownReader):
    def read(self, source_path):
        text = Path(source_path).read_text(encoding='utf-8-sig')
        # Obsidian can create an empty scratch note before any post metadata exists.
        if not text.strip():
            return '', {'status': 'skip'}
        # Legacy posts keep the exact original Pelican reader and metadata semantics.
        if not text.startswith('---\n') and not text.startswith('---\r\n'):
            return super().read(source_path)
        raw, body, _ = split_document(text)
        raw.setdefault('status', 'hidden')
        parser = Markdown(**self.settings['MARKDOWN'])
        parser.preprocessors.deregister('meta')
        html = parser.convert(body)
        metadata = {}
        # Only the YAML header supplies metadata; body-leading colons remain content.
        for name, value in raw.items():
            if name in {'tags', 'authors'}:
                metadata[name] = self.process_metadata(name, value)
            elif name in self.settings['FORMATTED_FIELDS']:
                metadata[name] = self.process_metadata(name, parser.reset().convert(str(value)))
            else:
                if not isinstance(value, (str, list)):
                    value = str(value).lower() if isinstance(value, bool) else str(value)
                metadata[name] = self.process_metadata(name, value)
        return html, metadata


def add_reader(readers):
    # All normal Markdown suffixes use the same backward-compatible reader.
    for extension in MarkdownReader.file_extensions:
        readers.reader_classes[extension] = ObsidianMarkdownReader


def register():
    signals.readers_init.connect(add_reader)
