"""Verify live destinations and their rendered separation from Stripe's sandbox."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import shutil
import tempfile
import unittest
from urllib.parse import urlsplit

from pelican import Pelican

import test_donation_methods as donation_tests
from test_sandbox import load_settings


ROOT = Path(__file__).resolve().parents[1]
ONCE = 'https://buy.stripe.com/6oU00j3Bk7Y54bxdHkd3i00'
PLANS = (
    ('5', 'https://buy.stripe.com/4gM14n2xg3HP9vRfPsd3i03'),
    ('10', 'https://buy.stripe.com/28E8wP1tc1zH37tcDgd3i04'),
    ('25', 'https://buy.stripe.com/8x214ndbU5PXdM79r4d3i01'),
)
CUSTOM = 'https://buy.stripe.com/4gM7sLgo6dip5fBdHkd3i02'
PORTAL = 'https://billing.stripe.com/p/login/6oU00j3Bk7Y54bxdHkd3i00'


class LiveDonationTests(unittest.TestCase):
    def test_production_uses_verified_live_links_with_distinct_checkouts(self):
        production = load_settings('publishconf.py')
        sandbox = load_settings('sandboxconf.py')
        self.assertFalse(production['DONATION_SANDBOX'])
        self.assertEqual(production['DONATION_CARD_URL'], ONCE)
        self.assertEqual(tuple((p['amount'], p['url']) for p in production['DONATION_MONTHLY_PLANS']), PLANS)
        self.assertEqual({p['currency'] for p in production['DONATION_MONTHLY_PLANS']}, {'EUR'})
        self.assertEqual(production['DONATION_MONTHLY_CUSTOM'],
                         {'url': CUSTOM, 'unit_amount': '1', 'currency': 'EUR'})
        self.assertEqual(production['DONATION_CUSTOMER_PORTAL_URL'], PORTAL)
        checkouts = [ONCE, CUSTOM, *(url for _, url in PLANS)]
        self.assertEqual(len(set(checkouts)), 5)
        # All five verified checkout links are live Stripe URLs and absent from sandbox settings.
        for url in checkouts:
            parsed = urlsplit(url)
            self.assertEqual((parsed.scheme, parsed.hostname), ('https', 'buy.stripe.com'))
            self.assertFalse(parsed.path.startswith('/test_'))
            self.assertNotIn(url, repr(sandbox))
        self.assertNotIn(PORTAL, repr(sandbox))

    def test_actual_live_render_keeps_links_static_and_the_page_unlisted(self):
        with tempfile.TemporaryDirectory(prefix='secemp-live-') as temporary:
            directory = Path(temporary)
            pages = directory / 'content/pages'
            pages.mkdir(parents=True)
            shutil.copyfile(ROOT / 'content/pages/donate.md', pages / 'donate.md')
            settings = load_settings(
                'publishconf.py', PATH=str(directory / 'content'),
                OUTPUT_PATH=str(directory / 'output'), CACHE_PATH=str(directory / 'cache'),
                STATIC_PATHS=[], EXTRA_PATH_METADATA={},
            )
            with redirect_stdout(StringIO()):
                Pelican(settings).run()
            html = (directory / 'output/donate/index.html').read_text(encoding='utf-8')
            document = donation_tests.DonationDocument(html)
            plans = document.with_attribute('data-monthly-plan')
            self.assertEqual([node['attrs']['href'] for node in plans], [url for _, url in PLANS])
            # Each known amount remains attached to its own immutable monthly checkout.
            for node, (amount, _) in zip(plans, PLANS):
                self.assertIn(f'{amount} EUR per month', node['attrs']['aria-label'])
            self.assertIn(f'href="{ONCE}"', html)
            self.assertEqual(document.with_attribute('data-monthly-custom')[0]['attrs']['href'], CUSTOM)
            portal = document.with_attribute('data-manage-monthly')[0]
            self.assertEqual(portal['attrs']['href'], PORTAL)
            self.assertFalse(document.is_hidden(portal))
            self.assertIn('Each unit is 1 EUR per month.', html)
            self.assertIn('charged each month until you cancel', html)
            self.assertIn('name="robots" content="noindex, nofollow, noimageindex"', html)
            self.assertNotIn('/donate/', (directory / 'output/index.html').read_text(encoding='utf-8'))
            # Live HTML must not leak test checkouts, a sandbox notice, secrets, or a charge form.
            for forbidden in ('buy.stripe.com/test_', 'billing.stripe.com/p/login/test_',
                              'data-donation-sandbox', '999999', 'sk_live_', 'sk_test_', '<form'):
                self.assertNotIn(forbidden, html)


if __name__ == '__main__':
    unittest.main()
