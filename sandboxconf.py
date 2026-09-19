"""Explicit, local-only Stripe sandbox preview; never imported by production."""

from pathlib import Path as _Path
import sys as _sys
from urllib.parse import urlsplit as _urlsplit

# Pelican's console entrypoint does not add this config's directory to sys.path.
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from publishconf import *

SITEURL = 'http://localhost:4003'
OUTPUT_PATH = 'output-sandbox/'
CACHE_PATH = 'cache/sandbox'
CACHE_CONTENT = False
LOAD_CONTENT_CACHE = False
SITENAME = 'secemp Blog (sandbox)'
DONATION_SANDBOX = True
DONATION_CARD_PROVIDER = 'Stripe (sandbox)'
DONATION_CARD_URL = 'https://buy.stripe.com/test_eVq8wPeeQ8wld658bba7C00'
DONATION_MONTHLY_PLANS = (
    {'id': 'eur-5', 'amount': '5', 'currency': 'EUR',
     'url': 'https://buy.stripe.com/test_00w9ATeeQeUJ4zz0IJa7C01'},
    {'id': 'eur-10', 'amount': '10', 'currency': 'EUR',
     'url': 'https://buy.stripe.com/test_dRmcN5eeQ6od3vv8bba7C02'},
    {'id': 'eur-25', 'amount': '25', 'currency': 'EUR',
     'url': 'https://buy.stripe.com/test_00w8wP3Ac27Xgihezza7C03'},
)
DONATION_MONTHLY_CUSTOM = {
    'url': 'https://buy.stripe.com/test_cNi3cvc6IbIxc21777a7C04',
    'unit_amount': '1',
    'currency': 'EUR',
}
DONATION_CUSTOMER_PORTAL_URL = 'https://billing.stripe.com/p/login/test_eVq8wPeeQ8wld658bba7C00'
# Never inherit live crypto destinations or sponsorship links into this preview.
DONATION_WALLETS = ()
DONATION_GITHUB_SPONSORS_URL = ''


def _is_test_link(url, host, prefix):
    parsed = _urlsplit(url)
    return (
        parsed.scheme == 'https' and parsed.hostname == host
        and parsed.port is None and parsed.username is None and parsed.password is None
        and parsed.path.startswith(prefix)
    )


# Every configured checkout must point to an explicit Stripe test link, not live money.
_checkout_urls = [DONATION_CARD_URL, DONATION_MONTHLY_CUSTOM['url']]
_checkout_urls.extend(plan['url'] for plan in DONATION_MONTHLY_PLANS)
if not all(_is_test_link(url, 'buy.stripe.com', '/test_') for url in _checkout_urls):
    raise ValueError('sandboxconf.py only accepts Stripe test checkout links')
if not _is_test_link(DONATION_CUSTOMER_PORTAL_URL, 'billing.stripe.com', '/p/login/test_'):
    raise ValueError('sandboxconf.py requires a Stripe test customer-portal link')
