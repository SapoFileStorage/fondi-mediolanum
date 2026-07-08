#!/usr/bin/env python3
"""
Scarica lo storico NAV dei fondi Mediolanum dai dati fondi del Financial Times
(markets.ft.com) e lo salva in data/nav_history.csv (formato: date,isin,nav).

Uso:  python fetch_nav.py
Nessuna dipendenza esterna: usa solo la libreria standard.
"""

import csv
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------- fondi ----
FUNDS = {
    "IE0004460683": "Challenge Energy Opportunities LA EUR",
    "IE0004488262": "Challenge Financial Opportunities LA EUR",
    "IE0004479642": "Challenge Healthcare Opportunities LA EUR",
    "IE0004462408": "Challenge Industrials and Materials Opportunities LA EUR",
    "IE0004621052": "Challenge Technology Opportunities LA EUR",
}

HISTORY_DAYS = 3650          # profondità dello storico richiesto (~10 anni)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HISTORY_CSV = DATA_DIR / "nav_history.csv"
IDS_CACHE = DATA_DIR / "ft_ids.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://markets.ft.com/data/funds",
}


def http(url: str, payload: dict | None = None) -> tuple[int, str]:
    """GET (o POST json se payload è presente). Ritorna (status, body)."""
    data = None
    headers = dict(HEADERS)
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def ft_search_xid(isin: str) -> str | None:
    """Cerca il titolo su FT e ritorna il suo xid interno."""
    url = ("https://markets.ft.com/data/searchapi/searchsecurities?query="
           + urllib.parse.quote(isin))
    status, body = http(url)
    if status != 200:
        print(f"  [!] Ricerca FT fallita (HTTP {status}): {body[:200]}")
        return None
    try:
        results = json.loads(body).get("data", {}).get("security", [])
    except json.JSONDecodeError:
        print(f"  [!] Risposta di ricerca non in JSON: {body[:200]}")
        return None
    if not results:
        print("  [!] Nessun risultato per questo ISIN su FT.")
        return None
    # se ci sono più classi/valute, preferisci quella in EUR
    best = next((r for r in results
                 if "EUR" in (r.get("symbol", "") + r.get("currency", ""))),
                results[0])
    xid = best.get("xid")
    if not xid:
        print(f"  [!] Risultato senza xid: {json.dumps(best)[:200]}")
        return None
    print(f"  trovato: {best.get('name', '?')} ({best.get('symbol', '?')})")
    return str(xid)


def ft_timeseries(xid: str) -> list[tuple[str, float]]:
    """Scarica la serie storica dei NAV. Ritorna [(YYYY-MM-DD, nav), ...]."""
    payload = {
        "days": HISTORY_DAYS,
        "dataNormalized": False,
        "dataPeriod": "Day",
        "dataInterval": 1,
        "realtime": False,
        "returnDateType": "ISO8601",
        "elements": [{"Label": "nav", "Type": "price", "Symbol": xid,
                      "OverlayIndicators": [], "Params": {}}],
    }
    status, body = http("https://markets.ft.com/data/chartapi/series", payload)
    if status != 200:
        print(f"  [!] Serie storica fallita (HTTP {status}): {body[:200]}")
        return []
    try:
        data = json.loads(body)
        dates = data["Dates"]
        comp = data["Elements"][0]["ComponentSeries"]
        closes = next(c["Values"] for c in comp if c.get("Type") == "Close")
    except (KeyError, IndexError, StopIteration, json.JSONDecodeError) as exc:
        print(f"  [!] Formato risposta inatteso ({exc}): {body[:200]}")
        return []
    series = []
    for day, value in zip(dates, closes):
        if value is None:
            continue
        series.append((str(day)[:10], float(value)))
    return series


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)

    # cache degli xid FT per non rifare la ricerca ogni volta
    ids: dict[str, str] = {}
    if IDS_CACHE.exists():
        ids = json.loads(IDS_CACHE.read_text())

    all_rows: list[tuple[str, str, float]] = []
    errors = 0

    for isin, name in FUNDS.items():
        print(f"* {name} ({isin})")
        xid = ids.get(isin) or ft_search_xid(isin)
        if not xid:
            errors += 1
            continue
        ids[isin] = xid

        series = ft_timeseries(xid)
        if not series:
            errors += 1
            continue
        print(f"  ok: {len(series)} punti, ultimo {series[-1][0]} -> {series[-1][1]}")
        all_rows.extend((day, isin, nav) for day, nav in series)

    IDS_CACHE.write_text(json.dumps(ids, indent=2))

    if not all_rows:
        print("Nessun dato scaricato: nav_history.csv non modificato.")
        return 1

    # Se qualche fondo è fallito, conserviamo i suoi dati precedenti.
    fetched_isins = {r[1] for r in all_rows}
    if HISTORY_CSV.exists():
        with HISTORY_CSV.open(newline="") as fh:
            for row in csv.DictReader(fh):
                if row["isin"] not in fetched_isins:
                    all_rows.append((row["date"], row["isin"], float(row["nav"])))

    all_rows.sort(key=lambda r: (r[1], r[0]))
    with HISTORY_CSV.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["date", "isin", "nav"])
        for day, isin, nav in all_rows:
            writer.writerow([day, isin, f"{nav:.4f}"])

    print(f"Scritti {len(all_rows)} record in {HISTORY_CSV}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
