# secemp's Blog

A personal site built with Pelican and a custom Jinja theme, deployed to
[secemp.blog](https://secemp.blog) through GitHub Pages.

## How the site works

- `content/*.md`: articles, written in Markdown with Pelican `Key: Value` metadata.
- `content/pages/*.md`: standalone pages, such as About.
- `content/images/`: images; the `obsidian_image_links` plugin resolves pasted Obsidian links.
- `themes/secemp/`: templates, CSS, JavaScript, and theme images.
- `pelicanconf.py`: local settings, menus, project links, and URL patterns.
- `publishconf.py`: production domain, feeds, clean builds, and draft HTML suppression.
- `.github/workflows/pelican.yml`: on a push to `main`, install requirements, run
  visibility tests, build `output/`, and deploy that generated directory to Pages.

Source files are committed; generated HTML is built by CI. A local commit alone
does not deploy anything. Pushing to `main` starts deployment.

## Run locally

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./serve.sh
```

Open [localhost:4001](http://localhost:4001). Changes rebuild automatically;
refresh the browser to see them. The script prefers `.venv/bin/pelican`, then a
Pelican installation already on `PATH`. Stop the server with Ctrl+C.

To check production settings, feeds, and absolute links on localhost:

```sh
./serve.sh --production --port 4002
```

Open [localhost:4002](http://localhost:4002). This uses `publishconf.py`, overrides
`SITEURL` to the local address, and writes to `output-preview/` so both servers
can run together. `PORT=4003 ./serve.sh` also works. The production preview
matches the Pages build settings; the deployed URL is still the final check for
hosting behavior.

## Unlisted first, public when ready

Use Pelican's native `Status` metadata. New posts from the CLI and Obsidian
helpers start with `Status: hidden`.

| Status | Deployed HTML | Listed on the site and in feeds | Search indexing |
| --- | --- | --- | --- |
| `hidden` | Yes, at its normal URL | No | `noindex` |
| `published` | Yes, at its normal URL | Yes | Allowed |
| `draft` | No, in this site's production configuration | No | Local preview only |

Existing articles without `Status` keep Pelican's default of `published`.
Pelican normally generates draft HTML too; this site explicitly disables that
HTML output in production. Draft source and copied static assets are still not
private.

Create an unlisted article:

```sh
python3 new_post_pelican.py --title "A preview of my next post"
python3 new_post_pelican.py --list
```

Its metadata looks like:

```text
Title: A preview of my next post
Date: 2026-09-15 14:30
Status: hidden
Slug: a-preview-of-my-next-post

The article starts here.
```

After pushing to `main` and a successful deployment, share
`https://secemp.blog/2026/09/15/a-preview-of-my-next-post/`. To make it public,
change just `Status: hidden` to `Status: published`, then commit and push.
The URL stays the same as long as `Date` and `Slug` stay the same. The next build
adds it to listings and feeds and removes `noindex`. Reversing the status removes
it from those listings again.

The included `content/pages/preview.md` is an unlisted design sample. Open
[the local preview page](http://localhost:4001/preview/) or
[the production settings preview](http://localhost:4002/preview/) to try it.
After deployment it is available at `https://secemp.blog/preview/`.

For another standalone unlisted page, create `content/pages/my-preview.md` with:

```text
Title: Preview
Slug: my-preview
Status: hidden

Page content here.
```

Its URL is `/my-preview/`; changing its status to `published` makes it public and
eligible for the page menu. Native drafts are available in the development build
under `/drafts/<slug>.html` for articles and `/drafts/pages/<slug>.html` for pages.

You can explicitly create public or local draft posts with `--status published`
or `--status draft`. Imports via `--from-file` retain any explicit existing
status; files without one become hidden. Pass `--status` to override an import.
See the [Obsidian setup](.obsidian/README.md) for editor integration.

### What “unlisted” means

This is link sharing, not access control. Anyone with the URL can open or
forward it. A public GitHub repository exposes committed Markdown, assets, and
history independently of the generated site's settings. Page metadata does not
protect image or download URLs. Do not put secrets in these files; confidential
content needs authentication and private source storage.

Hidden pages tell search engines `noindex`. Google must be allowed to crawl the
page to read that instruction, so do not add `robots.txt` disallow rules for
these URLs. Google removes an already indexed page after recrawling it; this is
not instant. Other crawlers may ignore the instruction. The setup cannot make
public content impossible to discover.

References: [Pelican hidden posts and drafts](https://docs.getpelican.com/en/latest/content.html#hidden-posts),
[Google's noindex guidance](https://developers.google.com/search/docs/crawling-indexing/block-indexing).

## Check a build

```sh
.venv/bin/python -m unittest discover -s tests
.venv/bin/pelican content -o output-preview -s publishconf.py --fatal warnings
```

The second command uses the real production domain in generated URLs. Use
`./serve.sh --production` for a version with local links.
