"""Turn raw yfinance statements or a CSV into one standard frame.

Standard frame: index = metric keys from config.FIELD_MAP, columns = FY labels
ordered oldest -> newest, money in ₹ crore, shares in crore shares.
"""

from __future__ import annotations

import re

import pandas as pd

from src.config import CRORE, FIELD_MAP

_TICKER_RE = re.compile(r"^[A-Z0-9&\-]{1,20}(\.(NS|BO))?$")


def normalise_ticker(text: str) -> tuple[str | None, str | None]:
    """Return (symbol, note). Symbol is None when the input is unusable."""
    raw = (text or "").strip().upper()
    if not raw:
        return None, None
    if not _TICKER_RE.match(raw):
        return None, f"'{text.strip()}' doesn't look like an NSE/BSE symbol."
    if raw.endswith((".NS", ".BO")):
        return raw, None
    if raw.isdigit():  # 6-digit BSE scrip codes like 500325
        return f"{raw}.BO", f"Interpreted as BSE code: using {raw}.BO"
    return f"{raw}.NS", f"No exchange given — using NSE: {raw}.NS"


def fy_label(period_end) -> str:
    """Indian FY: period ending Jan–Mar of year Y -> FY{Y}; later months -> FY{Y+1}."""
    ts = pd.Timestamp(period_end)
    return f"FY{ts.year if ts.month <= 3 else ts.year + 1}"


def _pick_row(statement: pd.DataFrame | None, labels: list[str]) -> pd.Series | None:
    if statement is None or statement.empty:
        return None
    for label in labels:
        if label in statement.index:
            row = statement.loc[label]
            if isinstance(row, pd.DataFrame):  # duplicate labels: take first
                row = row.iloc[0]
            if row.notna().any():
                return row
    return None


def from_yfinance(statements: dict[str, pd.DataFrame | None]) -> pd.DataFrame:
    """statements: {'income': df, 'balance': df, 'cashflow': df} with Timestamp columns."""
    series = {}
    for metric, (stmt, labels) in FIELD_MAP.items():
        row = _pick_row(statements.get(stmt), labels)
        if row is not None:
            series[metric] = pd.to_numeric(row, errors="coerce") / CRORE
    if not series:
        return pd.DataFrame()
    frame = pd.DataFrame(series).T
    frame.columns = [fy_label(c) for c in frame.columns]
    # Merging statements with different dates can create duplicate FY columns: keep first non-null.
    frame = frame.T.groupby(level=0).first().T
    frame = frame[sorted(frame.columns)]
    frame = frame.reindex(list(FIELD_MAP))
    # Drop FY columns where nothing core is present (Yahoo sometimes adds an empty old year).
    core = frame.loc[["revenue", "net_profit", "total_equity"]]
    frame = frame.loc[:, core.notna().any()]
    return frame.astype(float)


def from_csv_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Validated CSV (one row per FY) -> standard frame."""
    df = df.copy()
    df["fy"] = df["fy"].astype(str).str.strip().str.upper()
    df = df.set_index("fy").sort_index()
    frame = df.T.reindex(list(FIELD_MAP))
    return frame.astype(float)


def is_financial_company(info: dict | None) -> bool:
    """Banks, NBFCs and insurers, judged from Yahoo's sector/industry fields.

    CSV uploads have no sector info, so they return False and missing fields
    simply show 'not available' rather than a guessed 'bank' label.
    """
    info = info or {}
    sector = str(info.get("sector", "")).lower()
    industry = str(info.get("industry", "")).lower()
    return "financial" in sector or any(
        w in industry for w in ("bank", "insurance", "credit services", "capital markets")
    )
