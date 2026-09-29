import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Stock Quality Checker",
    page_icon="⭐",
    layout="centered"
)

st.title("⭐ Stock Quality Checker")
st.caption("Stage 2 — Fundamental Quality Analysis")

st.info(
    "Enter a stock that has already passed your Screener.in Stage-1 scan."
)

ticker_input = st.text_input(
    "Enter NSE stock symbol",
    placeholder="Example: TATAELXSI"
)

check_button = st.button(
    "🔍 CHECK STOCK",
    use_container_width=True
)


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def clean_number(value):
    try:
        return float(value)
    except:
        return np.nan


def stars(n):
    return "⭐" * n + "☆" * (8 - n)


def safe_pct(value):
    if pd.isna(value):
        return None
    return round(float(value), 2)


def get_statement_value(df, names):

    if df is None or df.empty:
        return None

    for name in names:

        if name in df.index:

            values = df.loc[name]

            values = pd.to_numeric(
                values,
                errors="coerce"
            ).dropna()

            if len(values) > 0:
                return values

    return None


# ---------------------------------------------------------
# QUALITY CHECKS
# ---------------------------------------------------------

def promoter_pledge_check(info):

    # Yahoo does not consistently expose promoter pledge
    # information for Indian stocks.

    possible_keys = [
        "heldPercentInsiders",
        "heldPercentInstitutions"
    ]

    for key in possible_keys:
        if key in info:
            value = info.get(key)

            if value is not None:
                return {
                    "status": "AVAILABLE",
                    "score": 1,
                    "message":
                        "Ownership information available."
                }

    return {
        "status": "UNAVAILABLE",
        "score": None,
        "message":
            "Promoter pledge data is not reliably available "
            "from Yahoo Finance."
    }


def cash_flow_vs_profit(ticker):

    cashflow = ticker.cashflow
    income = ticker.financials

    if cashflow is None or cashflow.empty:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Cash-flow data unavailable."
        }

    if income is None or income.empty:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Profit data unavailable."
        }

    cfo = get_statement_value(
        cashflow,
        [
            "Operating Cash Flow",
            "Total Cash From Operating Activities"
        ]
    )

    profit = get_statement_value(
        income,
        [
            "Net Income",
            "Net Income Common Stockholders"
        ]
    )

    if cfo is None or profit is None:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Required data unavailable."
        }

    common = min(len(cfo), len(profit))

    if common < 2:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Not enough historical data."
        }

    cfo = cfo.iloc[:common]
    profit = profit.iloc[:common]

    valid = profit.abs() > 0

    if valid.sum() < 2:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Insufficient profit data."
        }

    ratio = (
        cfo[valid].abs() /
        profit[valid].abs()
    ).mean()

    if ratio >= 0.8:
        return {
            "status": "PASS",
            "score": 1,
            "message":
                f"Average CFO/Profit ratio ≈ {ratio:.2f}"
        }

    elif ratio >= 0.5:
        return {
            "status": "WATCH",
            "score": 0,
            "message":
                f"CFO/Profit ratio ≈ {ratio:.2f}; review cash conversion."
        }

    return {
        "status": "RED FLAG",
        "score": 0,
        "message":
            f"CFO/Profit ratio ≈ {ratio:.2f}; significant mismatch."
    }


def roce_consistency(ticker):

    # Yahoo does not always provide ROCE directly.
    # We attempt a simple ROCE approximation.

    income = ticker.financials
    balance = ticker.balance_sheet

    if income is None or income.empty:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Income statement unavailable."
        }

    if balance is None or balance.empty:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Balance sheet unavailable."
        }

    ebit = get_statement_value(
        income,
        ["EBIT", "Operating Income"]
    )

    assets = get_statement_value(
        balance,
        ["Total Assets"]
    )

    liabilities = get_statement_value(
        balance,
        ["Total Liabilities Net Minority Interest"]
    )

    if ebit is None or assets is None or liabilities is None:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Cannot calculate ROCE reliably."
        }

    n = min(len(ebit), len(assets), len(liabilities))

    if n < 3:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Not enough historical data."
        }

    roce_values = []

    for i in range(n):

        capital_employed = (
            assets.iloc[i] -
            liabilities.iloc[i]
        )

        if capital_employed > 0:

            roce = (
                ebit.iloc[i] /
                capital_employed
            ) * 100

            roce_values.append(roce)

    if len(roce_values) < 3:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "ROCE could not be calculated."
        }

    recent = roce_values[:5]

    positive = sum(
        value > 15
        for value in recent
    )

    if positive >= 4:
        return {
            "status": "PASS",
            "score": 1,
            "message":
                "ROCE has remained relatively strong."
        }

    return {
        "status": "WATCH",
        "score": 0,
        "message":
            "ROCE consistency requires review."
    }


def debt_trend(ticker):

    balance = ticker.balance_sheet

    if balance is None or balance.empty:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Balance sheet unavailable."
        }

    debt = get_statement_value(
        balance,
        [
            "Total Debt",
            "Long Term Debt",
            "Net Debt"
        ]
    )

    if debt is None or len(debt) < 2:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Historical debt data unavailable."
        }

    recent = debt.iloc[:min(4, len(debt))]

    if recent.iloc[0] <= recent.iloc[-1]:
        return {
            "status": "PASS",
            "score": 1,
            "message": "Debt is stable or declining."
        }

    return {
        "status": "WATCH",
        "score": 0,
        "message": "Debt appears to be increasing."
    }


def growth_consistency(ticker):

    income = ticker.financials

    if income is None or income.empty:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Income statement unavailable."
        }

    revenue = get_statement_value(
        income,
        [
            "Total Revenue",
            "Operating Revenue"
        ]
    )

    profit = get_statement_value(
        income,
        [
            "Net Income",
            "Net Income Common Stockholders"
        ]
    )

    if revenue is None or profit is None:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Revenue/profit history unavailable."
        }

    if len(revenue) < 3 or len(profit) < 3:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Not enough history."
        }

    revenue_growth = revenue.pct_change().dropna()
    profit_growth = profit.pct_change().dropna()

    rev_positive = (revenue_growth > 0).sum()
    profit_positive = (profit_growth > 0).sum()

    if rev_positive >= 2 and profit_positive >= 2:
        return {
            "status": "PASS",
            "score": 1,
            "message":
                "Recent sales and profit trend is broadly positive."
        }

    return {
        "status": "WATCH",
        "score": 0,
        "message":
            "Sales/profit consistency requires review."
    }


def valuation_check(info):

    pe = info.get("trailingPE")
    peg = info.get("pegRatio")
    ps = info.get("priceToSalesTrailing12Months")

    available = []

    if pe is not None:
        available.append(f"P/E {pe:.2f}")

    if peg is not None:
        available.append(f"PEG {peg:.2f}")

    if ps is not None:
        available.append(f"P/S {ps:.2f}")

    if not available:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Valuation data unavailable."
        }

    # This is NOT a buy/sell valuation model.
    # It simply flags unusually high/low values for review.

    if pe is not None and pe > 50:
        return {
            "status": "WATCH",
            "score": 0,
            "message":
                ", ".join(available) +
                " — valuation deserves review."
        }

    return {
        "status": "PASS",
        "score": 1,
        "message":
            ", ".join(available)
    }


def red_flags(ticker, info):

    flags = []

    # Negative earnings
    earnings = info.get("trailingEps")

    if earnings is not None and earnings < 0:
        flags.append("Negative EPS")

    # Negative free cash flow
    cashflow = ticker.cashflow

    if cashflow is not None and not cashflow.empty:

        fcf = get_statement_value(
            cashflow,
            ["Free Cash Flow"]
        )

        if fcf is not None:

            recent = fcf.iloc[:3]

            if (recent < 0).sum() >= 2:
                flags.append(
                    "Negative free cash flow in recent periods"
                )

    # Falling revenue
    income = ticker.financials

    if income is not None and not income.empty:

        revenue = get_statement_value(
            income,
            ["Total Revenue"]
        )

        if revenue is not None and len(revenue) >= 3:

            growth = revenue.pct_change().dropna()

            if (growth < 0).sum() >= 2:
                flags.append(
                    "Revenue declined in multiple periods"
                )

    if not flags:

        return {
            "status": "PASS",
            "score": 1,
            "message": "No major automated red flag detected."
        }

    return {
        "status": "RED FLAG",
        "score": 0,
        "message": "; ".join(flags)
    }


# ---------------------------------------------------------
# MAIN APP
# ---------------------------------------------------------

if check_button:

    if not ticker_input.strip():

        st.warning("Please enter a stock symbol.")

    else:

        symbol = ticker_input.strip().upper()

        if not symbol.endswith(".NS"):
            symbol += ".NS"

        with st.spinner(
            f"Fetching data for {symbol}..."
        ):

            try:

                stock = yf.Ticker(symbol)

                info = stock.info

                if not info:

                    st.error(
                        "Yahoo Finance did not return data."
                    )
                    st.stop()

                company_name = info.get(
                    "longName",
                    symbol
                )

                st.subheader(company_name)

                st.caption(symbol)

                checks = {}

                checks[
                    "Promoter Pledge"
                ] = promoter_pledge_check(info)

                checks[
                    "Cash Flow vs Profit"
                ] = cash_flow_vs_profit(stock)

                checks[
                    "ROCE Consistency"
                ] = roce_consistency(stock)

                checks[
                    "Debt Trend"
                ] = debt_trend(stock)

                checks[
                    "Sales/Profit Consistency"
                ] = growth_consistency(stock)

                checks[
                    "Valuation"
                ] = valuation_check(info)

                checks[
                    "Possible Red Flags"
                ] = red_flags(
                    stock,
                    info
                )

                # -------------------------------------------------
                # DISPLAY CHECKS
                # -------------------------------------------------

                score = 0
                available = 0

                for name, result in checks.items():

                    status = result["status"]

                    if status == "PASS":
                        icon = "✅"

                    elif status == "WATCH":
                        icon = "⚠️"

                    elif status == "RED FLAG":
                        icon = "❌"

                    else:
                        icon = "⚪"

                    if result["score"] is not None:

                        available += 1

                        if result["score"] == 1:
                            score += 1

                    with st.container():

                        col1, col2 = st.columns(
                            [2, 1]
                        )

                        with col1:
                            st.markdown(
                                f"### {icon} {name}"
                            )

                        with col2:
                            st.markdown(
                                f"**{status}**"
                            )

                        st.write(
                            result["message"]
                        )

                        st.divider()


                # -------------------------------------------------
                # SCORE
                # -------------------------------------------------

                st.subheader(
                    "⭐ Quality Score"
                )

                if available > 0:

                    st.metric(
                        "Available Checks",
                        f"{score} / {available}"
                    )

                    st.markdown(
                        f"## {stars(score)}"
                    )

                else:

                    st.warning(
                        "Not enough Yahoo Finance data "
                        "to calculate a quality score."
                    )

                st.caption(
                    "This is a research tool, not a buy/sell recommendation. "
                    "Data availability and definitions can vary by company."
                )

            except Exception as e:

                st.error(
                    f"Unable to analyse {symbol}."
                )

                st.code(str(e))
