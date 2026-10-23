"""Data sources: Yahoo Finance (via yfinance) and user-uploaded CSV."""

from __future__ import annotations

import io

import pandas as pd

from src.config import CSV_MAX_BYTES, CSV_OPTIONAL_COLUMNS, CSV_REQUIRED_COLUMNS


class DataSourceError(Exception):
    """Raised with a user-facing message; the UI shows str(err) as-is."""


class TickerNotFound(DataSourceError):
    pass


class SourceUnavailable(DataSourceError):
    pass


def fetch_yfinance(symbol: str) -> dict:
    """Fetch annual statements + company info for one symbol.

    Returns {'statements': {'income','balance','cashflow'}, 'info': dict}.
    yfinance often returns empty frames instead of raising when Yahoo is
    unreachable, so an all-empty result is reported as 'not found or unavailable'.
    """
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        statements = {
            "income": ticker.financials,
            "balance": ticker.balance_sheet,
            "cashflow": ticker.cashflow,
        }
    except Exception as exc:  # network errors, rate limits, library changes
        raise SourceUnavailable(
            "Data source unavailable, try again in a minute or upload a CSV. "
            f"(Details: {type(exc).__name__})"
        ) from exc

    if all(df is None or df.empty for df in statements.values()):
        base = symbol.rsplit(".", 1)[0]
        alt = f"{base}.BO" if symbol.endswith(".NS") else f"{base}.NS"
        raise TickerNotFound(
            f"No financial data found for {symbol}. Check the symbol on nseindia.com, "
            f"try {alt}, or upload a CSV. If the symbol is correct, Yahoo Finance may be "
            "temporarily unavailable — try again in a minute."
        )

    try:
        info = ticker.info or {}
    except Exception:
        info = {}  # info is nice-to-have (name, sector); statements are what matter
    return {"statements": statements, "info": info}


def load_csv(data: bytes, filename: str) -> tuple[pd.DataFrame, list[str]]:
    """Validate an uploaded CSV. Returns (clean dataframe, warnings). Raises DataSourceError."""
    if not filename.lower().endswith(".csv"):
        raise DataSourceError("Please upload a .csv file (use the template provided).")
    if len(data) > CSV_MAX_BYTES:
        raise DataSourceError("File is larger than 2 MB. The template needs only a few rows.")
    if not data.strip():
        raise DataSourceError("The uploaded file is empty.")

    try:
        df = pd.read_csv(io.BytesIO(data), comment="#", skip_blank_lines=True)
    except Exception as exc:
        raise DataSourceError(f"Could not read the CSV: {exc}") from exc

    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in CSV_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise DataSourceError(f"Missing required column(s): {', '.join(missing)}")
    if df.empty:
        raise DataSourceError("The CSV has headers but no data rows.")

    warnings = []
    known = set(CSV_REQUIRED_COLUMNS) | set(CSV_OPTIONAL_COLUMNS)
    extra = [c for c in df.columns if c not in known]
    if extra:
        warnings.append(f"Ignored unknown column(s): {', '.join(extra)}")
        df = df.drop(columns=extra)

    df["fy"] = df["fy"].astype(str).str.strip().str.upper()
    bad_fy = df.loc[~df["fy"].str.fullmatch(r"FY\d{4}"), "fy"]
    if not bad_fy.empty:
        raise DataSourceError(
            f"Invalid FY value(s): {', '.join(bad_fy.astype(str))}. Use the format FY2025."
        )
    dupes = df.loc[df["fy"].duplicated(), "fy"].unique()
    if len(dupes):
        raise DataSourceError(f"Duplicate FY row(s): {', '.join(dupes)}")

    errors = []
    for col in [c for c in df.columns if c != "fy"]:
        raw = df[col]
        # Allow Indian-style commas like "1,23,456.7"
        cleaned = raw.astype(str).str.replace(",", "", regex=False).str.strip()
        cleaned = cleaned.replace({"": None, "nan": None, "NaN": None})
        numeric = pd.to_numeric(cleaned, errors="coerce")
        bad = numeric.isna() & cleaned.notna()
        for idx in df.index[bad]:
            errors.append(f"row {idx + 1} ({df.at[idx, 'fy']}), column '{col}': '{raw[idx]}'")
        df[col] = numeric
    if errors:
        raise DataSourceError("Non-numeric value(s) found — " + "; ".join(errors[:10]))

    for col in CSV_REQUIRED_COLUMNS[1:]:
        if df[col].isna().all():
            raise DataSourceError(f"Required column '{col}' has no values.")
    return df, warnings
