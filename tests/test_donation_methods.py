"""Check payment configuration, QR payloads and real donation-page publication."""

from contextlib import redirect_stdout
from copy import deepcopy
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from pelican import Pelican, signals
from pelican.contents import Article, Page
from pelican.settings import DEFAULT_CONFIG, read_settings
import qrcode

from plugins.donation_methods import prepare_donation


ROOT = Path(__file__).resolve().parents[1]
# Synthetic fixtures exist only in tests, separate from the owner's site settings.
EVM_ADDRESS = "0x1234567890123456789012345678901234567890"
SOL_ADDRESS = "11111111111111111111111111111111"
WALLETS = (
    {"id": "base-usdc", "network": "base", "network_label": "Base", "asset": "USDC", "address": EVM_ADDRESS},
    {"id": "base-eth", "network": "base", "network_label": "Base", "asset": "ETH", "address": EVM_ADDRESS},
    {"id": "solana-sol", "network": "solana", "network_label": "Solana", "asset": "SOL", "address": SOL_ADDRESS},
)
MONTHLY_PLANS = (
    {"id": "eur-5", "amount": "5", "currency": "EUR", "url": "https://checkout.example/monthly-5"},
    {"id": "eur-10", "amount": "10", "currency": "EUR", "url": "https://checkout.example/monthly-10"},
)
PORTAL_URL = "https://billing.example/supporters"
SPONSORS_URL = "https://github.com/sponsors/fixture-account"
CUSTOM_MONTHLY = {"url": "https://checkout.example/monthly-custom", "unit_amount": "1", "currency": "EUR"}


class DonationDocument(HTMLParser):
    """Inspect rendered links and hidden ancestors before JavaScript executes."""

    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, html):
        super().__init__()
        self.nodes = []
        self._stack = []
        self._anchor = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "ancestors": tuple(self._stack), "text": ""}
        self.nodes.append(node)
        if tag not in self.VOID_TAGS:
            self._stack.append(node)
        if tag == "a":
            self._anchor = node

    def handle_endtag(self, tag):
        # A closing tag ends its matching open element and any unclosed children.
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index]["tag"] == tag:
                del self._stack[index:]
                break
        if tag == "a":
            self._anchor = None

    def handle_data(self, data):
        if self._anchor is not None:
            self._anchor["text"] += data

    def with_attribute(self, name):
        return [node for node in self.nodes if name in node["attrs"]]

    @staticmethod
    def is_hidden(node):
        return any("hidden" in ancestor["attrs"] for ancestor in (*node["ancestors"], node))


class DonationConfigurationTests(unittest.TestCase):
    def page(self, settings=None, metadata=None, content_class=Page):
        config = deepcopy(DEFAULT_CONFIG)
        config.update(settings or {})
        values = {"title": "Support", "template": "donate", "status": "hidden"}
        values.update(metadata or {})
        # Isolate unit calls from receivers retained by earlier integration builds.
        with signals.content_object_init.muted():
            page = content_class("A donation page.", metadata=values, settings=config)
        prepare_donation(page)
        return page

    def test_empty_configuration_exposes_no_payment_destination(self):
        page = self.page()
        self.assertEqual(page.donation, {
            "card": {"url": "", "provider": "Stripe", "configured": False},
            "monthly": {"plans": [], "custom": None, "portal_url": "", "sponsors_url": "", "configured": False},
            "networks": [], "wallets": [],
        })
        self.assertFalse(hasattr(self.page(metadata={"template": "page"}), "donation"))
        self.assertFalse(hasattr(self.page(content_class=Article), "donation"))

    def test_metadata_overrides_global_card_settings_including_disabling(self):
        settings = {"DONATION_CARD_URL": "https://checkout.example/global", "DONATION_CARD_PROVIDER": "Global provider"}
        self.assertEqual(self.page(settings).donation["card"], {
            "url": "https://checkout.example/global", "provider": "Global provider", "configured": True,
        })
        self.assertEqual(self.page(settings, {"donation_url": "https://checkout.example/page", "donation_provider": "Page provider"}).donation["card"], {
            "url": "https://checkout.example/page", "provider": "Page provider", "configured": True,
        })
        self.assertFalse(self.page(settings, {"donation_url": ""}).donation["card"]["configured"])

    def test_monthly_plans_preserve_order_and_exact_decimal_amounts(self):
        plans = (
            dict(MONTHLY_PLANS[0], amount="0005.5000"),
            dict(MONTHLY_PLANS[1], amount="12345678901234567890.1234567890123456789", currency="USD"),
            {"id": "jpy-50", "amount": "50", "currency": "JPY", "url": "https://checkout.example/monthly-50"},
        )
        before = deepcopy(plans)
        monthly = self.page({
            "DONATION_MONTHLY_PLANS": plans,
            "DONATION_CUSTOMER_PORTAL_URL": PORTAL_URL,
            "DONATION_GITHUB_SPONSORS_URL": SPONSORS_URL,
        }).donation["monthly"]
        self.assertEqual(monthly, {
            "plans": [dict(plans[0], amount="5.5"), plans[1], plans[2]],
            "custom": None,
            "portal_url": PORTAL_URL, "sponsors_url": SPONSORS_URL, "configured": True,
        })
        self.assertEqual(plans, before)

    def test_sponsors_only_needs_no_stripe_portal_and_portal_alone_remains_available(self):
        self.assertEqual(self.page({"DONATION_GITHUB_SPONSORS_URL": SPONSORS_URL}).donation["monthly"], {
            "plans": [], "custom": None, "portal_url": "", "sponsors_url": SPONSORS_URL, "configured": True,
        })
        self.assertEqual(self.page({"DONATION_CUSTOMER_PORTAL_URL": PORTAL_URL}).donation["monthly"], {
            "plans": [], "custom": None, "portal_url": PORTAL_URL, "sponsors_url": "", "configured": False,
        })

    def test_custom_monthly_is_independent_of_presets_and_preserves_its_input(self):
        custom = dict(CUSTOM_MONTHLY, unit_amount="001.000")
        before = deepcopy(custom)
        monthly = self.page({"DONATION_MONTHLY_CUSTOM": custom, "DONATION_CUSTOMER_PORTAL_URL": PORTAL_URL}).donation["monthly"]
        self.assertTrue(monthly["configured"])
        self.assertEqual(monthly["plans"], [])
        self.assertEqual(monthly["custom"], CUSTOM_MONTHLY)
        self.assertEqual(custom, before)

    def test_custom_monthly_requires_a_portal_and_a_distinct_destination(self):
        with self.assertRaisesRegex(ValueError, "DONATION_CUSTOMER_PORTAL_URL is required"):
            self.page({"DONATION_MONTHLY_CUSTOM": CUSTOM_MONTHLY})
        settings = {"DONATION_MONTHLY_CUSTOM": CUSTOM_MONTHLY, "DONATION_CUSTOMER_PORTAL_URL": PORTAL_URL}
        with self.assertRaisesRegex(ValueError, "one-time"):
            self.page(dict(settings, DONATION_CARD_URL=CUSTOM_MONTHLY["url"]))
        with self.assertRaisesRegex(ValueError, "one-time"):
            self.page(settings, {"donation_url": CUSTOM_MONTHLY["url"]})
        with self.assertRaisesRegex(ValueError, "fixed monthly"):
            self.page(dict(settings, DONATION_MONTHLY_PLANS=MONTHLY_PLANS,
                           DONATION_MONTHLY_CUSTOM=dict(CUSTOM_MONTHLY, url=MONTHLY_PLANS[0]["url"])))

    def test_invalid_custom_monthly_records_fail_before_rendering(self):
        invalid = (
            (None, "record"), ([], "record"), (False, "record"),
            ({"url": ""}, r"\.url"),
            (dict(CUSTOM_MONTHLY, url="http://checkout.example/custom"), r"\.url"),
            (dict(CUSTOM_MONTHLY, url="https://user:secret@checkout.example/custom"), r"\.url"),
            (dict(CUSTOM_MONTHLY, currency="eur"), r"\.currency"),
            (dict(CUSTOM_MONTHLY, currency="EU1"), r"\.currency"),
            (dict(CUSTOM_MONTHLY, unit_amount="0"), r"\.unit_amount"),
            (dict(CUSTOM_MONTHLY, unit_amount=1), r"\.unit_amount"),
            (dict(CUSTOM_MONTHLY, unit_amount="1e3"), r"\.unit_amount"),
        )
        # Each case violates the record, safe URL, currency, or positive unit-price contract.
        for record, error in invalid:
            with self.subTest(record=record), self.assertRaisesRegex(ValueError, error):
                self.page({"DONATION_MONTHLY_CUSTOM": record, "DONATION_CUSTOMER_PORTAL_URL": PORTAL_URL})

    def test_monthly_plans_require_a_management_portal(self):
        with self.assertRaisesRegex(ValueError, "DONATION_CUSTOMER_PORTAL_URL is required"):
            self.page({"DONATION_MONTHLY_PLANS": MONTHLY_PLANS})

    def test_monthly_plan_cannot_reuse_effective_one_time_destination(self):
        settings = {"DONATION_MONTHLY_PLANS": MONTHLY_PLANS, "DONATION_CUSTOMER_PORTAL_URL": PORTAL_URL}
        with self.assertRaisesRegex(ValueError, "one-time"):
            self.page(dict(settings, DONATION_CARD_URL=MONTHLY_PLANS[0]["url"]))
        with self.assertRaisesRegex(ValueError, "one-time"):
            self.page(dict(settings, DONATION_CARD_URL="https://checkout.example/global"), {"donation_url": MONTHLY_PLANS[0]["url"]})
        # Disabling the effective one-time URL removes the duplicate destination.
        self.assertTrue(self.page(dict(settings, DONATION_CARD_URL=MONTHLY_PLANS[0]["url"]), {"donation_url": ""}).donation["monthly"]["configured"])

    def test_invalid_monthly_records_are_rejected_before_rendering(self):
        invalid = (
            (None, "list or tuple"),
            ({}, "list or tuple"),
            ([None], "record"),
            ([{}], r"\.id"),
            ([dict(MONTHLY_PLANS[0], id="eur 5")], r"\.id"),
            ([dict(MONTHLY_PLANS[0], currency="eur")], r"\.currency"),
            ([dict(MONTHLY_PLANS[0], currency="EURO")], r"\.currency"),
            ([dict(MONTHLY_PLANS[0], currency="EU1")], r"\.currency"),
            ([dict(MONTHLY_PLANS[0], url="")], r"\.url"),
            ([dict(MONTHLY_PLANS[0], url="http://checkout.example/monthly")], r"\.url"),
            ([dict(MONTHLY_PLANS[0], url="https://user:password@checkout.example/monthly")], r"\.url"),
            ([MONTHLY_PLANS[0], dict(MONTHLY_PLANS[1], id="eur-5")], r"\.id duplicates"),
            ([MONTHLY_PLANS[0], dict(MONTHLY_PLANS[1], amount="05.00")], "amount/currency"),
            ([MONTHLY_PLANS[0], dict(MONTHLY_PLANS[1], url=MONTHLY_PLANS[0]["url"])], r"\.url duplicates"),
        )
        # Each fixture violates its named field or a unique-checkout invariant.
        for plans, error in invalid:
            with self.subTest(plans=plans), self.assertRaisesRegex(ValueError, error):
                self.page({"DONATION_MONTHLY_PLANS": plans, "DONATION_CUSTOMER_PORTAL_URL": PORTAL_URL})

    def test_monthly_amount_requires_positive_plain_decimal_string(self):
        # These values violate the exact positive decimal-string contract.
        for amount in (None, 5, 5.5, True, "", " ", " 5", "0", "0.00", "-5", "+5", "1e3", "NaN", "Infinity", ".5", "5.", "1,000", "٥"):
            with self.subTest(amount=amount), self.assertRaisesRegex(ValueError, r"DONATION_MONTHLY_PLANS\[0\]\.amount"):
                self.page({
                    "DONATION_MONTHLY_PLANS": [dict(MONTHLY_PLANS[0], amount=amount)],
                    "DONATION_CUSTOMER_PORTAL_URL": PORTAL_URL,
                })

    def test_monthly_service_urls_reject_unsafe_and_unofficial_destinations(self):
        invalid = (
            ("DONATION_CUSTOMER_PORTAL_URL", None),
            ("DONATION_CUSTOMER_PORTAL_URL", "http://billing.example"),
            ("DONATION_CUSTOMER_PORTAL_URL", "https://billing.example:bad"),
            ("DONATION_CUSTOMER_PORTAL_URL", "https://user:secret@billing.example"),
            ("DONATION_GITHUB_SPONSORS_URL", "http://github.com/sponsors/fixture-account"),
            ("DONATION_GITHUB_SPONSORS_URL", "https://github.com.evil.example/sponsors/fixture-account"),
            ("DONATION_GITHUB_SPONSORS_URL", "https://github.com/fixture-account"),
            ("DONATION_GITHUB_SPONSORS_URL", "https://github.com/sponsors/fixture-account/other"),
            ("DONATION_GITHUB_SPONSORS_URL", "https://github.com/sponsors/fixture-account?other=1"),
            ("DONATION_GITHUB_SPONSORS_URL", "https://github.com/sponsors/fixture-account#other"),
            ("DONATION_GITHUB_SPONSORS_URL", "https://github.com:443/sponsors/fixture-account"),
        )
        # Each service URL must fail its own setting's HTTPS or official-profile rule.
        for field, value in invalid:
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                self.page({field: value})

    def test_wallets_group_by_network_and_encode_exact_raw_address(self):
        original_add_data = qrcode.QRCode.add_data
        with mock.patch.object(qrcode.QRCode, "add_data", autospec=True, side_effect=original_add_data) as add_data:
            donation = self.page({"DONATION_WALLETS": WALLETS}).donation
        self.assertEqual(donation["networks"], [{"id": "base", "label": "Base"}, {"id": "solana", "label": "Solana"}])
        self.assertEqual([call.args[1] for call in add_data.call_args_list], [EVM_ADDRESS, EVM_ADDRESS, SOL_ADDRESS])
        # Every configured wallet must preserve its fields and produce an opaque,
        # ID-free SVG with the library's explicit four-module quiet margin.
        for source, wallet, call in zip(WALLETS, donation["wallets"], add_data.call_args_list):
            self.assertEqual({key: wallet[key] for key in source}, source)
            self.assertEqual(call.args[0].border, 4)
            svg = ET.fromstring(wallet["qr_svg"])
            self.assertEqual(svg.tag, "{http://www.w3.org/2000/svg}svg")
            self.assertTrue(svg.findall("{http://www.w3.org/2000/svg}path"))
            self.assertEqual(svg.find("{http://www.w3.org/2000/svg}rect").get("fill"), "white")
            self.assertFalse(any(element.get("id") for element in svg.iter()))

    def test_invalid_card_urls_are_rejected(self):
        # Each declared invalid input breaks a required URL invariant.
        for url in (None, "http://checkout.example", "javascript:alert(1)", "//checkout.example", "https://", "https://user:password@checkout.example", "https://checkout.example/ bad", "https://checkout.example:invalid", 'https://checkout.example/"bad'):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "Donation_url"):
                self.page({"DONATION_CARD_URL": url})

    def test_invalid_wallet_records_are_rejected(self):
        invalid = (
            (None, "list or tuple"),
            ({"id": "base"}, "list or tuple"),
            ([None], "record"),
            ([{}], r"\.id"),
            ([dict(WALLETS[0], id="base usdc")], r"\.id"),
            ([dict(WALLETS[0], address="")], r"\.address"),
            ([dict(WALLETS[0], address=" address ")], r"\.address"),
            ([dict(WALLETS[0], address="<script>alert(1)</script>")], r"\.address"),
            ([dict(WALLETS[0], address="YOUR_ADDRESS")], r"\.address"),
            ([dict(WALLETS[0], address="placeholder")], r"\.address"),
            ([WALLETS[0], WALLETS[0]], "duplicates"),
            ([WALLETS[0], dict(WALLETS[0], id="other-id", asset="usdc")], "network/asset"),
            ([WALLETS[0], dict(WALLETS[1], network_label="Different Base")], "conflicts"),
        )
        # Each fixture must fail at its named invalid field, before rendering.
        for wallets, error in invalid:
            with self.subTest(wallets=wallets), self.assertRaisesRegex(ValueError, error):
                self.page({"DONATION_WALLETS": wallets})


class DonationIntegrationTests(unittest.TestCase):
    def assert_monthly_no_javascript_fallback(self, html, configured, expected_plans=MONTHLY_PLANS):
        document = DonationDocument(html)
        panels = document.with_attribute("data-frequency-panel")
        self.assertEqual([panel["attrs"]["data-frequency-panel"] for panel in panels], ["once", "monthly"])
        self.assertFalse(any(document.is_hidden(panel) for panel in panels))
        self.assertTrue(document.is_hidden(document.with_attribute("data-frequency-toggle")[0]))
        if not configured:
            self.assertFalse(document.with_attribute("data-monthly-plan"))
            self.assertFalse(document.with_attribute("data-monthly-custom"))
            self.assertFalse(document.with_attribute("data-monthly-sponsors"))
            self.assertFalse(document.with_attribute("data-manage-monthly"))
            self.assertIn("Monthly card payments are not available yet.", html)
            return

        plans = document.with_attribute("data-monthly-plan")
        self.assertEqual(len(plans), len(expected_plans))
        # Each rendered amount must keep its own checkout and explicit monthly label.
        for link, plan in zip(plans, expected_plans):
            self.assertEqual(link["tag"], "a")
            self.assertEqual(link["attrs"]["data-monthly-plan"], plan["id"])
            self.assertEqual(link["attrs"]["href"], plan["url"])
            self.assertIn(f'{plan["amount"]} {plan["currency"]}', " ".join(link["text"].split()))
            self.assertIn("per month", link["text"])
            self.assertIn(f'{plan["amount"]} {plan["currency"]} per month', link["attrs"]["aria-label"])
            self.assertFalse(document.is_hidden(link))
        custom = document.with_attribute("data-monthly-custom")
        self.assertEqual(len(custom), 1)
        self.assertEqual(custom[0]["attrs"]["href"], CUSTOM_MONTHLY["url"])
        self.assertIn("Other monthly amount" if expected_plans else "Choose monthly amount", custom[0]["text"])
        self.assertIn("monthly-custom-help", custom[0]["attrs"]["aria-describedby"])
        self.assertFalse(document.is_hidden(custom[0]))
        self.assertIn("Each unit is 1 EUR per month.", html)
        self.assertNotIn("999999", html)
        self.assertNotIn("Monthly card payments are not available yet.", html)
        portal = document.with_attribute("data-manage-monthly")
        self.assertEqual(len(portal), 1)
        self.assertEqual(portal[0]["attrs"]["href"], PORTAL_URL)
        self.assertFalse(document.is_hidden(portal[0]))
        self.assertFalse(any("data-frequency-panel" in ancestor["attrs"] for ancestor in portal[0]["ancestors"]))
        sponsors = document.with_attribute("data-monthly-sponsors")
        self.assertEqual(len(sponsors), 1)
        self.assertEqual(sponsors[0]["attrs"]["href"], SPONSORS_URL)
        self.assertFalse(document.is_hidden(sponsors[0]))

    def test_real_theme_keeps_configured_donations_unlisted_across_builds(self):
        with tempfile.TemporaryDirectory(prefix="secemp-donation-") as temporary:
            directory = Path(temporary)
            content = directory / "content"
            pages = content / "pages"
            pages.mkdir(parents=True)
            (content / "public.md").write_text("Title: Public control\nDate: 2026-01-01\nStatus: published\n\nPublic body.\n", encoding="utf-8")
            (pages / "donate.md").write_text("Title: Support fixture\nSlug: donate\nStatus: hidden\nTemplate: donate\n\nDonation body.\n", encoding="utf-8")
            overrides = {
                "PATH": str(content), "OUTPUT_PATH": str(directory / "output"),
                "CACHE_PATH": str(directory / "cache"),
                "STATIC_PATHS": [], "EXTRA_PATH_METADATA": {},
            }
            # Payment destinations must follow current settings across production
            # and two local builds with unchanged content and the real reader cache.
            for production, configured, custom_only in ((True, True, False), (False, True, False), (False, True, True), (False, False, False)):
                with self.subTest(production=production, configured=configured, custom_only=custom_only):
                    overrides.update({
                        "DONATION_CARD_URL": "https://checkout.example/support" if configured else "",
                        "DONATION_WALLETS": WALLETS if configured else (),
                        "DONATION_MONTHLY_PLANS": MONTHLY_PLANS if configured and not custom_only else (),
                        "DONATION_MONTHLY_CUSTOM": CUSTOM_MONTHLY if configured else {},
                        "DONATION_CUSTOMER_PORTAL_URL": PORTAL_URL if configured else "",
                        "DONATION_GITHUB_SPONSORS_URL": SPONSORS_URL if configured else "",
                    })
                    config = ROOT / ("publishconf.py" if production else "pelicanconf.py")
                    with mock.patch.object(sys, "path", [str(ROOT), *sys.path]):
                        settings = read_settings(str(config), override=overrides)
                        self.assertEqual(settings["CACHE_CONTENT"], not production)
                        self.assertEqual(settings["LOAD_CONTENT_CACHE"], not production)
                        with redirect_stdout(StringIO()):
                            Pelican(settings).run()
                    output = directory / "output"
                    html = (output / "donate/index.html").read_text(encoding="utf-8")
                    self.assertIn('name="robots" content="noindex, nofollow, noimageindex"', html)
                    self.assertEqual("https://checkout.example/support" in html, configured)
                    self.assertEqual(EVM_ADDRESS in html, configured)
                    self.assertEqual(SOL_ADDRESS in html, configured)
                    self.assertEqual(MONTHLY_PLANS[0]["url"] in html, configured and not custom_only)
                    self.assertEqual(MONTHLY_PLANS[1]["url"] in html, configured and not custom_only)
                    self.assertEqual(CUSTOM_MONTHLY["url"] in html, configured)
                    self.assertEqual(PORTAL_URL in html, configured)
                    self.assertEqual(SPONSORS_URL in html, configured)
                    self.assert_monthly_no_javascript_fallback(html, configured, () if custom_only else MONTHLY_PLANS)
                    # A hidden donation page must not appear in public navigation,
                    # indexes or feeds, even though its direct URL renders.
                    for path in output.rglob("*"):
                        if path.suffix not in {".html", ".xml"} or path == output / "donate/index.html":
                            continue
                        public = path.read_text(encoding="utf-8")
                        self.assertNotIn("Support fixture", public, str(path))
                        self.assertNotIn("/donate/", public, str(path))


if __name__ == "__main__":
    unittest.main()
