"""Prepare static donation methods and local QR images for the donate page.

DONATION_WALLETS is an ordered list/tuple of dictionaries with id, network,
network_label, asset and address. Use an empty collection until real receiving
addresses are available; incomplete records are errors, never payment options.
DONATION_MONTHLY_PLANS contains id, amount, currency and URL for each hosted
monthly checkout. Amounts describe the matching checkout; they are never charged
or converted by this static page. Configure the customer portal for cancellation.
DONATION_MONTHLY_CUSTOM optionally describes a recurring unit price whose
quantity the donor chooses on Stripe. Limits are enforced there, not by this site.
This validates configuration shape, not address ownership, chain compatibility,
or the amount and billing interval actually configured at a checkout provider.
"""

from collections.abc import Mapping
from decimal import Decimal
import re
from urllib.parse import urlsplit

from pelican import signals
from pelican.contents import Page
import qrcode
from qrcode.image.svg import SvgPathFillImage


_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_ADDRESS = re.compile(r"[A-Za-z0-9]+(?::[A-Za-z0-9]+)?\Z")
_PLACEHOLDER = re.compile(
    r"(?:your|replace|paste|insert|example|placeholder|todo|test)[-_ ]|"
    r"(?:address|wallet|youraddress|yourwalletaddress|replace|placeholder|todo|test)\Z",
    re.IGNORECASE,
)


def _text(value, field, limit=80):
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or len(value) > limit
        or re.search(r"[<>\x00-\x1f\x7f]", value)
    ):
        raise ValueError(f"{field} must be nonempty plain text (at most {limit} characters)")
    return value


def _identifier(value, field):
    value = _text(value, field, limit=64)
    if not _ID.fullmatch(value):
        raise ValueError(f"{field} must contain lowercase letters, numbers and single hyphens")
    return value


def _https_url(value, field):
    if value == "":
        return ""
    if not isinstance(value, str) or re.search(r"[\s<>\"'\\\x00-\x1f\x7f]", value):
        raise ValueError(f"{field} must be an HTTPS URL")
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
        )
        parsed.port  # Access validates a supplied port before the URL is rendered.
    except ValueError as error:
        raise ValueError(f"{field} is malformed") from error
    if not valid:
        raise ValueError(f"{field} must be HTTPS without credentials")
    return value


def _monthly_amount(value, field):
    value = _text(value, field, limit=64)
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        raise ValueError(f"{field} must be a positive decimal string, without signs or exponents")
    amount = Decimal(value)
    if not amount.is_finite() or amount <= 0:
        raise ValueError(f"{field} must be a positive finite decimal string")
    display = format(amount, "f")
    return display.rstrip("0").rstrip(".") if "." in display else display


def _monthly_methods(settings, card_url):
    portal_url = _https_url(
        settings.get("DONATION_CUSTOMER_PORTAL_URL", ""), "DONATION_CUSTOMER_PORTAL_URL"
    )
    sponsors_url = _https_url(
        settings.get("DONATION_GITHUB_SPONSORS_URL", ""), "DONATION_GITHUB_SPONSORS_URL"
    )
    if sponsors_url:
        parsed = urlsplit(sponsors_url)
        if (
            parsed.hostname != "github.com"
            or parsed.port is not None
            or parsed.query
            or parsed.fragment
            or not re.fullmatch(r"/sponsors/[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*/?", parsed.path)
        ):
            raise ValueError("DONATION_GITHUB_SPONSORS_URL must be an https://github.com/sponsors/<account> profile URL")
    configured_plans = settings.get("DONATION_MONTHLY_PLANS", ())
    if not isinstance(configured_plans, (list, tuple)):
        raise ValueError("DONATION_MONTHLY_PLANS must be a list or tuple of monthly plan records")

    plans = []
    ids = set()
    pairs = set()
    urls = set()
    # Each declared plan must yield one unique amount/currency and checkout URL.
    for index, record in enumerate(configured_plans):
        prefix = f"DONATION_MONTHLY_PLANS[{index}]"
        if not isinstance(record, Mapping):
            raise ValueError(f"{prefix} must be a monthly plan record")
        identifier = _identifier(record.get("id"), f"{prefix}.id")
        amount = _monthly_amount(record.get("amount"), f"{prefix}.amount")
        currency = _text(record.get("currency"), f"{prefix}.currency", limit=3)
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError(f"{prefix}.currency must be a three-letter uppercase currency code")
        url = _https_url(record.get("url"), f"{prefix}.url")
        if not url:
            raise ValueError(f"{prefix}.url must be a nonempty monthly checkout URL")
        if identifier in ids:
            raise ValueError(f"{prefix}.id duplicates another monthly plan")
        pair = (amount, currency)
        if pair in pairs:
            raise ValueError(f"{prefix} duplicates a monthly amount/currency pair")
        if url in urls:
            raise ValueError(f"{prefix}.url duplicates another monthly checkout URL")
        if url == card_url:
            raise ValueError(f"{prefix}.url must differ from the one-time DONATION_CARD_URL / Donation_url")
        ids.add(identifier)
        pairs.add(pair)
        urls.add(url)
        plans.append({"id": identifier, "amount": amount, "currency": currency, "url": url})

    custom = settings.get("DONATION_MONTHLY_CUSTOM", {})
    if not isinstance(custom, Mapping):
        raise ValueError("DONATION_MONTHLY_CUSTOM must be a record, or an empty dictionary to disable it")
    if custom:
        prefix = "DONATION_MONTHLY_CUSTOM"
        url = _https_url(custom.get("url"), f"{prefix}.url")
        if not url:
            raise ValueError(f"{prefix}.url must be a nonempty monthly checkout URL")
        if url == card_url:
            raise ValueError(f"{prefix}.url must differ from the one-time checkout")
        if url in urls:
            raise ValueError(f"{prefix}.url must differ from fixed monthly checkouts")
        unit_amount = _monthly_amount(custom.get("unit_amount"), f"{prefix}.unit_amount")
        currency = _text(custom.get("currency"), f"{prefix}.currency", limit=3)
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError(f"{prefix}.currency must be a three-letter uppercase currency code")
        custom = {"url": url, "unit_amount": unit_amount, "currency": currency}
    else:
        custom = None

    if (plans or custom) and not portal_url:
        raise ValueError("DONATION_CUSTOMER_PORTAL_URL is required when monthly Stripe checkouts are configured, so supporters can manage or cancel")
    return {
        "plans": plans,
        "custom": custom,
        "portal_url": portal_url,
        "sponsors_url": sponsors_url,
        "configured": bool(plans or custom or sponsors_url),
    }


def _qr_svg(address):
    qr = qrcode.QRCode(border=4, box_size=10)
    # Only the receiving address is encoded; selecting a network stays explicit.
    qr.add_data(address, optimize=0)
    qr.make(fit=True)
    image = qr.make_image(image_factory=SvgPathFillImage)
    # All generated elements must be ID-free when several QRs share a document.
    for element in image.get_image().iter():
        element.attrib.pop("id", None)
    return image.to_string(encoding="unicode")


def prepare_donation(content):
    if not isinstance(content, Page) or content.template != "donate":
        return

    # Read the current content's settings, never state from an earlier build.
    settings = content.settings
    card_url = _https_url(
        getattr(content, "donation_url", settings.get("DONATION_CARD_URL", "")),
        "DONATION_CARD_URL / Donation_url",
    )
    provider = _text(
        getattr(content, "donation_provider", settings.get("DONATION_CARD_PROVIDER", "Stripe")),
        "DONATION_CARD_PROVIDER / Donation_provider",
    )
    configured_wallets = settings.get("DONATION_WALLETS", ())
    if not isinstance(configured_wallets, (list, tuple)):
        raise ValueError("DONATION_WALLETS must be a list or tuple of wallet records")

    wallets = []
    networks = {}
    ids = set()
    pairs = set()
    # Each declared record must yield one unique wallet and a consistent network.
    for index, record in enumerate(configured_wallets):
        prefix = f"DONATION_WALLETS[{index}]"
        if not isinstance(record, Mapping):
            raise ValueError(f"{prefix} must be a wallet record")
        identifier = _identifier(record.get("id"), f"{prefix}.id")
        network = _identifier(record.get("network"), f"{prefix}.network")
        label = _text(record.get("network_label"), f"{prefix}.network_label")
        asset = _text(record.get("asset"), f"{prefix}.asset", limit=32)
        address = _text(record.get("address"), f"{prefix}.address", limit=512)
        if not _ADDRESS.fullmatch(address) or _PLACEHOLDER.match(address):
            raise ValueError(f"{prefix}.address must be a receiving address, without placeholders or whitespace")
        if identifier in ids:
            raise ValueError(f"{prefix}.id duplicates another wallet")
        pair = (network, asset.casefold())
        if pair in pairs:
            raise ValueError(f"{prefix} duplicates a network/asset pair")
        if network in networks and networks[network] != label:
            raise ValueError(f"{prefix}.network_label conflicts with the label for {network}")
        ids.add(identifier)
        pairs.add(pair)
        networks[network] = label
        wallets.append({
            "id": identifier,
            "network": network,
            "network_label": label,
            "asset": asset,
            "address": address,
            "qr_svg": _qr_svg(address),
        })

    content.donation = {
        "card": {"url": card_url, "provider": provider, "configured": bool(card_url)},
        "monthly": _monthly_methods(settings, card_url),
        "networks": [{"id": network, "label": label} for network, label in networks.items()],
        "wallets": wallets,
    }


def register():
    signals.content_object_init.connect(prepare_donation)
