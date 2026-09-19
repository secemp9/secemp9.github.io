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
    'extra/og-image.png': {'path': 'og-image.png'},
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
OG_IMAGE = 'https://secemp.blog/og-image.png'

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

# Donation methods: add only your own hosted checkout URL and receiving addresses.
# An empty collection leaves the corresponding payment method unavailable.
DONATION_CARD_URL = 'https://buy.stripe.com/6oU00j3Bk7Y54bxdHkd3i00'
DONATION_CARD_PROVIDER = 'Stripe'
# Public Phantom receiving addresses supplied by the owner on 2026-09-19.
# Equal EVM addresses do not make networks interchangeable. No private keys.
_DONATION_EVM_ADDRESS = '0x77334ce2f9bebdcb35d294eb93fab0175a844186'
DONATION_WALLETS = (
    {'id': 'solana-sol', 'network': 'solana', 'network_label': 'Solana',
     'asset': 'SOL', 'address': '8n5UNHa2rGoqw4tMLQcgBeywEC4HBDeYK6eijHBDRCDM'},
    {'id': 'ethereum-eth', 'network': 'ethereum', 'network_label': 'Ethereum',
     'asset': 'ETH', 'address': _DONATION_EVM_ADDRESS},
    # One BTC option: Native SegWit, not the separate Taproot receiving address.
    {'id': 'bitcoin-btc', 'network': 'bitcoin', 'network_label': 'Bitcoin',
     'asset': 'BTC', 'address': 'bc1qm3zuxj2ty99awg3fka52ryythjp5m59ks7n0g6'},
    {'id': 'base-eth', 'network': 'base', 'network_label': 'Base',
     'asset': 'ETH', 'address': _DONATION_EVM_ADDRESS},
    {'id': 'sui-sui', 'network': 'sui', 'network_label': 'Sui',
     'asset': 'SUI', 'address': '0xcf4d0ca54490e10bb35d4f909b8e303fa75fa350f7d0fd8ad0cad73de194a9da'},
    {'id': 'polygon-pol', 'network': 'polygon', 'network_label': 'Polygon',
     'asset': 'POL', 'address': _DONATION_EVM_ADDRESS},
    {'id': 'hyperevm-hype', 'network': 'hyperevm', 'network_label': 'HyperEVM',
     'asset': 'HYPE', 'address': _DONATION_EVM_ADDRESS},
    {'id': 'robinhood-eth', 'network': 'robinhood', 'network_label': 'Robinhood Chain',
     'asset': 'ETH', 'address': _DONATION_EVM_ADDRESS},
)
# Monthly plans: id, amount (decimal string), currency (e.g. EUR), url.
# Each URL must be a separate monthly Stripe Payment Link matching its amount.
# Configure the hosted customer portal with cancellation enabled before adding plans.
DONATION_MONTHLY_PLANS = (
    {'id': 'eur-5', 'amount': '5', 'currency': 'EUR',
     'url': 'https://buy.stripe.com/4gM14n2xg3HP9vRfPsd3i03'},
    {'id': 'eur-10', 'amount': '10', 'currency': 'EUR',
     'url': 'https://buy.stripe.com/28E8wP1tc1zH37tcDgd3i04'},
    {'id': 'eur-25', 'amount': '25', 'currency': 'EUR',
     'url': 'https://buy.stripe.com/8x214ndbU5PXdM79r4d3i01'},
)
# Optional recurring unit-price checkout: url, unit_amount (decimal string), currency.
# Enable adjustable quantity in Stripe; the blog never creates or changes charges.
DONATION_MONTHLY_CUSTOM = {
    'url': 'https://buy.stripe.com/4gM7sLgo6dip5fBdHkd3i02',
    'unit_amount': '1',
    'currency': 'EUR',
}
DONATION_CUSTOMER_PORTAL_URL = 'https://billing.stripe.com/p/login/6oU00j3Bk7Y54bxdHkd3i00'
DONATION_GITHUB_SPONSORS_URL = ''
DONATION_SANDBOX = False

# Plugins (add as needed)
PLUGIN_PATHS = ['plugins']
# Native Obsidian properties and source-relative links; legacy posts still work.
PLUGINS = ['obsidian_metadata', 'obsidian_image_links', 'donation_methods']

# Cache for faster rebuilds
CACHE_CONTENT = True
LOAD_CONTENT_CACHE = True
