# secemp's Blog

A personal site built with Pelican and a custom Jinja theme, deployed to
[secemp.blog](https://secemp.blog) through GitHub Pages.

## How the site works

- `content/**/*.md`: articles with native Obsidian YAML properties or legacy Pelican headers.
- `content/pages/*.md`: standalone pages, such as About.
- `content/images/`: pasted images; note-relative links work from nested folders too.
- `.obsidian/plugins/secemp-blog/`: the repo-local desktop authoring commands.
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

Open the repository root as an Obsidian vault and enable its bundled **Blog**
plugin. **Ctrl/Cmd+Shift+N** creates a post; **Ctrl/Cmd+Shift+P** builds and
opens a real local preview; **Ctrl/Cmd+Shift+B** edits visibility. See the
[authoring guide](.obsidian/README.md) for setup and publishing.

Use the `status` property. New posts from both the CLI and Obsidian start
unlisted with `status: hidden`.

| Status | Deployed HTML | Listed on the site and in feeds | Search indexing |
| --- | --- | --- | --- |
| `hidden` | Yes, at its normal URL | No | `noindex` |
| `published` | Yes, at its normal URL | Yes | Allowed |
| `draft` | No, in this site's production configuration | No | Local preview only |

Legacy Pelican-header articles without `Status` keep their historical
`published` default. YAML notes without `status` default to `hidden`.
Pelican normally generates draft HTML too; this site explicitly disables that
HTML output in production. Draft source and copied static assets are still not
private.

Create an unlisted article:

```sh
.venv/bin/python new_post_pelican.py --title "A preview of my next post"
.venv/bin/python new_post_pelican.py --list
```

Its metadata looks like:

```yaml
---
title: A preview of my next post
date: 2026-09-15T14:30:00+02:00
status: hidden
slug: a-preview-of-my-next-post
tags: []
cssclasses: [blog-post]
---

The article starts here.
```

After pushing to `main` and a successful deployment, share
`https://secemp.blog/2026/09/15/a-preview-of-my-next-post/`. To make it public,
change just `status: hidden` to `status: published`, then commit and push.
The URL stays the same as long as `date` and `slug` stay the same. The next build
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

## Donation page

The donation page lives in `content/pages/donate.md` at `/donate/`. It is public,
linked from the main navigation, and uses the dedicated `donate.html` template.
Edit its Markdown to change the copy.

Configure payment methods in `pelicanconf.py`:

- `DONATION_CARD_URL`: your hosted HTTPS payment link. For Stripe, create a
  Payment Link with **Customers choose what to pay** for one-time support.
  A Stripe test link can be used while testing the unlisted page.
- `DONATION_CARD_PROVIDER`: the checkout name shown on the button, such as Stripe.
- `DONATION_WALLETS`: one receiving address record per network and asset.
- `DONATION_MONTHLY_PLANS`: fixed monthly Stripe prices with their matching
  Payment Links (see below).
- `DONATION_MONTHLY_CUSTOM`: optional adjustable-quantity monthly checkout,
  described by `url`, `unit_amount`, and `currency`.
- `DONATION_CUSTOMER_PORTAL_URL`: your Stripe customer-portal login link for
  managing and cancelling monthly payments.
- `DONATION_GITHUB_SPONSORS_URL`: optional `https://github.com/sponsors/ACCOUNT`
  profile link. Leave empty until you have a working Sponsors page.

The current production configuration contains **live** Stripe checkout and
customer-portal links, alongside real crypto receiving addresses. The normal
and production previews inherit these destinations: submitting a payment there
would move real money. Use `./serve.sh --sandbox` for payment testing; it replaces
every Stripe destination with a test link and excludes crypto addresses.

### Monthly payments

The page starts on **One-time**. **Monthly** shows only configured recurring
Stripe links and the optional GitHub Sponsors route. Crypto remains under
One-time: copying an address does not set up recurring transfers.

In Stripe, create a product with a **monthly recurring price**, then a Payment
Link for that price. Add a record like this to `DONATION_MONTHLY_PLANS`, replacing
the placeholder with the actual link:

```python
{
    'id': 'eur-5',
    'amount': '5',
    'currency': 'EUR',
    'url': 'YOUR_STRIPE_MONTHLY_PAYMENT_LINK',
}
```

Amounts are decimal strings, currencies are uppercase three-letter codes, and
each amount button goes directly to its own checkout URL. Choose the amounts
and currency you actually want to accept; these examples are not enabled by
default. Stripe's **Customers choose what to pay** Payment Links support
one-time payments only, so don't reuse that URL for a monthly option.

Activate Stripe's [customer portal](https://docs.stripe.com/no-code/customer-portal),
enable subscription cancellation there, and set `DONATION_CUSTOMER_PORTAL_URL`
to its HTTPS login link. The site requires this when monthly Stripe plans are
configured. The management link remains visible on either frequency and can
remain configured after removing every plan, for existing subscribers.

The amounts and currencies here are display labels: they must match the actual
Stripe prices. Updating these settings does not change an existing subscription
or cancel it; manage billing in Stripe. Test the chosen monthly amount, currency,
and cancellation flow using Stripe's test environment before adding live links.

### Choose another monthly amount, without a backend

Create a separate Stripe product with a **1 EUR monthly recurring price**, then
create its Payment Link with **Let customers adjust quantity** enabled. Set the
minimum to **1** and maximum to **999999** (Stripe's supported quantity ceiling),
with an initial quantity of 1. Quantity 17 then means 17 EUR per month. The amount
repeats until the donor changes or cancels the subscription. Other payment limits
can still prevent a very large charge; the quantity ceiling is not a payment guarantee.

Configure the actual hosted link, not a server endpoint:

```python
DONATION_MONTHLY_CUSTOM = {
    'url': 'YOUR_STRIPE_ADJUSTABLE_MONTHLY_PAYMENT_LINK',
    'unit_amount': '1',
    'currency': 'EUR',
}
```

The page keeps the fixed amounts and adds **Other monthly amount** with an
explanation of the unit price. With no fixed amounts it shows **Choose monthly
amount** instead. The maximum is not printed on the blog; Stripe controls its own
quantity picker and validation and may reveal the limits there. No API key,
backend, payment request, or quantity manipulation runs in the static site.

`DONATION_CUSTOMER_PORTAL_URL` is required for this option too. In the portal,
enable quantity updates for the adjustable product and review proration settings
so changes do not unexpectedly charge or credit the current billing period. Keep
the fixed-price shortcuts at quantity 1. Verify checkout, quantity changes, and
cancellation in a sandbox before configuring live links. These settings describe
the checkout; they do not verify or change its actual Stripe price or limits.

Leave `DONATION_MONTHLY_CUSTOM = {}` to disable the option. Sandbox previews can
set `DONATION_SANDBOX = True` to display an explicit test-payment notice; never
use that flag or test checkout URLs for a live donation page.

Run the configured, local-only Stripe sandbox preview with:

```sh
./serve.sh --sandbox
```

Open [localhost:4003/donate/](http://localhost:4003/donate/). This explicitly uses
`sandboxconf.py`, writes only to `output-sandbox/`, and shows a sandbox notice.
The checked-in URLs are public **test** checkout links, not credentials. This
config rejects live Stripe URLs and disables crypto and GitHub Sponsors, so a
future live configuration cannot leak into the test preview. `publishconf.py`
does not import it. `--port` or `PORT` can override the sandbox preview port.

### Crypto payments

The wallet record format is:

```python
{
    'id': 'base-usdc',
    'network': 'base',
    'network_label': 'Base',
    'asset': 'USDC',
    'address': 'YOUR_ACTUAL_RECEIVING_ADDRESS',
}
```

Replace the example address with your own verified receiving address before
adding the record to `DONATION_WALLETS`. Repeat for each asset/network you
actually accept; the selectors are generated from those records. Never put
private keys or seed phrases in the configuration. Empty settings show clear
unavailable states; the example above is not a payment destination.

The current configuration uses the owner's public Phantom receiving addresses
for SOL on Solana, ETH on Ethereum/Base/Robinhood Chain, BTC on Bitcoin,
SUI on Sui, POL on Polygon, and HYPE on HyperEVM. Only these native assets are
listed; adding a token requires its own explicit asset/network record. Bitcoin
uses the supplied Native SegWit (`bc1q`) address, not the alternate Taproot one.
The five EVM networks share an address but retain separate network labels.
These are **real mainnet receiving addresses**, including in the production
preview on port 4002. The Stripe sandbox on port 4003 excludes them entirely.
Address-format checks do not prove ownership or successful receipt; verify the
displayed destination in Phantom before sharing the donation page.

QR codes are generated locally during the Pelican build using `qrcode`, with a
white background and a four-module quiet margin. They encode only the exact
receiving address, so the donor must select the displayed network in their
wallet. QR generation and copying do not verify address ownership, network
compatibility, or payment receipt. No external QR service is called.

The frequency/method switchers and copy controls use plain JavaScript. If JavaScript is
unavailable, both one-time and monthly sections, configured links, and addresses
remain visible. If clipboard access
fails, the address can be selected and copied manually. Invalid configuration
logs a build error; the deployment's `--fatal warnings` stops that build.

Existing page metadata `Donation_url` and `Donation_provider` still override
the corresponding global card settings. Payment details are entered on the
provider's hosted checkout. This site does not collect card details, create
payment intents, verify crypto transactions, or display payment confirmations.

See [Stripe Payment Links](https://docs.stripe.com/payment-links/create) and
[Stripe testing](https://docs.stripe.com/testing) for checkout setup. Available
wallet methods depend on the provider, account settings, and donor's device.

Preview it at [localhost:4002/donate/](http://localhost:4002/donate/). Its current
`Status: published` keeps it in navigation. Changing it to `hidden` and deploying
would remove that listing and add `noindex`, while retaining `/donate/`.

## Check a build

```sh
.venv/bin/python -m unittest discover -s tests
npm ci --ignore-scripts
npm test
.venv/bin/pelican content -o output-preview -s publishconf.py --fatal warnings
```

The Pelican command uses the real production domain in generated URLs. Use
`./serve.sh --production` for a version with local links.

Node 22 and jsdom are used only for interaction tests. The deployed site stays
static HTML, CSS, and JavaScript; no Node server or npm packages are shipped.
