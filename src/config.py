"""Central configuration: field mappings, thresholds and plain-English explanations.

Yahoo Finance renames statement rows from time to time, so each standard metric
lists several known labels. When a new label shows up, add it here rather than
in the logic.
"""

CRORE = 1_00_00_000  # 1 crore = 10 million

# Standard metric -> (statement, [candidate yfinance row labels in priority order])
FIELD_MAP: dict[str, tuple[str, list[str]]] = {
    "revenue": ("income", ["Total Revenue", "Operating Revenue"]),
    "ebitda": ("income", ["EBITDA", "Normalized EBITDA"]),
    "ebit": ("income", ["EBIT", "Operating Income"]),
    "interest_expense": ("income", ["Interest Expense", "Interest Expense Non Operating"]),
    "net_profit": ("income", ["Net Income", "Net Income Common Stockholders",
                              "Net Income From Continuing Operation Net Minority Interest"]),
    "total_assets": ("balance", ["Total Assets"]),
    "total_equity": ("balance", ["Stockholders Equity", "Common Stock Equity",
                                 "Total Equity Gross Minority Interest"]),
    "total_debt": ("balance", ["Total Debt"]),
    "current_assets": ("balance", ["Current Assets"]),
    "current_liabilities": ("balance", ["Current Liabilities"]),
    "operating_cash_flow": ("cashflow", ["Operating Cash Flow",
                                         "Cash Flow From Continuing Operating Activities"]),
    "capex": ("cashflow", ["Capital Expenditure"]),
    "shares_outstanding": ("balance", ["Ordinary Shares Number", "Share Issued"]),
}

# Metrics whose raw value is a count (shares), not money.
SHARE_METRICS = {"shares_outstanding"}

# CSV upload contract (money in ₹ crore, shares in crore shares).
CSV_REQUIRED_COLUMNS = ["fy", "revenue", "net_profit", "total_equity"]
CSV_OPTIONAL_COLUMNS = [
    "ebitda", "ebit", "interest_expense", "total_assets", "total_debt",
    "current_assets", "current_liabilities", "operating_cash_flow", "capex",
    "shares_outstanding",
]
CSV_MAX_BYTES = 2 * 1024 * 1024  # 2 MB

KEY_FIGURES = [
    ("revenue", "Revenue"),
    ("ebitda", "EBITDA"),
    ("net_profit", "Net Profit"),
    ("total_debt", "Total Debt"),
    ("total_equity", "Total Equity"),
    ("operating_cash_flow", "Operating Cash Flow"),
    ("free_cash_flow", "Free Cash Flow"),
]

# Ratio key -> (display name, unit) ; unit is "%", "x" or "₹"
RATIOS: dict[str, tuple[str, str]] = {
    "revenue_growth": ("Revenue growth (YoY)", "%"),
    "net_margin": ("Net profit margin", "%"),
    "ebitda_margin": ("EBITDA margin", "%"),
    "roe": ("Return on equity (ROE)", "%"),
    "roce": ("Return on capital employed (ROCE)", "%"),
    "debt_to_equity": ("Debt-to-equity", "x"),
    "current_ratio": ("Current ratio", "x"),
    "interest_coverage": ("Interest coverage", "x"),
    "cash_conversion": ("Cash conversion (OCF ÷ Net profit)", "x"),
    "eps": ("Earnings per share (EPS)", "₹"),
}

# Ratios that are not meaningful for banks / NBFCs / insurers.
NOT_MEANINGFUL_FOR_FINANCIALS = {"current_ratio", "ebitda_margin", "interest_coverage", "roce"}

# Traffic-light thresholds. "higher_is_better" decides direction.
# green if value beats `good`, red if it is worse than `bad`, amber in between.
THRESHOLDS: dict[str, dict] = {
    "debt_to_equity": {"good": 1.0, "bad": 2.0, "higher_is_better": False},
    "interest_coverage": {"good": 3.0, "bad": 1.5, "higher_is_better": True},
    "current_ratio": {"good": 1.2, "bad": 1.0, "higher_is_better": True},
    "cash_conversion": {"good": 0.8, "bad": 0.5, "higher_is_better": True},
}

FLAG_LABELS = {"green": "🟢 Healthy", "amber": "🟠 Watch", "red": "🔴 Risk"}

EXPLANATIONS: dict[str, str] = {
    "revenue_growth": "How much sales grew versus the previous year. Formula: (Revenue this year ÷ last year − 1) × 100.",
    "net_margin": "Of every ₹100 of sales, how many rupees are left as profit after all costs and tax. Formula: Net profit ÷ Revenue × 100.",
    "ebitda_margin": "Operating profitability before interest, tax, depreciation and amortisation. Formula: EBITDA ÷ Revenue × 100.",
    "roe": "Profit earned on shareholders' money. Formula: Net profit ÷ average equity (opening + closing) ÷ 2 × 100.",
    "roce": "Profit earned on all long-term capital (equity + debt). Formula: EBIT ÷ (Equity + Debt) × 100.",
    "debt_to_equity": "How much the company borrows compared with what shareholders own. Below 1 is generally comfortable. Formula: Total debt ÷ Equity.",
    "current_ratio": "Ability to pay bills due within a year from short-term assets. Above 1.2 is generally comfortable. Formula: Current assets ÷ Current liabilities.",
    "interest_coverage": "How many times operating profit covers the interest bill. Below 1.5 is a warning sign. Formula: EBIT ÷ Interest expense.",
    "cash_conversion": "Whether reported profit actually turns into cash. Above 0.8 is healthy. Formula: Operating cash flow ÷ Net profit.",
    "eps": "Profit attributable to each share, in rupees. Formula: Net profit ÷ Shares outstanding.",
}

DISCLAIMER = (
    "For educational use only. Not investment advice. Data from Yahoo Finance may be "
    "incomplete or delayed — verify with the company's annual report or NSE/BSE filings."
)
