"""Pure ratio functions. Every function returns a Result: (value or None, reason or None).

Input is the standard frame: rows = metric keys, columns = FY labels (oldest -> newest),
money in ₹ crore, shares in crore shares. Missing values are NaN.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import pandas as pd

from src.config import NOT_MEANINGFUL_FOR_FINANCIALS, RATIOS


class Result(NamedTuple):
    value: float | None
    reason: str | None = None


FINANCIALS_REASON = "N/A — not meaningful for banks/financials"


def _get(frame: pd.DataFrame, metric: str, fy: str):
    if metric not in frame.index or fy not in frame.columns:
        return None
    v = frame.at[metric, fy]
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return float(v)


def safe_divide(num, den, num_name: str, den_name: str, positive_den: bool = False) -> Result:
    """Divide with explicit reasons instead of errors or infinity."""
    if num is None:
        return Result(None, f"N/A — {num_name} not available")
    if den is None:
        return Result(None, f"N/A — {den_name} not available")
    if den == 0:
        return Result(None, f"N/A — {den_name} is zero")
    if positive_den and den < 0:
        return Result(None, f"N/A — {den_name} is negative")
    return Result(num / den)


def _pct(r: Result) -> Result:
    return Result(r.value * 100, None) if r.value is not None else r


def revenue_growth(frame, fy, prev_fy) -> Result:
    if prev_fy is None:
        return Result(None, "N/A — needs previous year")
    cur, prev = _get(frame, "revenue", fy), _get(frame, "revenue", prev_fy)
    r = safe_divide(cur, prev, "revenue", "previous year revenue", positive_den=True)
    return Result((r.value - 1) * 100) if r.value is not None else r


def net_margin(frame, fy, _prev=None) -> Result:
    return _pct(safe_divide(_get(frame, "net_profit", fy), _get(frame, "revenue", fy),
                            "net profit", "revenue", positive_den=True))


def ebitda_margin(frame, fy, _prev=None) -> Result:
    return _pct(safe_divide(_get(frame, "ebitda", fy), _get(frame, "revenue", fy),
                            "EBITDA", "revenue", positive_den=True))


def roe(frame, fy, prev_fy) -> Result:
    np_ = _get(frame, "net_profit", fy)
    closing = _get(frame, "total_equity", fy)
    opening = _get(frame, "total_equity", prev_fy) if prev_fy else None
    equity = (opening + closing) / 2 if (opening is not None and closing is not None) else closing
    return _pct(safe_divide(np_, equity, "net profit", "equity", positive_den=True))


def roce(frame, fy, _prev=None) -> Result:
    equity, debt = _get(frame, "total_equity", fy), _get(frame, "total_debt", fy)
    capital = None if equity is None else equity + (debt or 0.0)
    return _pct(safe_divide(_get(frame, "ebit", fy), capital, "EBIT", "capital employed",
                            positive_den=True))


def debt_to_equity(frame, fy, _prev=None) -> Result:
    return safe_divide(_get(frame, "total_debt", fy), _get(frame, "total_equity", fy),
                       "total debt", "equity", positive_den=True)


def current_ratio(frame, fy, _prev=None) -> Result:
    return safe_divide(_get(frame, "current_assets", fy), _get(frame, "current_liabilities", fy),
                       "current assets", "current liabilities", positive_den=True)


def interest_coverage(frame, fy, _prev=None) -> Result:
    interest = _get(frame, "interest_expense", fy)
    interest = abs(interest) if interest is not None else None  # Yahoo sometimes reports as negative
    return safe_divide(_get(frame, "ebit", fy), interest, "EBIT", "interest expense")


def cash_conversion(frame, fy, _prev=None) -> Result:
    np_ = _get(frame, "net_profit", fy)
    if np_ is not None and np_ < 0:
        return Result(None, "N/A — net profit is negative")
    return safe_divide(_get(frame, "operating_cash_flow", fy), np_,
                       "operating cash flow", "net profit")


def eps(frame, fy, _prev=None) -> Result:
    # net profit (₹ Cr) ÷ shares (crore) = ₹ per share
    return safe_divide(_get(frame, "net_profit", fy), _get(frame, "shares_outstanding", fy),
                       "net profit", "shares outstanding", positive_den=True)


RATIO_FUNCS = {
    "revenue_growth": revenue_growth, "net_margin": net_margin, "ebitda_margin": ebitda_margin,
    "roe": roe, "roce": roce, "debt_to_equity": debt_to_equity,
    "current_ratio": current_ratio, "interest_coverage": interest_coverage,
    "cash_conversion": cash_conversion, "eps": eps,
}
assert set(RATIO_FUNCS) == set(RATIOS)


def add_free_cash_flow(frame: pd.DataFrame) -> pd.DataFrame:
    """FCF = OCF − |capex|. Yahoo reports capex as negative; CSV users may enter positive."""
    out = frame.copy()
    if "operating_cash_flow" in out.index:
        capex = out.loc["capex"].abs() if "capex" in out.index else 0.0
        out.loc["free_cash_flow"] = out.loc["operating_cash_flow"] - capex
    return out


def compute_all(frame: pd.DataFrame, is_financial: bool = False) -> dict[str, dict[str, Result]]:
    """Return {ratio_key: {fy: Result}} for every ratio and FY column."""
    fys = list(frame.columns)
    out: dict[str, dict[str, Result]] = {}
    for key, func in RATIO_FUNCS.items():
        out[key] = {}
        for i, fy in enumerate(fys):
            if is_financial and key in NOT_MEANINGFUL_FOR_FINANCIALS:
                out[key][fy] = Result(None, FINANCIALS_REASON)
                continue
            prev = fys[i - 1] if i > 0 else None
            out[key][fy] = func(frame, fy, prev)
    return out


def cagr(frame: pd.DataFrame, metric: str, years: int = 3) -> Result:
    """CAGR over `years` years; needs years + 1 data points."""
    fys = list(frame.columns)
    if len(fys) < years + 1:
        return Result(None, f"Needs {years + 1} years of data")
    start, end = _get(frame, metric, fys[-(years + 1)]), _get(frame, metric, fys[-1])
    if start is None or end is None:
        return Result(None, "N/A — data missing")
    if start <= 0 or end <= 0:
        return Result(None, "N/A — not meaningful with zero or negative values")
    return Result(((end / start) ** (1 / years) - 1) * 100)
