#!/usr/bin/env python
# -*- coding: utf-8 -*-

AUTHOR = 'secemp'
SITENAME = 'secemp Blog'
SITEURL = ''

PATH = 'content'
OUTPUT_PATH = 'output/'

TIMEZONE = 'UTC'
DEFAULT_LANG = 'en'

# Feed generation (disabled for dev)
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Theme
THEME = 'themes/secemp'

# URL structure (matches Jekyll's pretty permalinks)
ARTICLE_URL = '{date:%Y}/{date:%m}/{date:%d}/{slug}/'
ARTICLE_SAVE_AS = '{date:%Y}/{date:%m}/{date:%d}/{slug}/index.html'
PAGE_URL = '{slug}/'
PAGE_SAVE_AS = '{slug}/index.html'

# Archives URL (posts listing)
ARCHIVES_SAVE_AS = 'posts/index.html'
TAGS_SAVE_AS = 'tags/index.html'
CATEGORIES_SAVE_AS = 'categories/index.html'
AUTHORS_SAVE_AS = 'authors/index.html'

# Static paths
STATIC_PATHS = ['images', 'extra']
EXTRA_PATH_METADATA = {
    'extra/favicon.ico': {'path': 'favicon.ico'},
    'extra/CNAME': {'path': 'CNAME'},
}

# Markdown extensions
MARKDOWN = {
    'extension_configs': {
        'markdown.extensions.codehilite': {'css_class': 'highlight'},
        'markdown.extensions.extra': {},
        'markdown.extensions.meta': {},
        'markdown.extensions.toc': {'permalink': True},
    },
    'output_format': 'html5',
}

# Pagination
DEFAULT_PAGINATION = 6

# Future dated posts
WITH_FUTURE_DATES = True

# Relative URLs for dev
RELATIVE_URLS = True

# Menu
DISPLAY_PAGES_ON_MENU = True
DISPLAY_CATEGORIES_ON_MENU = False

# Social links
SOCIAL = (
    ('email', 'mailto:secemp9@gmail.com'),
    ('github', 'https://github.com/secemp9'),
    ('twitter', 'https://x.com/secemp9'),
    ('huggingface', 'https://huggingface.co/secemp9'),
)

# Site metadata for templates
SITESUBTITLE = 'Reverse engineering, ML, and systems notes from an independent researcher.'
PROFILE_IMAGE = '/theme/img/profile.webp'
OG_IMAGE = 'https://pbs.twimg.com/profile_images/1904889083505053698/fIdxky7Q_400x400.jpg'

# Homepage dossier panel
NOW = 'Agent tooling, model behavior, and reverse engineering workflows.'
FOCUS = 'llm evaluation · agent harnesses · systems'

# Homepage projects ledger: (name, url, blurb, kind)
PROJECTS = (
    ('elwood', 'https://github.com/secemp9/elwood',
     'Drop-in replacement for the Claude Code SDK via Babel AST instrumentation.', 'tool'),
    ('harn', 'https://github.com/secemp9/harn',
     'Full Python port of earendil\u2019s pi agent.', 'library'),
    ('rubrics', 'https://github.com/secemp9/rubrics',
     'A collection of rubrics for LLM judge use cases.', 'data'),
    ('niwa', 'https://github.com/secemp9/niwa',
     'Async conflict-aware spec and planning for users and their agents.', 'tool'),
    ('jari', 'https://github.com/secemp9/jari',
     'LMDB-backed task and issue tracker for agent workflows.', 'tool'),
    ('goal', 'https://github.com/secemp9/goal',
     'Port of /goal from Codex to arbitrary agents and harnesses.', 'tool'),
)

# Plugins (add as needed)
PLUGIN_PATHS = ['plugins']
# obsidian_image_links rewrites Obsidian-pasted relative image links
# (e.g. ![](images/Pasted%20image%20....png)) to {static}/images/... so
# the same markdown renders in Obsidian and on the published site.
PLUGINS = ['obsidian_image_links']

# Cache for faster rebuilds
CACHE_CONTENT = True
LOAD_CONTENT_CACHE = True
