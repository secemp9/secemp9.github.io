"""Prepare static donation methods and local QR images for the donate page.

DONATION_WALLETS is an ordered list/tuple of dictionaries with id, network,
network_label, asset and address. Use an empty collection until real receiving
addresses are available; incomplete records are errors, never payment options.
This validates configuration shape, not address ownership or chain compatibility.
"""

from collections.abc import Mapping
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


def _card_url(value):
    if value == "":
        return ""
    if not isinstance(value, str) or re.search(r"[\s<>\"'\\\x00-\x1f\x7f]", value):
        raise ValueError("DONATION_CARD_URL / Donation_url must be an HTTPS checkout URL")
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
        raise ValueError("DONATION_CARD_URL / Donation_url is malformed") from error
    if not valid:
        raise ValueError("DONATION_CARD_URL / Donation_url must be HTTPS without credentials")
    return value


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
    card_url = _card_url(getattr(content, "donation_url", settings.get("DONATION_CARD_URL", "")))
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
        "networks": [{"id": network, "label": label} for network, label in networks.items()],
        "wallets": wallets,
    }


def register():
    signals.content_object_init.connect(prepare_donation)
