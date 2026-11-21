"""Fetch the latest daily close for the CNM index board and write indices.json.

Nifty 50, Sensex, Bank Nifty and Nifty Midcap 100 come from Yahoo Finance's public
chart endpoint (end-of-day). GIFT Nifty is not on Yahoo, so its entry is kept from the
existing file (it is updated separately) and only replaced if a value is supplied.
Standard library only, so it runs on a bare GitHub Actions runner.
"""
import json, os, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "indices.json")
BOARD = [  # (display name, Yahoo symbol)
    ("NIFTY 50", "^NSEI"),
    ("SENSEX", "^BSESN"),
    ("BANK NIFTY", "^NSEBANK"),
    ("NIFTY MIDCAP 100", "NIFTY_MIDCAP_100.NS"),
]

def fetch(symbol):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(symbol) + "?range=10d&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (cnm-market-data)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                res = json.load(r)["chart"]["result"][0]
            break
        except Exception as e:  # rate limits / transient errors
            if attempt == 3: raise
            time.sleep(5 * (attempt + 1))
    pts = [(t, c) for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]) if c is not None]
    (t0, prev), (t1, last) = pts[-2], pts[-1]
    # Ignore today's partial bar if the market is still open (run happens after close anyway).
    day = datetime.fromtimestamp(t1, IST)
    change = round(last - prev, 2)
    return {"value": round(last, 2), "change": change,
            "pct": round(change / prev * 100, 2), "date": day.strftime("%d %b %Y")}

def main():
    import urllib.parse  # noqa: F401 (used in fetch)
    old = {}
    if os.path.exists(OUT):
        with open(OUT) as f:
            old = json.load(f)
    old_by_name = {x["name"]: x for x in old.get("indices", [])}
    rows, dates = [], []
    for name, sym in BOARD:
        try:
            d = fetch(sym)
            rows.append({"name": name, **d}); dates.append(d["date"])
        except Exception as e:
            print(f"WARN {name}: {e}", file=sys.stderr)
            if name in old_by_name: rows.append(old_by_name[name])
    gift = old_by_name.get("GIFT NIFTY")
    if gift: rows.append(gift)
    if not rows: sys.exit("no data")
    as_of = max(dates, key=lambda s: datetime.strptime(s, "%d %b %Y")) if dates else old.get("asOf")
    data = {"asOf": as_of, "updated": datetime.now(IST).strftime("%d %b %Y %H:%M IST"), "indices": rows}
    with open(OUT, "w") as f:
        json.dump(data, f, indent=1)
    print(json.dumps(data, indent=1))

if __name__ == "__main__":
    import urllib.parse
    main()
