"""Dataset and network validation helpers for NetSage-AI.

These helpers are deliberately dependency-light (stdlib only) so the
deterministic rule checker never depends on pandas at runtime.
"""
from __future__ import annotations

import ipaddress
import re
from typing import Optional

from utils.csv_loader import CASE_FIELDS, Case

# Canonical category list and valid severities.
CATEGORIES = [
    "VLAN", "Default Gateway", "DHCP", "DNS",
    "Routing", "ACL", "NAT", "Wireless",
]
SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
OSI_LAYERS = ["Layer 1", "Layer 2", "Layer 3", "Layer 4", "Layer 7"]

_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_MASK_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


# --------------------------------------------------------------------------- #
# IP / subnet primitives
# --------------------------------------------------------------------------- #
def is_valid_ipv4(addr: str) -> bool:
    if not addr or not _IPV4_RE.match(addr):
        return False
    try:
        ipaddress.ip_address(addr)
        return True
    except ValueError:
        return False


def is_valid_subnet(cidr: str) -> bool:
    """Validate an IPv4Network string (e.g. '192.168.10.0/24')."""
    try:
        ipaddress.ip_network(cidr, strict=True)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_mask(mask: str) -> bool:
    """Return True if the mask is a valid contiguous IPv4 subnet mask."""
    if not _MASK_RE.match(mask):
        return False
    try:
        ipaddress.IPv4Address(mask)  # each octet 0-255
    except ValueError:
        return False
    # A valid contiguous mask lets ipaddress build a network; non-contiguous
    # masks (e.g. 255.255.0.255) raise ValueError.
    try:
        ipaddress.IPv4Network(f"0.0.0.0/{mask}", strict=False)
        return True
    except ValueError:
        return False


def ip_in_subnet(ip: str, network: str) -> bool:
    """True if ip is a usable address within network (cidr)."""
    try:
        net = ipaddress.ip_network(network, strict=False)
        return ipaddress.ip_address(ip) in net
    except (ValueError, TypeError):
        return False


def normalize_ip(ip: str) -> Optional[str]:
    if is_valid_ipv4(ip):
        return ip
    return None


# --------------------------------------------------------------------------- #
# Dataset validation
# --------------------------------------------------------------------------- #
def validate_dataset(cases: list[Case]) -> dict:
    """Validate the cases list.

    Returns a dict: {ok, count, errors: [...], warnings: [...],
                    category_counts, severity_counts}.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if len(cases) < 30:
        errors.append(f"Dataset has only {len(cases)} cases; at least 30 required.")

    seen_ids = set()
    cat_counts = {c: 0 for c in CATEGORIES}
    sev_counts = {s: 0 for s in SEVERITIES}

    for i, c in enumerate(cases):
        prefix = f"case {c.case_id or i}: "
        # required fields non-empty
        missing = [f for f in CASE_FIELDS if not str(getattr(c, f, "")).strip()]
        if missing:
            errors.append(prefix + "empty required field(s): " + ", ".join(missing))
        if c.case_id in seen_ids:
            errors.append(prefix + "duplicate case_id")
        seen_ids.add(c.case_id)
        if c.category not in CATEGORIES:
            errors.append(prefix + f"unknown category '{c.category}'")
        else:
            cat_counts[c.category] += 1
        if c.severity not in SEVERITIES:
            errors.append(prefix + f"unknown severity '{c.severity}'")
        else:
            sev_counts[c.severity] += 1
        if not c.show_output.strip():
            errors.append(prefix + "empty show_output")

    # category coverage
    for cat in CATEGORIES:
        if cat_counts.get(cat, 0) == 0:
            errors.append(f"Category '{cat}' is not represented in the dataset.")

    # at least one ACL deny-style finding etc. are handled by checker tests.
    if errors:
        ok = False
    else:
        ok = True
        warnings.append("Dataset passed structural validation.")

    return {
        "ok": ok,
        "count": len(cases),
        "errors": errors,
        "warnings": warnings,
        "category_counts": {k: v for k, v in cat_counts.items() if v},
        "severity_counts": {k: v for k, v in sev_counts.items() if v},
    }
