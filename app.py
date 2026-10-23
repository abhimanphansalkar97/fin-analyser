"""Streamlit UI for the Indian company financial analyser. Logic lives in src/."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import DISCLAIMER, EXPLANATIONS, KEY_FIGURES, RATIOS, THRESHOLDS
from src.data_sources import DataSourceError, fetch_yfinance, load_csv
from src.formatting import flag_for, flag_label, format_by_unit, format_inr_cr, format_pct, indian_group
from src.normalise import from_csv_frame, from_yfinance, is_financial_company, normalise_ticker
from src.ratios import add_free_cash_flow, cagr, compute_all

st.set_page_config(page_title="Company Financials Analyser", page_icon="📊", layout="wide")

BLUE, ORANGE = "#1f6feb", "#d95f02"  # colour-blind-safe pair


@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch(symbol: str) -> dict:
    # Exceptions are not cached by st.cache_data, so failures are retried on the next click.
    return fetch_yfinance(symbol)


def money_formatter(currency: str):
    if currency == "INR":
        return format_inr_cr
    return lambda v: "N/A" if pd.isna(v) else f"{currency} {indian_group(v)} Cr"


# ---------- Input ----------
st.title("📊 Indian Company Financials Analyser")
st.caption("Annual financial health check for NSE/BSE listed companies. " + DISCLAIMER)

source = st.radio("Data source", ["Fetch online (Yahoo Finance)", "Upload CSV"], horizontal=True)

if source.startswith("Fetch"):
    col_in, col_btn = st.columns([3, 1], vertical_alignment="bottom")
    ticker_text = col_in.text_input(
        "Ticker", placeholder="e.g. TCS, INFY, HDFCBANK.NS, 500325.BO",
        help="NSE symbol (TCS), NSE with suffix (TCS.NS), or BSE code with .BO (500325.BO).",
    )
    clicked = col_btn.button("Analyse", type="primary", disabled=not ticker_text.strip(),
                             width="stretch")
    if clicked:
        symbol, note = normalise_ticker(ticker_text)
        if symbol is None:
            st.error(note)
            st.session_state.pop("analysis", None)
        else:
            if note:
                st.info(note)
            try:
                with st.spinner(f"Fetching annual statements for {symbol}…"):
                    raw = cached_fetch(symbol)
                frame = from_yfinance(raw["statements"])
                if frame.empty:
                    raise DataSourceError(
                        f"Yahoo Finance returned statements for {symbol}, but none of the key "
                        "figures (revenue, net profit, equity) were present. Try uploading a CSV."
                    )
                info = raw["info"]
                st.session_state["analysis"] = {
                    "frame": frame, "info": info, "symbol": symbol,
                    "source": "Yahoo Finance (via yfinance)",
                    "financial": is_financial_company(info),
                    "currency": str(info.get("financialCurrency") or "INR").upper(),
                }
            except DataSourceError as err:
                st.error(str(err))
                st.session_state.pop("analysis", None)
else:
    with open("assets/template.csv", "rb") as fh:
        st.download_button("⬇️ Download CSV template", fh.read(), "template.csv", "text/csv")
    st.caption("Fill one row per financial year. Money in ₹ crore, shares in crore. "
               "Required: fy, revenue, net_profit, total_equity. Max 2 MB.")
    upload = st.file_uploader("Upload your CSV", type=["csv"])
    name = st.text_input("Company name (optional, for labels)", placeholder="e.g. My Company Ltd")
    if st.button("Analyse", type="primary", disabled=upload is None):
        try:
            df, warnings = load_csv(upload.getvalue(), upload.name)
            for w in warnings:
                st.warning(w)
            st.session_state["analysis"] = {
                "frame": from_csv_frame(df), "info": {"longName": name.strip() or "Uploaded company"},
                "symbol": (name.strip() or "upload").replace(" ", "_"),
                "source": "User upload", "financial": False, "currency": "INR",
            }
        except DataSourceError as err:
            st.error(str(err))
            st.session_state.pop("analysis", None)


# ---------- Dashboard ----------
def render(a: dict) -> None:
    frame = add_free_cash_flow(a["frame"])
    fys = list(frame.columns)
    info, currency = a["info"], a["currency"]
    fmt_money = money_formatter(currency)
    ratios = compute_all(frame, is_financial=a["financial"])

    st.divider()
    st.header(info.get("longName") or info.get("shortName") or a["symbol"])
    meta = [a["symbol"] if a["source"] != "User upload" else None,
            info.get("sector"), info.get("industry"),
            f"{fys[0]}–{fys[-1]}" if len(fys) > 1 else fys[0], f"Source: {a['source']}"]
    st.caption(" · ".join(m for m in meta if m))

    if currency != "INR":
        st.warning(f"Statements are reported in {currency}, not INR. Values are shown in "
                   f"{currency} crore and are not converted.")
    if a["financial"]:
        st.info("This looks like a bank/NBFC/insurer. Current ratio, EBITDA margin, interest "
                "coverage and ROCE are not meaningful for such businesses and are shown as N/A.")

    # Key figures
    st.subheader("Key figures")
    kf = pd.DataFrame(
        {fy: [fmt_money(frame.at[k, fy]) if k in frame.index else "N/A" for k, _ in KEY_FIGURES]
         for fy in fys},
        index=[label for _, label in KEY_FIGURES],
    )
    st.table(kf)

    c1, c2 = st.columns(2)
    for col, metric, label in [(c1, "revenue", "Revenue 3-yr CAGR"),
                               (c2, "net_profit", "Net profit 3-yr CAGR")]:
        r = cagr(frame, metric)
        col.metric(label, format_pct(r.value) if r.value is not None else r.reason)

    # Ratios
    st.subheader("Ratios")
    latest = fys[-1]
    rows, reasons = [], []
    for key, (name, unit) in RATIOS.items():
        row = {"Ratio": name}
        for fy in fys:
            res = ratios[key][fy]
            row[fy] = format_by_unit(res.value, unit)
            if res.reason and not (key == "revenue_growth" and fy == fys[0]):
                reasons.append(f"**{name} ({fy})** — {res.reason}")
        row[f"Status ({latest})"] = (
            (flag_label(flag_for(key, ratios[key][latest].value)) or "N/A") if key in THRESHOLDS else "—"
        )
        rows.append(row)
    st.table(pd.DataFrame(rows).set_index("Ratio"))

    with st.expander("What these ratios mean"):
        for key, (name, _) in RATIOS.items():
            st.markdown(f"**{name}** — {EXPLANATIONS[key]}")
        st.markdown("**Status thresholds** — Debt-to-equity: <1 Healthy, 1–2 Watch, >2 Risk · "
                    "Interest coverage: >3 Healthy, 1.5–3 Watch, <1.5 Risk · "
                    "Current ratio: >1.2 Healthy, 1–1.2 Watch, <1 Risk · "
                    "Cash conversion: >0.8 Healthy, 0.5–0.8 Watch, <0.5 Risk.")
    if reasons:
        with st.expander(f"Why some values are N/A ({len(reasons)})"):
            st.markdown("\n".join(f"- {r}" for r in reasons))

    # Charts
    st.subheader("Trends")
    if len(fys) < 2:
        st.info("Needs at least 2 years of data to show trends and growth.")
    else:
        def series(metric):
            return [frame.at[metric, fy] if metric in frame.index else None for fy in fys]

        def ratio_series(key):
            return [ratios[key][fy].value for fy in fys]

        unit = "₹ Cr" if currency == "INR" else f"{currency} Cr"
        charts = []

        f1 = go.Figure([go.Bar(name="Revenue", x=fys, y=series("revenue"), marker_color=BLUE),
                        go.Bar(name="Net profit", x=fys, y=series("net_profit"), marker_color=ORANGE)])
        f1.update_layout(title="Revenue & net profit", yaxis_title=unit, barmode="group")
        charts.append(f1)

        f2 = go.Figure([go.Scatter(name="Net margin", x=fys, y=ratio_series("net_margin"),
                                   mode="lines+markers", line_color=ORANGE),
                        go.Scatter(name="EBITDA margin", x=fys, y=ratio_series("ebitda_margin"),
                                   mode="lines+markers", line_color=BLUE, line_dash="dash")])
        f2.update_layout(title="Margins", yaxis_title="%")
        charts.append(f2)

        f3 = go.Figure([go.Scatter(name="Debt-to-equity", x=fys, y=ratio_series("debt_to_equity"),
                                   mode="lines+markers", line_color=BLUE)])
        f3.add_hline(y=1, line_dash="dot", annotation_text="1.0x comfort line")
        f3.update_layout(title="Debt-to-equity", yaxis_title="x (times)")
        charts.append(f3)

        f4 = go.Figure([go.Bar(name="Operating cash flow", x=fys, y=series("operating_cash_flow"),
                               marker_color=BLUE),
                        go.Bar(name="Net profit", x=fys, y=series("net_profit"), marker_color=ORANGE)])
        f4.update_layout(title="Operating cash flow vs net profit", yaxis_title=unit, barmode="group")
        charts.append(f4)

        for i in range(0, 4, 2):
            cols = st.columns(2)
            for col, fig in zip(cols, charts[i:i + 2]):
                fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10),
                                  legend=dict(orientation="h", y=-0.2), xaxis_title="Financial year")
                col.plotly_chart(fig, width="stretch")

    # Export
    export = frame.copy()
    for key, (name, unit) in RATIOS.items():
        export.loc[f"{name} ({unit})"] = [ratios[key][fy].value for fy in fys]
    export.index.name = "metric (money in crore)"
    fname = f"{a['symbol']}_analysis_{date.today().strftime('%d-%m-%Y')}.csv"
    st.download_button("⬇️ Download analysis (CSV)", export.to_csv().encode("utf-8"), fname, "text/csv")


if "analysis" in st.session_state:
    render(st.session_state["analysis"])

st.divider()
st.caption(f"⚠️ {DISCLAIMER}")
