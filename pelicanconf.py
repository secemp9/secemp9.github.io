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
SITESUBTITLE = 'ML researcher and pragmatic optimist. Writing about ideas and scaling.'
PROFILE_IMAGE = '/theme/img/profile.webp'
OG_IMAGE = 'https://pbs.twimg.com/profile_images/1904889083505053698/fIdxky7Q_400x400.jpg'

# Plugins (add as needed)
PLUGINS = []

# Cache for faster rebuilds
CACHE_CONTENT = True
LOAD_CONTENT_CACHE = True
