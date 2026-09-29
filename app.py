import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import quote

# ============================================================
# STOCK QUALITY CHECKER
# Stage 2 only
#
# Input:
#   Stock name / NSE symbol
#
# Checks:
#   1. Promoter pledge
#   2. Cash flow vs profit
#   3. ROCE consistency
#   4. Debt trend
#   5. Sales consistency
#   6. Profit consistency
#   7. Valuation
#   8. Possible red flags
#
# Primary structured source:
#   Yahoo Finance / yfinance
#
# Secondary web source:
#   Public Screener / Trendlyne pages
# ============================================================

st.set_page_config(
    page_title="Stock Quality Checker",
    page_icon="⭐",
    layout="centered"
)

# ------------------------------------------------------------
# PAGE STYLE
# ------------------------------------------------------------

st.markdown(
    """
    <style>

    .main-title {
        font-size: 32px;
        font-weight: 700;
        text-align: center;
    }

    .subtitle {
        text-align: center;
        color: #777;
        margin-bottom: 25px;
    }

    .score-box {
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        border: 1px solid #ddd;
        margin: 15px 0;
    }

    .good {
        color: #16803c;
        font-weight: 700;
    }

    .warning {
        color: #b77900;
        font-weight: 700;
    }

    .bad {
        color: #c62828;
        font-weight: 700;
    }

    .unknown {
        color: #777;
        font-weight: 700;
    }

    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    '<div class="main-title">⭐ Stock Quality Checker</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Stage 2 — Fundamental Quality Analysis</div>',
    unsafe_allow_html=True
)

st.info(
    "Enter a stock that has already passed your Stage-1 "
    "Screener.in scan."
)


# ============================================================
# INPUT
# ============================================================

stock_input = st.text_input(
    "Enter NSE stock name or symbol",
    placeholder="Example: TATAELXSI or Tata Elxsi"
)

check_button = st.button(
    "🔍 CHECK STOCK",
    use_container_width=True
)


# ============================================================
# HELPERS
# ============================================================

def clean_symbol(value):

    value = value.strip().upper()

    if value.endswith(".NS"):
        return value

    if value.endswith(".BO"):
        return value

    return value + ".NS"


def clean_text(value):

    if value is None:
        return ""

    return str(value).strip()


def number(value):

    if value is None:
        return np.nan

    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)

    text = str(value)

    text = (
        text
        .replace(",", "")
        .replace("₹", "")
        .replace("%", "")
        .replace("Cr.", "")
        .replace("Cr", "")
        .strip()
    )

    try:
        return float(text)
    except:
        return np.nan


def star_string(score, total):

    if total <= 0:
        return "☆☆☆☆☆☆☆☆"

    full = int(score)
    empty = 8 - full

    if empty < 0:
        empty = 0

    return "⭐" * full + "☆" * empty


def result(
    status,
    score,
    message,
    source="Yahoo Finance"
):

    return {
        "status": status,
        "score": score,
        "message": message,
        "source": source
    }


def get_statement_row(df, possible_names):

    if df is None or df.empty:
        return None

    for name in possible_names:

        if name in df.index:

            values = pd.to_numeric(
                df.loc[name],
                errors="coerce"
            )

            values = values.dropna()

            if len(values):
                return values

    return None


# ============================================================
# YAHOO DATA
# ============================================================

def get_yahoo_data(symbol):

    try:

        ticker = yf.Ticker(symbol)

        info = ticker.info

        financials = ticker.financials

        balance = ticker.balance_sheet

        cashflow = ticker.cashflow

        return {
            "ticker": ticker,
            "info": info,
            "financials": financials,
            "balance": balance,
            "cashflow": cashflow
        }

    except Exception as e:

        return {
            "ticker": None,
            "info": {},
            "financials": pd.DataFrame(),
            "balance": pd.DataFrame(),
            "cashflow": pd.DataFrame(),
            "error": str(e)
        }


# ============================================================
# WEB SEARCH / SECONDARY SOURCE
# ============================================================

def web_search_public_pages(company_name):

    """
    Finds public Screener / Trendlyne pages.

    This is only a fallback discovery mechanism.
    It does NOT assume that search results contain
    complete or current data.
    """

    results = []

    try:

        query = quote(
            f"{company_name} Screener.in Trendlyne"
        )

        url = (
            "https://www.google.com/search?q="
            + query
        )

        headers = {
            "User-Agent":
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        for link in soup.find_all("a"):

            href = link.get("href", "")

            text = link.get_text(
                " ",
                strip=True
            )

            if (
                "screener.in/company/" in href
                or "trendlyne.com/fundamentals/" in href
            ):

                results.append({
                    "text": text,
                    "url": href
                })

    except Exception:
        pass

    return results


# ============================================================
# PROMOTER PLEDGE
# ============================================================

def check_promoter_pledge(
    company_name,
    symbol
):

    """
    Yahoo frequently does not provide promoter pledge.

    Try Yahoo first, then public web information.
    """

    yahoo = get_yahoo_data(symbol)

    info = yahoo.get("info", {})

    # Yahoo insider ownership is NOT the same thing as
    # promoter pledge, therefore we do not treat it as
    # promoter pledge.

    pages = web_search_public_pages(
        company_name
    )

    if pages:

        screener_found = any(
            "screener.in" in p["url"]
            for p in pages
        )

        trendlyne_found = any(
            "trendlyne.com" in p["url"]
            for p in pages
        )

        sources = []

        if screener_found:
            sources.append("Screener")

        if trendlyne_found:
            sources.append("Trendlyne")

        if sources:

            return result(
                "VERIFY",
                None,
                "Promoter pledge information "
                "was located on public Indian "
                "market-data pages. Verify the "
                "latest quarter before relying on it.",
                ", ".join(sources)
            )

    return result(
        "UNAVAILABLE",
        None,
        "Reliable promoter-pledge data was "
        "not available through the automated sources.",
        "Web / Yahoo"
    )


# ============================================================
# CASH FLOW VS PROFIT
# ============================================================

def check_cash_flow_vs_profit(
    financials,
    cashflow
):

    if (
        financials is None
        or financials.empty
        or cashflow is None
        or cashflow.empty
    ):

        return result(
            "UNAVAILABLE",
            None,
            "Cash-flow or profit history unavailable."
        )

    profit = get_statement_row(
        financials,
        [
            "Net Income",
            "Net Income Common Stockholders"
        ]
    )

    cfo = get_statement_row(
        cashflow,
        [
            "Operating Cash Flow",
            "Total Cash From Operating Activities"
        ]
    )

    if profit is None or cfo is None:

        return result(
            "UNAVAILABLE",
            None,
            "Operating cash flow and profit "
            "could not both be obtained."
        )

    n = min(
        len(profit),
        len(cfo)
    )

    if n < 2:

        return result(
            "UNAVAILABLE",
            None,
            "Not enough historical data."
        )

    profit = profit.iloc[:n]
    cfo = cfo.iloc[:n]

    ratios = []

    for p, c in zip(profit, cfo):

        if abs(p) > 0:

            ratios.append(
                c / p
            )

    if len(ratios) < 2:

        return result(
            "UNAVAILABLE",
            None,
            "Could not calculate CFO/profit relationship."
        )

    avg_ratio = np.mean(ratios)

    if avg_ratio >= 0.8:

        return result(
            "PASS",
            1,
            f"Average CFO / profit ≈ {avg_ratio:.2f}. "
            "Cash generation broadly supports reported profit."
        )

    if avg_ratio >= 0.5:

        return result(
            "WATCH",
            0,
            f"Average CFO / profit ≈ {avg_ratio:.2f}. "
            "Cash conversion deserves review."
        )

    return result(
        "RED FLAG",
        0,
        f"Average CFO / profit ≈ {avg_ratio:.2f}. "
        "Large cash-flow/profit mismatch."
    )


# ============================================================
# ROCE CONSISTENCY
# ============================================================

def check_roce_consistency(
    financials,
    balance
):

    if (
        financials is None
        or financials.empty
        or balance is None
        or balance.empty
    ):

        return result(
            "UNAVAILABLE",
            None,
            "Financial statements unavailable."
        )

    ebit = get_statement_row(
        financials,
        [
            "EBIT",
            "Operating Income"
        ]
    )

    assets = get_statement_row(
        balance,
        [
            "Total Assets"
        ]
    )

    liabilities = get_statement_row(
        balance,
        [
            "Total Liabilities Net Minority Interest",
            "Total Liabilities"
        ]
    )

    if (
        ebit is None
        or assets is None
        or liabilities is None
    ):

        return result(
            "UNAVAILABLE",
            None,
            "Not enough balance-sheet data "
            "to calculate historical ROCE."
        )

    n = min(
        len(ebit),
        len(assets),
        len(liabilities)
    )

    if n < 3:

        return result(
            "UNAVAILABLE",
            None,
            "Less than three comparable periods."
        )

    roce_values = []

    for i in range(n):

        capital_employed = (
            assets.iloc[i]
            - liabilities.iloc[i]
        )

        if capital_employed > 0:

            roce = (
                ebit.iloc[i]
                / capital_employed
            ) * 100

            roce_values.append(
                roce
            )

    if len(roce_values) < 3:

        return result(
            "UNAVAILABLE",
            None,
            "ROCE could not be calculated reliably."
        )

    recent = roce_values[:5]

    strong_periods = sum(
        r >= 15
        for r in recent
    )

    if strong_periods >= 4:

        return result(
            "PASS",
            1,
            "ROCE has remained relatively strong "
            "across the available periods."
        )

    if strong_periods >= 2:

        return result(
            "WATCH",
            0,
            "ROCE has some strength but is not "
            "consistently strong."
        )

    return result(
        "RED FLAG",
        0,
        "ROCE appears weak across the available periods."
    )


# ============================================================
# DEBT TREND
# ============================================================

def check_debt_trend(balance):

    if balance is None or balance.empty:

        return result(
            "UNAVAILABLE",
            None,
            "Balance-sheet data unavailable."
        )

    debt = get_statement_row(
        balance,
        [
            "Total Debt"
        ]
    )

    if debt is None:

        debt = get_statement_row(
            balance,
            [
                "Long Term Debt"
            ]
        )

    if debt is None or len(debt) < 2:

        return result(
            "UNAVAILABLE",
            None,
            "Historical debt data unavailable."
        )

    recent = debt.iloc[
        :min(5, len(debt))
    ]

    # Yahoo columns are generally newest first.

    newest = recent.iloc[0]
    oldest = recent.iloc[-1]

    if newest < oldest:

        return result(
            "PASS",
            1,
            "Debt has declined over the available period."
        )

    if newest <= oldest * 1.10:

        return result(
            "WATCH",
            0,
            "Debt is broadly stable."
        )

    return result(
        "RED FLAG",
        0,
        "Debt has increased materially over "
        "the available period."
    )


# ============================================================
# SALES CONSISTENCY
# ============================================================

def check_sales_consistency(financials):

    if financials is None or financials.empty:

        return result(
            "UNAVAILABLE",
            None,
            "Revenue history unavailable."
        )

    revenue = get_statement_row(
        financials,
        [
            "Total Revenue",
            "Operating Revenue"
        ]
    )

    if revenue is None or len(revenue) < 3:

        return result(
            "UNAVAILABLE",
            None,
            "At least three revenue periods are required."
        )

    growth = revenue.pct_change()

    # Remove first NaN
    growth = growth.dropna()

    positive = (
        growth > 0
    ).sum()

    if positive >= 3:

        return result(
            "PASS",
            1,
            "Revenue has increased in most available periods."
        )

    if positive >= 2:

        return result(
            "WATCH",
            0,
            "Revenue growth is somewhat inconsistent."
        )

    return result(
        "RED FLAG",
        0,
        "Revenue declined in multiple periods."
    )


# ============================================================
# PROFIT CONSISTENCY
# ============================================================

def check_profit_consistency(financials):

    if financials is None or financials.empty:

        return result(
            "UNAVAILABLE",
            None,
            "Profit history unavailable."
        )

    profit = get_statement_row(
        financials,
        [
            "Net Income",
            "Net Income Common Stockholders"
        ]
    )

    if profit is None or len(profit) < 3:

        return result(
            "UNAVAILABLE",
            None,
            "At least three profit periods are required."
        )

    growth = profit.pct_change().dropna()

    positive = (
        growth > 0
    ).sum()

    if positive >= 3:

        return result(
            "PASS",
            1,
            "Profit has increased in most available periods."
        )

    if positive >= 2:

        return result(
            "WATCH",
            0,
            "Profit growth is somewhat inconsistent."
        )

    return result(
        "RED FLAG",
        0,
        "Profit declined in multiple periods."
    )


# ============================================================
# VALUATION
# ============================================================

def check_valuation(info):

    if not info:

        return result(
            "UNAVAILABLE",
            None,
            "Yahoo valuation data unavailable."
        )

    pe = info.get(
        "trailingPE"
    )

    forward_pe = info.get(
        "forwardPE"
    )

    peg = info.get(
        "pegRatio"
    )

    ps = info.get(
        "priceToSalesTrailing12Months"
    )

    values = []

    if pe is not None:
        values.append(
            f"P/E {pe:.2f}"
        )

    if forward_pe is not None:
        values.append(
            f"Forward P/E {forward_pe:.2f}"
        )

    if peg is not None:
        values.append(
            f"PEG {peg:.2f}"
        )

    if ps is not None:
        values.append(
            f"P/S {ps:.2f}"
        )

    if not values:

        return result(
            "UNAVAILABLE",
            None,
            "No reliable valuation metrics returned."
        )

    # We do NOT call this a buy/sell signal.
    # Extremely high valuation is simply flagged.

    if pe is not None and pe > 50:

        return result(
            "WATCH",
            0,
            ", ".join(values)
            + ". Valuation deserves detailed review."
        )

    if peg is not None and peg > 2:

        return result(
            "WATCH",
            0,
            ", ".join(values)
            + ". PEG is relatively high; review assumptions."
        )

    return result(
        "PASS",
        1,
        ", ".join(values)
        + ". No extreme valuation flag from these metrics."
    )


# ============================================================
# RED FLAGS
# ============================================================

def check_red_flags(
    info,
    financials,
    cashflow,
    balance
):

    flags = []

    # EPS
    eps = info.get(
        "trailingEps"
    )

    if eps is not None:

        if eps < 0:
            flags.append(
                "Negative EPS"
            )

    # Revenue
    revenue = get_statement_row(
        financials,
        [
            "Total Revenue",
            "Operating Revenue"
        ]
    )

    if revenue is not None and len(revenue) >= 3:

        growth = revenue.pct_change().dropna()

        if (
            (growth < 0).sum()
            >= 2
        ):

            flags.append(
                "Revenue declined in multiple periods"
            )

    # Profit
    profit = get_statement_row(
        financials,
        [
            "Net Income",
            "Net Income Common Stockholders"
        ]
    )

    if profit is not None and len(profit) >= 3:

        growth = profit.pct_change().dropna()

        if (
            (growth < 0).sum()
            >= 2
        ):

            flags.append(
                "Profit declined in multiple periods"
            )

    # Free cash flow
    fcf = get_statement_row(
        cashflow,
        [
            "Free Cash Flow"
        ]
    )

    if fcf is not None:

        recent = fcf.iloc[
            :min(4, len(fcf))
        ]

        if (
            (recent < 0).sum()
            >= 2
        ):

            flags.append(
                "Negative free cash flow in multiple periods"
            )

    # Debt
    debt = get_statement_row(
        balance,
        [
            "Total Debt"
        ]
    )

    if debt is not None and len(debt) >= 2:

        if debt.iloc[0] > debt.iloc[-1] * 1.5:

            flags.append(
                "Debt increased materially"
            )

    if not flags:

        return result(
            "PASS",
            1,
            "No major automated red flag detected."
        )

    return result(
        "RED FLAG",
        0,
        "; ".join(flags)
    )


# ============================================================
# DISPLAY
# ============================================================

def display_check(
    title,
    data
):

    status = data["status"]

    if status == "PASS":

        icon = "🟢"

    elif status == "WATCH":

        icon = "🟡"

    elif status == "RED FLAG":

        icon = "🔴"

    elif status == "VERIFY":

        icon = "🔵"

    else:

        icon = "⚪"

    st.markdown(
        f"### {icon} {title}"
    )

    st.write(
        data["message"]
    )

    st.caption(
        f"Source: {data['source']}"
    )

    st.divider()


# ============================================================
# RUN
# ============================================================

if check_button:

    if not stock_input.strip():

        st.warning(
            "Please enter a stock name or NSE symbol."
        )

        st.stop()

    symbol = clean_symbol(
        stock_input
    )

    with st.spinner(
        f"Collecting data for {symbol}..."
    ):

        data = get_yahoo_data(
            symbol
        )

    info = data["info"]

    financials = data["financials"]

    balance = data["balance"]

    cashflow = data["cashflow"]

    ticker = data["ticker"]

    if not info:

        st.error(
            "Yahoo Finance did not return information "
            f"for {symbol}."
        )

        st.write(
            "Try the NSE symbol, for example:"
        )

        st.code(
            "TATAELXSI"
        )

        st.stop()

    company_name = info.get(
        "longName",
        symbol
    )

    st.success(
        f"Data found: {company_name}"
    )

    st.header(
        company_name
    )

    st.caption(
        f"NSE Symbol: {symbol}"
    )

    # --------------------------------------------------------
    # OPTIONAL BASIC INFORMATION
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    market_cap = info.get(
        "marketCap"
    )

    price = info.get(
        "currentPrice"
    )

    pe = info.get(
        "trailingPE"
    )

    with col1:

        if market_cap:

            st.metric(
                "Market Cap",
                f"₹{market_cap / 1e7:,.0f} Cr"
            )

    with col2:

        if price:

            st.metric(
                "Price",
                f"₹{price:,.2f}"
            )

    with col3:

        if pe:

            st.metric(
                "P/E",
                f"{pe:.2f}"
            )

    st.divider()

    # --------------------------------------------------------
    # RUN CHECKS
    # --------------------------------------------------------

    checks = {}

    checks[
        "1. Promoter Pledge"
    ] = check_promoter_pledge(
        company_name,
        symbol
    )

    checks[
        "2. Cash Flow vs Profit"
    ] = check_cash_flow_vs_profit(
        financials,
        cashflow
    )

    checks[
        "3. ROCE Consistency"
    ] = check_roce_consistency(
        financials,
        balance
    )

    checks[
        "4. Debt Trend"
    ] = check_debt_trend(
        balance
    )

    checks[
        "5. Sales Consistency"
    ] = check_sales_consistency(
        financials
    )

    checks[
        "6. Profit Consistency"
    ] = check_profit_consistency(
        financials
    )

    checks[
        "7. Valuation"
    ] = check_valuation(
        info
    )

    checks[
        "8. Possible Red Flags"
    ] = check_red_flags(
        info,
        financials,
        cashflow,
        balance
    )

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    st.subheader(
        "Stage 2 Quality Checks"
    )

    total_score = 0
    total_available = 0

    for title, data in checks.items():

        display_check(
            title,
            data
        )

        if data["score"] is not None:

            total_available += 1

            total_score += data["score"]

    # --------------------------------------------------------
    # FINAL SCORE
    # --------------------------------------------------------

    st.subheader(
        "⭐ Quality Score"
    )

    if total_available:

        percentage = (
            total_score
            / total_available
        ) * 100

        st.markdown(
            f"""
            <div class="score-box">

            <h2>
            {star_string(total_score, total_available)}
            </h2>

            <h3>
            {total_score} / {total_available}
            </h3>

            <p>
            Data coverage: {percentage:.0f}%
            </p>

            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.warning(
            "Not enough data to calculate a score."
        )

    # --------------------------------------------------------
    # INTERPRETATION
    # --------------------------------------------------------

    st.subheader(
        "📋 How to read the result"
    )

    st.write(
        """
        🟢 PASS — the available data supports the check.

        🟡 WATCH — the metric needs additional research.

        🔴 RED FLAG — the available data identifies a
        potential issue that deserves investigation.

        🔵 VERIFY — a secondary web source was located,
        but the value should be checked against the latest
        company filing.

        ⚪ UNAVAILABLE — reliable data was not obtained.
        No assumption is made.
        """
    )

    st.warning(
        "This tool is a research aid, not a buy/sell "
        "recommendation. Financial data can be delayed, "
        "incomplete, or differently defined across sources."
    )
