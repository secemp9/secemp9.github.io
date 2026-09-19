"""Pin owner-supplied destinations, network labels and static QR payloads.

These checks verify encoding and preservation, not ownership or fund receipt.
"""

from contextlib import redirect_stdout
from functools import reduce
from io import StringIO
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from pelican import Pelican
import qrcode

import test_donation_methods as donation_tests
from test_sandbox import load_settings


ROOT = Path(__file__).resolve().parents[1]
EVM = '0x77334ce2f9bebdcb35d294eb93fab0175a844186'
SOLANA = '8n5UNHa2rGoqw4tMLQcgBeywEC4HBDeYK6eijHBDRCDM'
BITCOIN = 'bc1qm3zuxj2ty99awg3fka52ryythjp5m59ks7n0g6'
SUI = '0xcf4d0ca54490e10bb35d4f909b8e303fa75fa350f7d0fd8ad0cad73de194a9da'
EXPECTED = (
    ('solana', 'Solana', 'SOL', SOLANA),
    ('ethereum', 'Ethereum', 'ETH', EVM),
    ('bitcoin', 'Bitcoin', 'BTC', BITCOIN),
    ('base', 'Base', 'ETH', EVM),
    ('sui', 'Sui', 'SUI', SUI),
    ('polygon', 'Polygon', 'POL', EVM),
    ('hyperevm', 'HyperEVM', 'HYPE', EVM),
    ('robinhood', 'Robinhood Chain', 'ETH', EVM),
)


def bech32_polymod(address):
    """Compute the BIP-173/350 checksum; mainnet v0 expects remainder 1.

    Specification: https://bips.dev/173/#checksum
    """
    hrp, data = address.rsplit('1', 1)
    alphabet = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
    values = [ord(char) >> 5 for char in hrp] + [0]
    values += [ord(char) & 31 for char in hrp]
    values += [alphabet.index(char) for char in data]
    generators = (0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3)
    remainder = 1
    # BIP-173 predicts remainder 1 for the complete Native SegWit address.
    for value in values:
        high = remainder >> 25
        remainder = ((remainder & 0x1ffffff) << 5) ^ value
        # Each of the five high bits selects its corresponding BCH generator.
        for bit, generator in enumerate(generators):
            if high & (1 << bit):
                remainder ^= generator
    return remainder


class ReceivingAddressTests(unittest.TestCase):
    def test_settings_preserve_exact_owner_addresses_and_native_asset_networks(self):
        wallets = load_settings('publishconf.py')['DONATION_WALLETS']
        self.assertEqual(
            tuple((w['network'], w['network_label'], w['asset'], w['address']) for w in wallets),
            EXPECTED,
        )
        self.assertEqual(len({w['id'] for w in wallets}), len(EXPECTED))
        self.assertEqual(load_settings('sandboxconf.py')['DONATION_WALLETS'], ())

    def test_address_encodings_and_bitcoin_checksum(self):
        self.assertRegex(EVM, r'^0x[0-9a-f]{40}$')
        self.assertRegex(SUI, r'^0x[0-9a-f]{64}$')
        alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        decoded = reduce(lambda value, char: value * 58 + alphabet.index(char), SOLANA, 0)
        leading_zeroes = len(SOLANA) - len(SOLANA.lstrip('1'))
        self.assertEqual(leading_zeroes + (decoded.bit_length() + 7) // 8, 32)
        # v0 + 32 base32 symbols encodes exactly a 20-byte witness program.
        self.assertTrue(BITCOIN.startswith('bc1q'))
        self.assertEqual(len(BITCOIN), 42)
        self.assertEqual(bech32_polymod(BITCOIN), 1)
        # Independent BIP-173 vector and a one-character corruption guard the helper.
        self.assertEqual(bech32_polymod('bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4'), 1)
        self.assertNotEqual(bech32_polymod(BITCOIN[:-1] + 'q'), 1)

    def test_real_production_render_preserves_addresses_qrs_and_nojs_fallback(self):
        with tempfile.TemporaryDirectory(prefix='secemp-receiving-') as temporary:
            directory = Path(temporary)
            pages = directory / 'content/pages'
            pages.mkdir(parents=True)
            shutil.copyfile(ROOT / 'content/pages/donate.md', pages / 'donate.md')
            settings = load_settings(
                'publishconf.py', PATH=str(directory / 'content'),
                OUTPUT_PATH=str(directory / 'output'), CACHE_PATH=str(directory / 'cache'),
                STATIC_PATHS=[], EXTRA_PATH_METADATA={},
            )
            original_add_data = qrcode.QRCode.add_data
            with mock.patch.object(qrcode.QRCode, 'add_data', autospec=True,
                                   side_effect=original_add_data) as add_data:
                with redirect_stdout(StringIO()):
                    Pelican(settings).run()
            self.assertEqual([call.args[1] for call in add_data.call_args_list],
                             [record[3] for record in EXPECTED])
            html = (directory / 'output/donate/index.html').read_text(encoding='utf-8')
            document = donation_tests.DonationDocument(html)
            addresses = document.with_attribute('data-wallet-address')
            self.assertEqual([node['attrs']['value'] for node in addresses],
                             [record[3] for record in EXPECTED])
            self.assertEqual(len(document.with_attribute('data-wallet-panel')), 8)
            self.assertEqual(len(document.with_attribute('data-copy-address')), 8)
            self.assertFalse(any(document.is_hidden(node) for node in addresses))
            # Each mainnet asset must have its own explicit network warning and QR label.
            for _, label, asset, _ in EXPECTED:
                self.assertIn(f'Send only <strong>{asset}</strong> on <strong>{label}</strong>.', html)
                self.assertIn(f'aria-label="Receiving address for {asset} on {label}"', html)
            self.assertIn('data-default-method="card"', html)
            self.assertIn('name="robots" content="noindex, nofollow, noimageindex"', html)
            self.assertNotIn('data-donation-sandbox', html)
            self.assertNotIn('https://buy.stripe.com/test_', html)
            self.assertNotIn('<form', html)


if __name__ == '__main__':
    unittest.main()
