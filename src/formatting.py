"""Indian number formatting and traffic-light flags."""

from __future__ import annotations

import math

from src.config import FLAG_LABELS, THRESHOLDS


def _is_missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def indian_group(value: float, decimals: int = 2) -> str:
    """Format a number with Indian digit grouping, e.g. 123456.789 -> '1,23,456.79'."""
    negative = value < 0
    text = f"{abs(value):.{decimals}f}"
    whole, _, frac = text.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    out = f"{whole}.{frac}" if frac else whole
    return f"-{out}" if negative else out


def format_inr_cr(value) -> str:
    """₹ crore with Indian grouping: 123456.789 -> '₹1,23,456.79 Cr'."""
    if _is_missing(value):
        return "N/A"
    text = indian_group(value, 2)
    if text.startswith("-"):
        return f"-₹{text[1:]} Cr"
    return f"₹{text} Cr"


def format_pct(value) -> str:
    return "N/A" if _is_missing(value) else f"{value:.1f}%"


def format_ratio(value) -> str:
    return "N/A" if _is_missing(value) else f"{value:.2f}x"


def format_rupees(value) -> str:
    if _is_missing(value):
        return "N/A"
    text = indian_group(value, 2)
    return f"-₹{text[1:]}" if text.startswith("-") else f"₹{text}"


def format_by_unit(value, unit: str) -> str:
    return {"%": format_pct, "x": format_ratio, "₹": format_rupees}[unit](value)


def flag_for(ratio_key: str, value) -> str | None:
    """Return 'green' / 'amber' / 'red' for ratios with thresholds, else None."""
    rule = THRESHOLDS.get(ratio_key)
    if rule is None or _is_missing(value):
        return None
    good, bad = rule["good"], rule["bad"]
    if rule["higher_is_better"]:
        if value > good:
            return "green"
        if value < bad:
            return "red"
        return "amber"
    if value < good:
        return "green"
    if value > bad:
        return "red"
    return "amber"


def flag_label(colour: str | None) -> str:
    return FLAG_LABELS.get(colour, "") if colour else ""
