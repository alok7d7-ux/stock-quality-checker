import numpy as np
import pandas as pd


def get_row(df, names):

    if df is None or df.empty:
        return None

    for name in names:

        if name in df.index:

            values = pd.to_numeric(
                df.loc[name],
                errors="coerce"
            ).dropna()

            if len(values) > 0:
                return values

    return None


def check_cashflow_profit(financials, cashflow):

    profit = get_row(
        financials,
        [
            "Net Income",
            "Net Income Common Stockholders"
        ]
    )

    cfo = get_row(
        cashflow,
        [
            "Operating Cash Flow",
            "Total Cash From Operating Activities"
        ]
    )

    if profit is None or cfo is None:
        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Cash-flow/profit data unavailable."
        }

    n = min(len(profit), len(cfo))

    ratios = []

    for i in range(n):

        if abs(profit.iloc[i]) > 0:

            ratios.append(
                cfo.iloc[i] / profit.iloc[i]
            )

    if len(ratios) < 2:

        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Not enough historical data."
        }

    avg = np.mean(ratios)

    if avg >= 0.80:

        return {
            "status": "PASS",
            "score": 1,
            "message":
                f"Average CFO/PAT ≈ {avg:.2f}x"
        }

    elif avg >= 0.50:

        return {
            "status": "WATCH",
            "score": 0.5,
            "message":
                f"Average CFO/PAT ≈ {avg:.2f}x"
        }

    return {
        "status": "RED FLAG",
        "score": 0,
        "message":
            f"Average CFO/PAT ≈ {avg:.2f}x"
    }


def check_sales_consistency(financials):

    revenue = get_row(
        financials,
        [
            "Total Revenue",
            "Operating Revenue"
        ]
    )

    if revenue is None or len(revenue) < 3:

        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Revenue history unavailable."
        }

    growth = revenue.pct_change().dropna()

    positive = int(
        (growth > 0).sum()
    )

    if positive >= 3:

        return {
            "status": "PASS",
            "score": 1,
            "message":
                "Revenue increased in most available periods."
        }

    if positive >= 2:

        return {
            "status": "WATCH",
            "score": 0.5,
            "message":
                "Revenue growth is somewhat inconsistent."
        }

    return {
        "status": "RED FLAG",
        "score": 0,
        "message":
            "Revenue declined repeatedly."
    }


def check_profit_consistency(financials):

    profit = get_row(
        financials,
        [
            "Net Income",
            "Net Income Common Stockholders"
        ]
    )

    if profit is None or len(profit) < 3:

        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Profit history unavailable."
        }

    growth = profit.pct_change().dropna()

    positive = int(
        (growth > 0).sum()
    )

    if positive >= 3:

        return {
            "status": "PASS",
            "score": 1,
            "message":
                "Profit increased in most available periods."
        }

    if positive >= 2:

        return {
            "status": "WATCH",
            "score": 0.5,
            "message":
                "Profit growth is somewhat inconsistent."
        }

    return {
        "status": "RED FLAG",
        "score": 0,
        "message":
            "Profit declined repeatedly."
    }


def check_debt_trend(balance):

    debt = get_row(
        balance,
        [
            "Total Debt",
            "Long Term Debt"
        ]
    )

    if debt is None or len(debt) < 2:

        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message": "Debt history unavailable."
        }

    newest = debt.iloc[0]
    oldest = debt.iloc[-1]

    if newest < oldest:

        return {
            "status": "PASS",
            "score": 1,
            "message":
                "Debt has declined over the available period."
        }

    increase = (
        (newest - oldest)
        / max(abs(oldest), 1)
    )

    if increase <= 0.10:

        return {
            "status": "WATCH",
            "score": 0.5,
            "message":
                "Debt is broadly stable."
        }

    return {
        "status": "RED FLAG",
        "score": 0,
        "message":
            "Debt has increased materially."
    }


def check_roce(financials, balance):

    ebit = get_row(
        financials,
        [
            "EBIT",
            "Operating Income"
        ]
    )

    assets = get_row(
        balance,
        [
            "Total Assets"
        ]
    )

    liabilities = get_row(
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

        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message":
                "Cannot calculate ROCE from available statements."
        }

    n = min(
        len(ebit),
        len(assets),
        len(liabilities)
    )

    values = []

    for i in range(n):

        capital = (
            assets.iloc[i]
            - liabilities.iloc[i]
        )

        if capital > 0:

            roce = (
                ebit.iloc[i]
                / capital
            ) * 100

            values.append(roce)

    if len(values) < 3:

        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message":
                "Not enough ROCE history."
        }

    recent = values[:5]

    strong = sum(
        x >= 15
        for x in recent
    )

    if strong >= 4:

        return {
            "status": "PASS",
            "score": 1,
            "message":
                "ROCE has remained relatively strong."
        }

    if strong >= 2:

        return {
            "status": "WATCH",
            "score": 0.5,
            "message":
                "ROCE is positive but somewhat inconsistent."
        }

    return {
        "status": "RED FLAG",
        "score": 0,
        "message":
            "ROCE appears weak."
    }


def check_valuation(info):

    pe = info.get("trailingPE")
    peg = info.get("pegRatio")

    values = []

    if pe is not None:
        values.append(f"P/E {pe:.2f}")

    if peg is not None:
        values.append(f"PEG {peg:.2f}")

    if not values:

        return {
            "status": "UNAVAILABLE",
            "score": None,
            "message":
                "Valuation data unavailable."
        }

    if pe is not None and pe > 50:

        return {
            "status": "WATCH",
            "score": 0.5,
            "message":
                ", ".join(values)
                + " — valuation deserves review."
        }

    if peg is not None and peg > 2:

        return {
            "status": "WATCH",
            "score": 0.5,
            "message":
                ", ".join(values)
                + " — PEG deserves review."
        }

    return {
        "status": "PASS",
        "score": 1,
        "message":
            ", ".join(values)
    }


def check_red_flags(
    info,
    financials,
    cashflow,
    balance
):

    flags = []

    eps = info.get("trailingEps")

    if eps is not None and eps < 0:

        flags.append(
            "Negative EPS"
        )

    revenue = get_row(
        financials,
        [
            "Total Revenue",
            "Operating Revenue"
        ]
    )

    if revenue is not None and len(revenue) >= 3:

        growth = revenue.pct_change().dropna()

        if (growth < 0).sum() >= 2:

            flags.append(
                "Repeated revenue decline"
            )

    profit = get_row(
        financials,
        [
            "Net Income",
            "Net Income Common Stockholders"
        ]
    )

    if profit is not None and len(profit) >= 3:

        growth = profit.pct_change().dropna()

        if (growth < 0).sum() >= 2:

            flags.append(
                "Repeated profit decline"
            )

    fcf = get_row(
        cashflow,
        [
            "Free Cash Flow"
        ]
    )

    if fcf is not None:

        recent = fcf.iloc[
            :min(4, len(fcf))
        ]

        if (recent < 0).sum() >= 2:

            flags.append(
                "Negative FCF in multiple periods"
            )

    if not flags:

        return {
            "status": "PASS",
            "score": 1,
            "message":
                "No major automated red flag detected."
        }

    return {
        "status": "RED FLAG",
        "score": 0,
        "message":
            "; ".join(flags)
    }
