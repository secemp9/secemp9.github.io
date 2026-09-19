"""Keep the explicit Stripe sandbox preview isolated from production."""

from contextlib import redirect_stdout
from io import StringIO
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import urlsplit

from pelican import Pelican
from pelican.settings import read_settings


ROOT = Path(__file__).resolve().parents[1]


def load_settings(filename, **overrides):
    with mock.patch.object(sys, 'path', [str(ROOT), *sys.path]):
        return read_settings(str(ROOT / filename), override=overrides)


class SandboxTests(unittest.TestCase):
    def test_console_entrypoint_loads_sandbox_without_pythonpath_help(self):
        executable = shutil.which('pelican') or str(Path(sys.executable).with_name('pelican'))
        environment = dict(os.environ)
        environment.pop('PYTHONPATH', None)
        result = subprocess.run(
            [executable, '--settings', str(ROOT / 'sandboxconf.py'), '--print-settings',
             'DONATION_SANDBOX', 'DONATION_MONTHLY_CUSTOM'],
            cwd=ROOT, env=environment, capture_output=True, text=True, check=True,
        )
        self.assertIn('True', result.stdout)
        self.assertIn('test_cNi3cvc6IbIxc21777a7C04', result.stdout)

    def test_only_explicit_sandbox_settings_enable_test_destinations(self):
        sandbox = load_settings('sandboxconf.py')
        production = load_settings('publishconf.py')
        self.assertTrue(sandbox['DONATION_SANDBOX'])
        self.assertFalse(production['DONATION_SANDBOX'])
        self.assertEqual(Path(sandbox['OUTPUT_PATH']).name, 'output-sandbox')
        self.assertNotEqual(sandbox['OUTPUT_PATH'], production['OUTPUT_PATH'])
        self.assertEqual(sandbox['DONATION_MONTHLY_CUSTOM']['unit_amount'], '1')
        self.assertEqual(sandbox['DONATION_MONTHLY_CUSTOM']['currency'], 'EUR')
        self.assertEqual([plan['amount'] for plan in sandbox['DONATION_MONTHLY_PLANS']], ['5', '10', '25'])
        self.assertEqual(sandbox['DONATION_WALLETS'], ())
        self.assertEqual(sandbox['DONATION_GITHUB_SPONSORS_URL'], '')
        links = [sandbox['DONATION_CARD_URL'], sandbox['DONATION_MONTHLY_CUSTOM']['url']]
        links.extend(plan['url'] for plan in sandbox['DONATION_MONTHLY_PLANS'])
        # Every sandbox payment destination is a distinct test checkout, absent from production settings.
        self.assertEqual(len(links), len(set(links)))
        for link in links:
            parsed = urlsplit(link)
            self.assertEqual((parsed.scheme, parsed.hostname), ('https', 'buy.stripe.com'))
            self.assertTrue(parsed.path.startswith('/test_'))
            self.assertNotIn(link, repr(production))
        self.assertTrue(urlsplit(sandbox['DONATION_CUSTOMER_PORTAL_URL']).path.startswith('/p/login/test_'))
        self.assertNotIn(sandbox['DONATION_CUSTOMER_PORTAL_URL'], repr(production))

    def test_real_sandbox_render_has_notice_and_custom_link_but_no_advertised_ceiling(self):
        with tempfile.TemporaryDirectory(prefix='secemp-sandbox-') as temporary:
            directory = Path(temporary)
            pages = directory / 'content/pages'
            pages.mkdir(parents=True)
            shutil.copyfile(ROOT / 'content/pages/donate.md', pages / 'donate.md')
            settings = load_settings(
                'sandboxconf.py', PATH=str(directory / 'content'),
                OUTPUT_PATH=str(directory / 'output'), CACHE_PATH=str(directory / 'cache'),
                STATIC_PATHS=[], EXTRA_PATH_METADATA={},
            )
            with redirect_stdout(StringIO()):
                Pelican(settings).run()
            html = (directory / 'output/donate/index.html').read_text(encoding='utf-8')
            self.assertIn('data-donation-sandbox', html)
            self.assertIn('No real money is transferred.', html)
            self.assertIn('name="robots" content="noindex, nofollow, noimageindex"', html)
            self.assertIn('Other monthly amount', html)
            self.assertIn('Each unit is 1 EUR per month.', html)
            self.assertIn(settings['DONATION_MONTHLY_CUSTOM']['url'], html)
            self.assertIn(settings['DONATION_CUSTOMER_PORTAL_URL'], html)
            self.assertNotIn('999999', html)
            self.assertNotIn('999,999', html)
            self.assertNotIn('<form', html)

    def test_preview_cli_documents_sandbox_and_rejects_conflicting_modes(self):
        help_result = subprocess.run(['bash', str(ROOT / 'serve.sh'), '--help'],
                                     cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertIn('--sandbox', help_result.stdout)
        self.assertIn('4003', help_result.stdout)
        cases = (
            (['--production', '--sandbox'], 'cannot be combined'),
            (['--sandbox', '--production'], 'cannot be combined'),
            (['--sandbox', '--port'], 'Missing value'),
            (['--sandbox', '--port', '0'], 'Port must be'),
            (['--port', '', '--sandbox'], 'Port must be'),
        )
        # Every invalid mode or explicit invalid port must fail before any server starts.
        for arguments, message in cases:
            with self.subTest(arguments=arguments):
                result = subprocess.run(['bash', str(ROOT / 'serve.sh'), *arguments],
                                        cwd=ROOT, capture_output=True, text=True,
                                        env={**os.environ, 'PORT': ''})
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, result.stderr)


if __name__ == '__main__':
    unittest.main()
