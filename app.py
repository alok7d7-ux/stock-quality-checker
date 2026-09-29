import streamlit as st
import yfinance as yf

from quality_engine import (
    check_cashflow_profit,
    check_sales_consistency,
    check_profit_consistency,
    check_debt_trend,
    check_roce,
    check_valuation,
    check_red_flags
)

from nse_data import (
    get_nse_quote,
    get_promoter_data
)


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Indian Stock Quality Checker",
    page_icon="⭐",
    layout="centered"
)

st.title(
    "⭐ Indian Stock Quality Checker"
)

st.caption(
    "Stage 2 — Quality & Red-Flag Analysis"
)

st.info(
    "Enter a stock that has already passed "
    "your Stage-1 Screener scan."
)


# ============================================================
# INPUT
# ============================================================

symbol_input = st.text_input(
    "NSE Symbol",
    placeholder="Example: TATAELXSI"
)

check = st.button(
    "🔍 CHECK STOCK",
    use_container_width=True
)


# ============================================================
# FUNCTIONS
# ============================================================

def normalize_symbol(symbol):

    symbol = (
        symbol
        .strip()
        .upper()
    )

    if symbol.endswith(".NS"):

        symbol = symbol[:-3]

    return symbol


def status_icon(status):

    icons = {
        "PASS": "🟢",
        "WATCH": "🟡",
        "RED FLAG": "🔴",
        "AVAILABLE": "🔵",
        "VERIFY": "🔵",
        "UNAVAILABLE": "⚪"
    }

    return icons.get(
        status,
        "⚪"
    )


def show_check(
    title,
    data
):

    status = data["status"]

    st.subheader(
        f"{status_icon(status)} {title}"
    )

    st.write(
        data["message"]
    )

    st.caption(
        "Source: "
        + data.get(
            "source",
            "Financial data"
        )
    )


# ============================================================
# MAIN
# ============================================================

if check:

    if not symbol_input.strip():

        st.warning(
            "Enter an NSE stock symbol."
        )

        st.stop()

    symbol = normalize_symbol(
        symbol_input
    )

    yahoo_symbol = (
        symbol + ".NS"
    )

    # --------------------------------------------------------
    # YAHOO
    # --------------------------------------------------------

    with st.spinner(
        "Collecting financial data..."
    ):

        try:

            stock = yf.Ticker(
                yahoo_symbol
            )

            info = stock.info

            financials = (
                stock.financials
            )

            balance = (
                stock.balance_sheet
            )

            cashflow = (
                stock.cashflow
            )

        except Exception as e:

            st.error(
                "Unable to retrieve financial data."
            )

            st.code(
                str(e)
            )

            st.stop()

    if not info:

        st.error(
            "No Yahoo Finance data found."
        )

        st.stop()

    company_name = info.get(
        "longName",
        symbol
    )

    st.header(
        company_name
    )

    st.caption(
        f"NSE: {symbol}"
    )

    # --------------------------------------------------------
    # NSE QUOTE
    # --------------------------------------------------------

    with st.spinner(
        "Checking NSE data..."
    ):

        nse_quote = get_nse_quote(
            symbol
        )

        promoter = get_promoter_data(
            symbol
        )

    # --------------------------------------------------------
    # BASIC DATA
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    price = info.get(
        "currentPrice"
    )

    market_cap = info.get(
        "marketCap"
    )

    pe = info.get(
        "trailingPE"
    )

    with col1:

        if price:

            st.metric(
                "Price",
                f"₹{price:,.2f}"
            )

    with col2:

        if market_cap:

            st.metric(
                "Market Cap",
                f"₹{market_cap / 1e7:,.0f} Cr"
            )

    with col3:

        if pe:

            st.metric(
                "P/E",
                f"{pe:.2f}"
            )

    st.divider()

    # ========================================================
    # STAGE 2
    # ========================================================

    st.header(
        "Stage 2 — Quality Checks"
    )

    score = 0
    available = 0

    # --------------------------------------------------------
    # 1 PROMOTER
    # --------------------------------------------------------

    st.subheader(
        "1️⃣ Promoter Holding / Pledge"
    )

    if promoter["status"] == "AVAILABLE":

        holding = promoter["data"][
            "promoter_holding"
        ]

        date = promoter["data"][
            "date"
        ]

        st.success(
            f"Promoter holding: {holding:.2f}%"
        )

        st.caption(
            f"As of {date} | Source: NSE"
        )

        # We do NOT treat promoter holding as
        # promoter pledge.

        st.info(
            "Promoter holding is available from NSE. "
            "Promoter pledge must be verified from "
            "the detailed shareholding disclosure."
        )

    else:

        st.warning(
            "NSE promoter data could not be extracted."
        )

    st.divider()

    # --------------------------------------------------------
    # 2 CASH FLOW
    # --------------------------------------------------------

    data = check_cashflow_profit(
        financials,
        cashflow
    )

    show_check(
        "2️⃣ Cash Flow vs Profit",
        data
    )

    if data["score"] is not None:

        available += 1
        score += data["score"]

    # --------------------------------------------------------
    # 3 ROCE
    # --------------------------------------------------------

    data = check_roce(
        financials,
        balance
    )

    show_check(
        "3️⃣ ROCE Consistency",
        data
    )

    if data["score"] is not None:

        available += 1
        score += data["score"]

    # --------------------------------------------------------
    # 4 DEBT
    # --------------------------------------------------------

    data = check_debt_trend(
        balance
    )

    show_check(
        "4️⃣ Debt Trend",
        data
    )

    if data["score"] is not None:

        available += 1
        score += data["score"]

    # --------------------------------------------------------
    # 5 SALES
    # --------------------------------------------------------

    data = check_sales_consistency(
        financials
    )

    show_check(
        "5️⃣ Sales Consistency",
        data
    )

    if data["score"] is not None:

        available += 1
        score += data["score"]

    # --------------------------------------------------------
    # 6 PROFIT
    # --------------------------------------------------------

    data = check_profit_consistency(
        financials
    )

    show_check(
        "6️⃣ Profit Consistency",
        data
    )

    if data["score"] is not None:

        available += 1
        score += data["score"]

    # --------------------------------------------------------
    # 7 VALUATION
    # --------------------------------------------------------

    data = check_valuation(
        info
    )

    show_check(
        "7️⃣ Valuation",
        data
    )

    if data["score"] is not None:

        available += 1
        score += data["score"]

    # --------------------------------------------------------
    # 8 RED FLAGS
    # --------------------------------------------------------

    data = check_red_flags(
        info,
        financials,
        cashflow,
        balance
    )

    show_check(
        "8️⃣ Possible Red Flags",
        data
    )

    if data["score"] is not None:

        available += 1
        score += data["score"]

    # ========================================================
    # FINAL SCORE
    # ========================================================

    st.header(
        "⭐ Stage-2 Score"
    )

    if available > 0:

        percentage = (
            score / available
        ) * 100

        full_stars = int(
            round(
                score / available * 8
            )
        )

        empty_stars = (
            8 - full_stars
        )

        if empty_stars < 0:
            empty_stars = 0

        stars = (
            "⭐" * full_stars
            + "☆" * empty_stars
        )

        st.markdown(
            f"""
            ## {stars}

            ### {score:.1f} / {available}

            Data coverage: {percentage:.0f}%
            """
        )

    else:

        st.warning(
            "Insufficient data to calculate score."
        )

    # ========================================================
    # SOURCES
    # ========================================================

    st.header(
        "📚 Data Sources"
    )

    st.write(
        """
        • NSE India — corporate filings

        • NSE India — shareholding pattern

        • Yahoo Finance — supporting market/financial data

        • Company official filings — to be used for
          detailed verification
        """
    )

    st.warning(
        "This application is a research tool. "
        "It does not provide a buy/sell recommendation. "
        "Always verify important figures against the "
        "latest company filing."
    )


