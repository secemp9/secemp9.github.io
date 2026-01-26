#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is only used if you use `make publish` or
# explicitly specify it as your config file.

import os
import sys
sys.path.append(os.curdir)
from pelicanconf import *

# Production URL
SITEURL = 'https://secemp9.github.io'
RELATIVE_URLS = False

# Feed generation (enabled for production)
FEED_ALL_ATOM = 'feeds/all.atom.xml'
CATEGORY_FEED_ATOM = 'feeds/{slug}.atom.xml'

# Delete output directory before regenerating
DELETE_OUTPUT_DIRECTORY = True

# Disable caching for production builds
CACHE_CONTENT = False
LOAD_CONTENT_CACHE = False
