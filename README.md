# Indian Company Financials Analyser

A simple Streamlit app that gives a quick financial health check of an NSE/BSE listed company. It shows the last 3–4 financial years of key figures, 10 ratios with plain-English explanations, traffic-light flags and trend charts. All amounts are in **₹ crore** with Indian digit grouping (₹1,23,456.79 Cr).

> **Disclaimer:** For educational use only. Not investment advice. Data from Yahoo Finance may be incomplete or delayed — verify with the company's annual report or NSE/BSE filings.

## Setup (one command)

Needs Python 3.11 or newer.

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

On Windows, use `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

## Run

```bash
streamlit run app.py
```

The app opens at http://localhost:8501.

## How to use

**Fetch online**
- Type a ticker and click **Analyse**:
  - `TCS` becomes `TCS.NS`. The app adds NSE by default.
  - `HDFCBANK.NS` is the explicit NSE form.
  - `500325.BO` is a BSE scrip code. Bare 6-digit codes get `.BO` added.
- Results are cached for 1 hour, so repeat lookups are instant.

**Upload CSV**
- Use this when Yahoo is down, the data looks wrong, or you want to analyse your own figures:
  1. Click **Download CSV template**.
  2. Replace the sample rows with your own data, one row per financial year (e.g. `FY2025`).
  3. Upload the file and click **Analyse**.
- Money columns are in ₹ crore. `shares_outstanding` is in crore shares.
- **Required columns:** `fy`, `revenue`, `net_profit`, `total_equity`.
- Leave a cell blank if you don't have the number. The related ratio shows "N/A" with a reason.
- You can write capex as positive or negative.
- Lines starting with `#` are ignored.
- Maximum file size is 2 MB.

**Download analysis**
- Exports figures and ratios as `<ticker>_analysis_DD-MM-YYYY.csv`.

## Ratio glossary

| Ratio | Formula | Status thresholds |
|---|---|---|
| Revenue growth | Revenue ÷ previous year − 1 | — |
| Net profit margin | Net profit ÷ Revenue | — |
| EBITDA margin | EBITDA ÷ Revenue | — |
| ROE | Net profit ÷ average equity (closing equity if only 1 year) | — |
| ROCE | EBIT ÷ (Equity + Debt) | — |
| Debt-to-equity | Total debt ÷ Equity | <1 Healthy · 1–2 Watch · >2 Risk |
| Current ratio | Current assets ÷ Current liabilities | >1.2 Healthy · 1–1.2 Watch · <1 Risk |
| Interest coverage | EBIT ÷ Interest expense | >3 Healthy · 1.5–3 Watch · <1.5 Risk |
| Cash conversion | Operating cash flow ÷ Net profit | >0.8 Healthy · 0.5–0.8 Watch · <0.5 Risk |
| EPS | Net profit ÷ Shares outstanding | — |
| 3-yr CAGR | (Latest ÷ value 3 years earlier)^(1/3) − 1 | needs 4 years of data |

You can change the thresholds in `src/config.py` (`THRESHOLDS`).

**Banks, NBFCs and insurers.** Yahoo's sector field is used to detect these businesses. For them, the current ratio, EBITDA margin, interest coverage and ROCE show "N/A — not meaningful for banks/financials", because those ratios don't describe a lender's health.

## Data limitations

- **Unofficial source.** `yfinance` is an unofficial wrapper around Yahoo Finance. Yahoo can change row names, drop fields, rate-limit requests or return nothing at all.
- **Missing data shows as N/A.** The app never fills a gap with 0. When data is missing, it shows N/A and tells you why.
- **Limited history.** Yahoo usually provides about 4 annual years, and sometimes the oldest year is partial.
- **Consolidated vs standalone.** Figures are whatever Yahoo reports, usually consolidated. They can differ from the standalone numbers in a company's annual report.
- **Indian financial year.** Statements ending 31-03-2025 are labelled FY2025.
- **Renamed rows.** If a figure goes missing because Yahoo renamed a row, add the new label to `FIELD_MAP` in `src/config.py`.

## Tests

```bash
pytest -q
```

The tests cover ratio maths, Indian number formatting, ticker and FY handling, and CSV validation. None of them use the network.

## Project structure

```
fin-analyser/
├── app.py               # Streamlit UI only
├── src/
│   ├── config.py        # field mappings, thresholds, explanations
│   ├── data_sources.py  # yfinance fetch + CSV validation
│   ├── normalise.py     # raw data → standard frame (₹ Cr, FY labels)
│   ├── ratios.py        # pure ratio + CAGR functions
│   └── formatting.py    # Indian number formatting, flags
├── assets/template.csv  # sample data (not a real company)
├── tests/
├── requirements.txt
└── pytest.ini
```

## Sharing (optional)

1. Push this folder to a GitHub repo.
2. Go to https://share.streamlit.io and choose **New app**.
3. Select the repo and pick `app.py` as the main file.

Streamlit Community Cloud installs `requirements.txt` automatically.
