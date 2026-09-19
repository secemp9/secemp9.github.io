"""Exercise the actual authoring core, YAML reader, and nested-link publication."""

from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import subprocess
import tempfile
import unittest
from unittest import mock
from urllib.parse import quote, unquote, urlsplit

from pelican import Pelican
from pelican.readers import MarkdownReader
from pelican.settings import DEFAULT_CONFIG
import yaml

import new_post_pelican as authoring
from plugins.obsidian_metadata import ObsidianMarkdownReader, serialize_document, split_document
from plugins.obsidian_image_links import process_content
from test_sandbox import load_settings


ROOT = Path(__file__).resolve().parents[1]


class AuthoringTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='secemp-authoring-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.content = self.directory / 'content'
        self.content.mkdir()
        patch = mock.patch.object(authoring, 'CONTENT_DIR', self.content)
        patch.start()
        self.addCleanup(patch.stop)

    def write(self, filename, text):
        path = self.content / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8', newline='') as target:
            target.write(text)
        return path

    def test_prepare_is_read_only_and_creation_has_properties_and_empty_body(self):
        plan = authoring.prepare_post('A title: café', tags=['python', 'ml'])
        self.assertFalse(list(self.content.iterdir()))
        metadata, body, kind = split_document(plan['content'])
        self.assertEqual(kind, 'yaml')
        self.assertEqual(metadata['title'], 'A title: café')
        self.assertEqual(metadata['tags'], ['python', 'ml'])
        self.assertEqual(metadata['status'], 'hidden')
        self.assertEqual(metadata['slug'], 'a-title-cafe')
        self.assertEqual(body.strip(), '')
        self.assertNotIn('Write your post', plan['content'])

    def test_duplicate_titles_get_distinct_filenames_slugs_and_output_routes(self):
        first = authoring.create_post('Same post')
        second = authoring.create_post('Same post')
        self.assertEqual((first['slug'], second['slug']), ('same-post', 'same-post-2'))
        self.assertNotEqual(first['path'], second['path'])
        self.assertNotEqual(authoring.preview_info(first['path'])['url'],
                            authoring.preview_info(second['path'])['url'])

    def test_nested_existing_slug_is_reserved_even_when_filename_differs(self):
        now = datetime.now().astimezone().isoformat(timespec='minutes')
        self.write('nested/renamed.md', serialize_document({'title': 'Old', 'date': now, 'slug': 'new-name'}))
        self.assertEqual(authoring.prepare_post('New name')['slug'], 'new-name-2')

    def test_yaml_without_status_stays_unlisted_when_converted_or_listed(self):
        path = self.write('native.md', serialize_document({'title': 'Native', 'date': '2026-01-02'}))
        self.assertEqual(authoring.preview_info(path)['status'], 'hidden')
        self.assertEqual(authoring.list_posts()[0]['status'], 'hidden')
        result = authoring.transform_note(path, properties=True)
        self.assertEqual(split_document(result['content'])[0]['status'], 'hidden')

    def test_blank_titles_and_control_characters_cannot_create_files(self):
        # Each input violates the required nonempty, single-line title contract.
        for value in ('', '  ', 'Title\nStatus: published', 'bad\x00title'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                authoring.create_post(value)
        self.assertEqual(list(self.content.iterdir()), [])
        self.assertEqual(authoring.prepare_post('你好')['slug'], 'post')

    def test_exclusive_creation_does_not_overwrite_a_racing_writer(self):
        plan = authoring.prepare_post('Race')
        path = self.directory / plan['path']
        path.write_text('Another writer owns this file', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            authoring._create(plan)
        self.assertEqual(path.read_text(), 'Another writer owns this file')

    def test_conversion_preserves_legacy_body_and_existing_visibility(self):
        original = 'Title: Legacy\r\nDate: 2026-01-02 12:00\r\nSlug: stable\r\nTags: a, b\r\n\r\nExact body.\r\n\r\n'
        path = self.write('legacy.md', original)
        result = authoring.transform_note(path, properties=True)
        self.assertEqual(result['original_sha256'], hashlib.sha256(original.encode()).hexdigest())
        metadata, body, kind = split_document(result['content'])
        self.assertEqual((metadata['slug'], metadata['status']), ('stable', 'published'))
        self.assertEqual(metadata['tags'], ['a', 'b'])
        self.assertEqual(body, 'Exact body.\r\n\r\n')
        self.assertEqual(path.read_bytes(), original.encode())
        before = authoring.preview_info(path)['url']
        authoring._write_transform(result)
        self.assertEqual(authoring.preview_info(path)['url'], before)

    def test_status_edit_does_not_modify_a_status_line_in_the_body(self):
        path = self.write('legacy.md', 'Title: Legacy\nDate: 2026-01-02\nSlug: legacy\n\nStatus: body text\n')
        result = authoring.transform_note(path, status='hidden')
        metadata, body, kind = split_document(result['content'])
        self.assertEqual((kind, metadata['status']), ('legacy', 'hidden'))
        self.assertEqual(body, 'Status: body text\n')
        path.write_text('New edits', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'changed'):
            authoring._write_transform(result)
        self.assertEqual(path.read_text(), 'New edits')

    def test_import_keeps_the_existing_date_status_and_body(self):
        source = self.directory / 'source.md'
        body = '\nBody without instructions.\n'
        source.write_text(serialize_document({'title': 'Imported', 'date': '2020-02-03',
                                             'slug': 'original', 'status': 'draft'}, body))
        result = authoring.import_post(source)
        self.assertEqual(result['path'], 'content/2020-02-03-original.md')
        metadata, imported_body, _ = split_document((self.directory / result['path']).read_text())
        self.assertEqual(metadata['status'], 'draft')
        self.assertEqual(imported_body, body)

    def test_preview_uses_real_pelican_routes_for_posts_pages_and_drafts(self):
        cases = (
            ('note.md', {'title': 'Note', 'date': '2026-02-03', 'slug': 'stable', 'status': 'hidden'}, '2026/02/03/stable/'),
            ('draft.md', {'title': 'Draft', 'date': '2026-02-03', 'slug': 'unfinished', 'status': 'draft'}, 'drafts/unfinished.html'),
            ('pages/page.md', {'title': 'Page', 'slug': 'page', 'status': 'hidden'}, 'page/'),
            ('pages/404.md', {'title': '404', 'slug': '404', 'save_as': '404.html'}, '404.html'),
        )
        # Each source class and status predicts its existing Pelican output location.
        for name, metadata, route in cases:
            path = self.write(name, serialize_document(metadata))
            self.assertEqual(authoring.preview_info(path)['url'], 'http://localhost:4010/' + route)

    def test_note_edits_reject_outside_paths_and_removal_is_exact_and_recoverable(self):
        outside = self.directory / 'outside.md'
        outside.write_text('Not a blog note')
        with self.assertRaises(ValueError):
            authoring.transform_note(outside, status='published')
        path = self.write('some-note.md', 'Title: Some note\nSlug: some-note\n\nBody')
        with self.assertRaises(ValueError):
            authoring.remove_post('some')
        result = authoring.remove_post('some-note')
        self.assertFalse(path.exists())
        self.assertTrue((self.directory / result['trash']).read_text().endswith('Body'))


class PropertiesTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='secemp-properties-')
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'note.md'
        self.settings = deepcopy(DEFAULT_CONFIG)

    def read(self, text, reader=ObsidianMarkdownReader):
        self.path.write_text(text, encoding='utf-8')
        return reader(self.settings).read(self.path)

    def test_native_properties_and_body_colons_are_independent(self):
        html, metadata = self.read('---\ntitle: "A title: café"\ndate: 2026-01-02\ntags:\n- python\n- ml\n---\nNote: keep this sentence.\n')
        self.assertIn('Note: keep this sentence.', html)
        self.assertEqual(metadata['title'], 'A title: café')
        self.assertEqual([str(tag) for tag in metadata['tags']], ['python', 'ml'])
        self.assertEqual(metadata['date'].strftime('%Y-%m-%d'), '2026-01-02')
        self.assertEqual(metadata['status'], 'hidden')

    def test_legacy_reader_output_is_unchanged(self):
        source = 'Title: Existing\nDate: 2026-01-02\nTags: one, two\n\nBody **bold**.\n'
        self.assertEqual(self.read(source), self.read(source, MarkdownReader))

    def test_bad_yaml_is_rejected_not_silently_reinterpreted(self):
        invalid = (
            '---\ntitle: Missing end\n',
            '---\n- a\n- b\n---\n',
            '---\nfalse\n---\n',
            '---\ntitle: One\nTitle: Two\n---\n',
            '---\nstatus: false\n---\n',
            '---\ntags: [one, 2]\n---\n',
            '---\ncategory: [one]\n---\n',
            '---\nnested: {key: value}\n---\n',
            '---\n!!python/object/apply:os.system [echo unsafe]\n---\n',
        )
        # Each malformed header must fail before generating any article content.
        for source in invalid:
            with self.subTest(source=source), self.assertRaises((ValueError, yaml.YAMLError)):
                self.read(source)

    def test_plain_colon_paragraph_is_not_a_legacy_metadata_header(self):
        source = 'Note: this is prose\n\nMore prose.\n'
        self.assertEqual(split_document(source), ({}, source, 'plain'))


class ObsidianLinkTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='secemp-links-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.content = self.directory / 'content'
        (self.content / 'images').mkdir(parents=True)
        self.source = self.content / 'nested/deep/note.md'
        self.source.parent.mkdir(parents=True)

    def rewrite(self, html):
        content = SimpleNamespace(_content=html, source_path=str(self.source),
                                  settings={'PATH': str(self.content)})
        process_content(content)
        return content._content

    def test_nested_images_note_links_headings_and_attributes(self):
        html = '<a href="../../other.md#A%20Heading">Other</a><img data-src="untouched.png" src="../../images/caf%C3%A9%2C%20image.png" alt="a > b"><a href="#A%20Heading">Jump</a>'
        result = self.rewrite(html)
        self.assertIn('href="{filename}/other.md#a-heading"', result)
        self.assertIn('src="{static}/images/caf%C3%A9%2C%20image.png"', result)
        self.assertIn('data-src="untouched.png"', result)
        self.assertIn('alt="a > b"', result)
        self.assertIn('href="#a-heading"', result)

    def test_external_site_root_and_existing_pelican_links_stay_unchanged(self):
        html = '<a href="https://example.org/a.md?q=1&amp;x=2">A</a><a href="/about/">B</a><img src="{static}/images/x.png"><img src="data:image/png;base64,abc">'
        self.assertEqual(self.rewrite(html), html)

    def test_escape_and_symlink_escape_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'escapes'):
            self.rewrite('<a href="../../../private.pdf">Outside</a>')
        outside = self.directory / 'private.png'
        outside.write_bytes(b'private fixture')
        (self.content / 'images/link.png').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            self.rewrite('<img src="../../images/link.png">')

    def test_real_build_copies_encoded_assets_and_resolves_legacy_and_yaml_notes(self):
        names = ['café, image.png', 'literal%20.png']
        # Both fixtures must be copied once under their real, decoded filesystem names.
        for name in names:
            (self.content / 'images' / name).write_bytes(b'image fixture')
        self.source.write_text(serialize_document({
            'title': 'Native properties', 'date': '2026-01-02', 'slug': 'native',
            'tags': ['python', 'ml'], 'status': 'hidden',
        }, '\n[Other](../../other.md#A%20Heading)\n\n' + '\n\n'.join(
            f'![image](../../images/{quote(name)})' for name in names)), encoding='utf-8')
        (self.content / 'other.md').write_text('Title: Other\nDate: 2026-01-01\nSlug: other\n\n## A Heading\n')
        pages = self.content / 'pages'
        pages.mkdir()
        (pages / 'page.md').write_text(serialize_document({'title': 'Page', 'slug': 'page'},
                                                        '\n[Native](../nested/deep/note.md)\n'))
        output = self.directory / 'output'
        settings = load_settings('publishconf.py', PATH=str(self.content), OUTPUT_PATH=str(output),
                                 CACHE_PATH=str(self.directory / 'cache'),
                                 STATIC_PATHS=['images'], EXTRA_PATH_METADATA={})
        with redirect_stdout(StringIO()):
            Pelican(settings).run()
        html = (output / '2026/01/02/native/index.html').read_text()
        self.assertIn('href="https://secemp.blog/2026/01/01/other/#a-heading"', html)
        self.assertNotIn('{static}', html)
        self.assertNotIn('{filename}', html)
        self.assertIn('noindex, nofollow, noimageindex', html)
        # Every generated image URL must identify exactly the file that was copied.
        from html.parser import HTMLParser
        class Images(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == 'img':
                    url = dict(attrs).get('src', '')
                    if '/images/' in url:
                        self.paths.append(unquote(urlsplit(url).path.lstrip('/')))
        images = Images()
        images.paths = []
        images.feed(html)
        self.assertEqual(images.paths, ['images/' + name for name in names])
        self.assertTrue(all((output / image).is_file() for image in images.paths))
        self.assertIn('https://secemp.blog/2026/01/02/native/', (output / 'page/index.html').read_text())


if __name__ == '__main__':
    unittest.main()
