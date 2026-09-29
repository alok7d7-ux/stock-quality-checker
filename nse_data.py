import requests
import pandas as pd
import re
from bs4 import BeautifulSoup


NSE_HOME = "https://www.nseindia.com"

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36",
    "Accept":
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language":
        "en-US,en;q=0.9",
    "Connection":
        "keep-alive",
}


def create_session():

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    try:

        session.get(
            NSE_HOME,
            timeout=15
        )

    except Exception:
        pass

    return session


def get_nse_quote(symbol):

    session = create_session()

    url = (
        NSE_HOME
        + "/api/quote-equity?symbol="
        + symbol
    )

    try:

        response = session.get(
            url,
            timeout=15
        )

        if response.status_code != 200:
            return None

        return response.json()

    except Exception:

        return None


def get_shareholding_page(symbol):

    url = (
        NSE_HOME
        + "/companies-listing/"
        + "corporate-filings-shareholding-pattern"
        + "?symbol="
        + symbol
        + "&tabIndex=equity"
    )

    session = create_session()

    try:

        response = session.get(
            url,
            timeout=20
        )

        if response.status_code != 200:
            return None

        return response.text

    except Exception:

        return None


def parse_promoter_history(html):

    if not html:
        return []

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    text = soup.get_text(
        " ",
        strip=True
    )

    results = []

    # Look for percentage values and dates.
    # NSE's page can change its HTML structure,
    # therefore this parser is deliberately conservative.

    pattern = re.compile(
        r"Promoter\s*&\s*Promoter\s*Group.*?"
        r"(\d+(?:\.\d+)?)"
        r".{0,250}?"
        r"(\d{2}-[A-Z]{3}-\d{4})",
        re.IGNORECASE
    )

    matches = pattern.findall(
        text
    )

    for percentage, date in matches:

        results.append({
            "promoter_holding": float(
                percentage
            ),
            "date": date
        })

    return results


def get_promoter_data(symbol):

    html = get_shareholding_page(
        symbol
    )

    history = parse_promoter_history(
        html
    )

    if not history:

        return {
            "status": "UNAVAILABLE",
            "data": None,
            "source":
                "NSE Shareholding Pattern"
        }

    latest = history[0]

    return {
        "status": "AVAILABLE",
        "data": latest,
        "history": history,
        "source":
            "NSE Shareholding Pattern"
    }
