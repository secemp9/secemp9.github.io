"""Build the real theme against temporary content to check publication boundaries.

Run with: python -m unittest discover -s tests -v
"""

from contextlib import redirect_stdout
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import urlsplit

from pelican import Pelican
from pelican.settings import read_settings


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ARTICLE = "2026/01/01/public-control/index.html"
HIDDEN_ARTICLE = "2026/01/02/unlisted-preview/index.html"
HIDDEN_PAGE = "preview-notes/index.html"
PUBLIC_TITLE = 'Public "quoted" & complete'
PUBLIC_SUMMARY = 'A "quoted" & complete description.'
HIDDEN_TITLE = "UNLISTEDARTICLE_SENTINEL"
PAGE_TITLE = "UNLISTEDPAGE_SENTINEL"


class Document(HTMLParser):
    """Read actual parsed metadata and links, including entity decoding."""

    def __init__(self, html):
        super().__init__()
        self.meta = {}
        self.links = []
        self.navigation_links = []
        self._main_navigation = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "nav" and attrs.get("aria-label") == "Main navigation":
            self._main_navigation = True
        elif tag == "meta":
            self.meta[attrs.get("name") or attrs.get("property")] = attrs.get(
                "content", ""
            )
        elif tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
            if self._main_navigation:
                self.navigation_links.append(attrs["href"])

    def handle_endtag(self, tag):
        if tag == "nav":
            self._main_navigation = False


class VisibilityIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="secemp-visibility-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.content = self.directory / "content"
        self.output = self.directory / "output"
        self.content.mkdir()
        self.write_content(
            "public.md",
            {
                "Title": PUBLIC_TITLE,
                "Date": "2026-01-01 12:00",
                "Slug": "public-control",
                "Status": "published",
                "Summary": PUBLIC_SUMMARY,
                "Tags": "shared",
                "Category": "public-category",
                "Author": "Public Author",
            },
        )
        self.write_visibility("hidden")
        self.write_content(
            "unfinished.md",
            {
                "Title": "DRAFTARTICLE_SENTINEL",
                "Date": "2026-01-03 12:00",
                "Slug": "unfinished-article",
                "Status": "draft",
                "Tags": "draft-only",
                "Category": "draft-category",
                "Author": "Draft Author",
            },
        )
        self.write_content(
            "pages/unfinished.md",
            {
                "Title": "DRAFTPAGE_SENTINEL",
                "Slug": "unfinished-page",
                "Status": "draft",
            },
        )
        self.write_about("published")
        self.write_content(
            "pages/404.md",
            {"Title": "404", "Status": "hidden", "Save_as": "404.html"},
        )

    def write_content(self, filename, metadata):
        path = self.content / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        # Each fixture must produce precisely its declared Pelican metadata.
        header = "\n".join(f"{key}: {value}" for key, value in metadata.items())
        path.write_text(f"{header}\n\nFixture body for {metadata['Title']}.\n", encoding="utf-8")

    def write_visibility(self, status):
        self.write_content(
            "preview.md",
            {
                "Title": HIDDEN_TITLE,
                "Date": "2026-01-02 12:00",
                "Slug": "unlisted-preview",
                "Status": status,
                "Tags": "shared, hidden-only",
                "Category": "hidden-category",
                "Author": "Hidden Author",
            },
        )
        self.write_content(
            "pages/preview.md",
            {"Title": PAGE_TITLE, "Slug": "preview-notes", "Status": status},
        )

    def write_about(self, status):
        self.write_content(
            "pages/about.md",
            {"Title": "About", "Slug": "about", "Status": status},
        )

    def build(self, production=True):
        # Only inputs, outputs and caches move; publication policy comes from
        # the actual repository configuration and templates under test.
        config = ROOT / ("publishconf.py" if production else "pelicanconf.py")
        with mock.patch.object(sys, "path", [str(ROOT), *sys.path]):
            settings = read_settings(
                str(config),
                override={
                    "PATH": str(self.content),
                    "OUTPUT_PATH": str(self.output),
                    "CACHE_PATH": str(self.directory / "cache"),
                    "CACHE_CONTENT": False,
                    "LOAD_CONTENT_CACHE": False,
                    "STATIC_PATHS": [],
                    "EXTRA_PATH_METADATA": {},
                },
            )
            with redirect_stdout(StringIO()):
                Pelican(settings).run()

    def read_output(self, relative):
        path = self.output / relative
        self.assertTrue(path.is_file(), f"Missing generated page: {relative}")
        return path.read_text(encoding="utf-8")

    def assert_unindexed(self, relative):
        document = Document(self.read_output(relative))
        directives = {part.strip() for part in document.meta.get("robots", "").split(",")}
        self.assertTrue(
            {"noindex", "nofollow", "noimageindex"}.issubset(directives),
            f"Missing crawler restrictions on {relative}: {directives}",
        )
        self.assertEqual(document.meta.get("referrer"), "no-referrer", relative)

    def assert_public(self, relative):
        document = Document(self.read_output(relative))
        self.assertNotIn("noindex", document.meta.get("robots", ""), relative)

    def navigation_paths(self):
        document = Document(self.read_output("index.html"))
        return {urlsplit(link).path for link in document.navigation_links}

    def assert_no_public_leaks(self, extra_private=(), extra_markers=()):
        private_paths = {HIDDEN_ARTICLE, HIDDEN_PAGE, "404.html", *extra_private}
        markers = (
            HIDDEN_TITLE,
            PAGE_TITLE,
            "unlisted-preview/",
            "preview-notes/",
            "DRAFTARTICLE_SENTINEL",
            "DRAFTPAGE_SENTINEL",
            "unfinished-article",
            "unfinished-page",
            *extra_markers,
        )
        # Native hidden/draft collections must leave no references in any
        # generated public HTML, feeds, or future XML sitemap.
        for path in self.output.rglob("*"):
            if path.suffix not in {".html", ".xml"}:
                continue
            relative = path.relative_to(self.output).as_posix()
            if relative in private_paths:
                continue
            contents = path.read_text(encoding="utf-8")
            # Every predefined private marker must be absent in this artifact.
            for marker in markers:
                self.assertNotIn(marker, contents, f"Private reference in {relative}")

    def assert_private_taxonomy_absent(self):
        # Tags, categories and authors belonging only to previews/drafts must
        # not generate discovery pages or category feeds.
        for relative in (
            "tag/hidden-only.html",
            "category/hidden-category.html",
            "author/hidden-author.html",
            "feeds/hidden-category.atom.xml",
            "tag/draft-only.html",
            "category/draft-category.html",
            "author/draft-author.html",
            "feeds/draft-category.atom.xml",
        ):
            self.assertFalse((self.output / relative).exists(), relative)

    def test_production_unlisted_content_is_directly_viewable_without_discovery(self):
        self.build()
        self.assert_unindexed(HIDDEN_ARTICLE)
        self.assert_unindexed(HIDDEN_PAGE)
        self.assert_unindexed("404.html")
        self.assert_public(PUBLIC_ARTICLE)
        self.assert_no_public_leaks()
        self.assert_private_taxonomy_absent()

        public_url = "2026/01/01/public-control/"
        # The published control must appear in every enabled discovery surface.
        for relative in (
            "index.html",
            "posts/index.html",
            "tag/shared.html",
            "category/public-category.html",
            "author/public-author.html",
            "feeds/all.atom.xml",
            "feeds/public-category.atom.xml",
        ):
            self.assertIn(public_url, self.read_output(relative), relative)

        preview = Document(self.read_output(HIDDEN_ARTICLE))
        self.assertFalse(
            any("/tag/hidden-only" in link for link in preview.links),
            "Preview-only tags must not link to nonexistent public archives",
        )

    def test_status_round_trip_preserves_urls_and_removes_stale_discovery(self):
        self.build()
        self.assert_unindexed(HIDDEN_ARTICLE)
        self.assert_unindexed(HIDDEN_PAGE)
        self.assertNotIn("/preview-notes/", self.navigation_paths())

        self.write_visibility("published")
        self.build()
        self.assert_public(HIDDEN_ARTICLE)
        self.assert_public(HIDDEN_PAGE)
        self.assertIn("/preview-notes/", self.navigation_paths())
        # Publishing must expose the same article URL in indexes and feeds.
        for relative in (
            "index.html",
            "posts/index.html",
            "tag/shared.html",
            "tag/hidden-only.html",
            "category/hidden-category.html",
            "author/hidden-author.html",
            "feeds/all.atom.xml",
            "feeds/hidden-category.atom.xml",
        ):
            self.assertIn("2026/01/02/unlisted-preview/", self.read_output(relative), relative)

        self.write_visibility("hidden")
        self.build()
        self.assert_unindexed(HIDDEN_ARTICLE)
        self.assert_unindexed(HIDDEN_PAGE)
        self.assertNotIn("/preview-notes/", self.navigation_paths())
        self.assert_no_public_leaks()
        self.assert_private_taxonomy_absent()

    def test_local_drafts_are_unindexed_and_removed_by_production_build(self):
        self.build(production=False)
        self.assert_unindexed("drafts/unfinished-article.html")
        self.assert_unindexed("drafts/pages/unfinished-page.html")

        self.build()
        self.assertFalse((self.output / "drafts/unfinished-article.html").exists())
        self.assertFalse((self.output / "drafts/pages/unfinished-page.html").exists())
        self.assert_no_public_leaks()

    def test_translated_and_custom_path_drafts_remain_local(self):
        cases = (
            (
                "unfinished-fr.md", "unfinished-article", "fr", None,
                "drafts/unfinished-article-fr.html",
            ),
            (
                "pages/unfinished-fr.md", "unfinished-page", "fr", None,
                "drafts/pages/unfinished-page-fr.html",
            ),
            (
                "custom-article.md", "custom-article", "en",
                "review/custom-article/index.html", "review/custom-article/index.html",
            ),
            (
                "custom-article-fr.md", "custom-article", "fr",
                "review/custom-article-fr/index.html", "review/custom-article-fr/index.html",
            ),
            (
                "pages/custom-page.md", "custom-page", "en",
                "review/custom-page/index.html", "review/custom-page/index.html",
            ),
            (
                "pages/custom-page-fr.md", "custom-page", "fr",
                "review/custom-page-fr/index.html", "review/custom-page-fr/index.html",
            ),
        )
        # Every article/page language and custom-path case must be available
        # at its declared local URL but produce no production HTML.
        for filename, slug, language, save_as, _ in cases:
            metadata = {
                "Title": f"DRAFTMATRIX_SENTINEL {slug} {language}",
                "Date": "2026-01-03 12:00",
                "Slug": slug,
                "Lang": language,
                "Status": "draft",
            }
            if save_as:
                metadata["Save_as"] = save_as
                metadata["Url"] = save_as.removesuffix("index.html")
            self.write_content(filename, metadata)

        self.build()
        self.assert_no_public_leaks(extra_markers=("DRAFTMATRIX_SENTINEL",))
        # Production suppresses both native draft paths and explicit overrides.
        for *_, relative in cases:
            self.assertFalse((self.output / relative).exists(), relative)

        # Reusing this process after a production build must not let the
        # registered production plugin suppress development drafts.
        self.build(production=False)
        # All six local outputs must retain crawler and referrer restrictions.
        for *_, relative in cases:
            self.assert_unindexed(relative)

        self.build()
        # Rebuilding production in the same directory removes every old draft.
        for *_, relative in cases:
            self.assertFalse((self.output / relative).exists(), relative)
        self.assert_no_public_leaks(extra_markers=("DRAFTMATRIX_SENTINEL",))

    def test_pagination_lists_distinct_complete_article_slices(self):
        # Eight published articles with page size six must yield Feb 7–2 on
        # index.html, then Feb 1 and the Jan 1 public control on index2.html.
        for day in range(1, 8):
            self.write_content(
                f"pagination-{day}.md",
                {
                    "Title": f"Pagination article {day}",
                    "Date": f"2026-02-{day:02d} 12:00",
                    "Slug": f"pagination-{day}",
                    "Status": "published",
                },
            )
        self.build()
        first_page = Document(self.read_output("index.html"))
        second_page = Document(self.read_output("index2.html"))

        def article_paths(document):
            return [
                urlsplit(link).path for link in document.links
                if urlsplit(link).path.startswith("/2026/")
            ]

        self.assertEqual(
            article_paths(first_page),
            [f"/2026/02/{day:02d}/pagination-{day}/" for day in (7, 6, 5, 4, 3, 2)],
        )
        self.assertEqual(
            article_paths(second_page),
            ["/2026/02/01/pagination-1/", "/2026/01/01/public-control/"],
        )
        self.assertIn("/index2.html", {urlsplit(link).path for link in first_page.links})
        self.assert_no_public_leaks()

    def test_hiding_about_removes_hardcoded_navigation_links(self):
        self.write_about("hidden")
        self.build()
        self.assert_unindexed("about/index.html")
        self.assert_no_public_leaks(extra_private=("about/index.html",))
        # Even historically hardcoded About links must obey page visibility.
        for path in self.output.rglob("*.html"):
            document = Document(path.read_text(encoding="utf-8"))
            about_links = [link for link in document.links if urlsplit(link).path == "/about/"]
            self.assertEqual(about_links, [], str(path.relative_to(self.output)))

    def test_quotes_and_ampersands_survive_parsed_article_metadata(self):
        self.build()
        document = Document(self.read_output(PUBLIC_ARTICLE))
        self.assertEqual(document.meta.get("og:title"), PUBLIC_TITLE)
        self.assertEqual(document.meta.get("twitter:title"), PUBLIC_TITLE)
        self.assertEqual(document.meta.get("description"), PUBLIC_SUMMARY)
        self.assertEqual(document.meta.get("og:description"), PUBLIC_SUMMARY)
        self.assertEqual(document.meta.get("twitter:description"), PUBLIC_SUMMARY)


if __name__ == "__main__":
    unittest.main()
