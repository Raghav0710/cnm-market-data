"""Fetch the latest daily close for the CNM index board and write indices.json.

Nifty 50, Sensex, Bank Nifty and Nifty Midcap 100 come from Yahoo Finance's public
chart endpoint (end-of-day). GIFT Nifty is not on Yahoo, so its entry is kept from the
existing file (it is updated separately) and only replaced if a value is supplied.
Standard library only, so it runs on a bare GitHub Actions runner.
"""
import json, os, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "indices.json")
BOARD = [  # (display name, Yahoo symbol)
    ("NIFTY 50", "^NSEI"),
    ("SENSEX", "^BSESN"),
    ("BANK NIFTY", "^NSEBANK"),
    ("NIFTY MIDCAP 100", "NIFTY_MIDCAP_100.NS|^CNXMIDCAP"),  # alternates tried in order
]

def _chart(symbol, rng):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(symbol) + "?range=" + rng + "&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (cnm-market-data)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)["chart"]["result"][0]
        except Exception:  # rate limits / transient errors
            if attempt == 3: raise
            time.sleep(5 * (attempt + 1))

def _one(symbol):
    res = _chart(symbol, "10d")
    meta = res.get("meta") or {}
    pts = [(t, c) for t, c in zip(res.get("timestamp") or [], (res.get("indicators", {}).get("quote") or [{}])[0].get("close") or []) if c is not None]
    cand = []
    if len(pts) >= 2:
        (t0, prev), (t1, last) = pts[-2], pts[-1]
        cand.append((t1, last, prev))
    # Yahoo sometimes drops the newest daily bar; the summary price is often fresher. Use whichever is newer.
    mt, mp = meta.get("regularMarketTime"), meta.get("regularMarketPrice")
    if mt and mp:
        mday = datetime.fromtimestamp(mt, IST).date()
        prior = [c for t, c in pts if datetime.fromtimestamp(t, IST).date() < mday]
        mprev = prior[-1] if prior else (meta.get("chartPreviousClose") or meta.get("previousClose"))
        if mprev: cand.append((mt, mp, mprev))
    if not cand:
        raise ValueError("no usable price")
    t1, last, prev = max(cand, key=lambda c: c[0])
    day = datetime.fromtimestamp(t1, IST)
    change = round(last - prev, 2)
    return {"value": round(last, 2), "change": change,
            "pct": round(change / prev * 100, 2), "date": day.strftime("%d %b %Y")}

def fetch(symbols):
    err = None
    for sym in symbols.split("|"):
        try:
            return _one(sym)
        except Exception as e:
            err = e
            print(f"WARN {sym}: {e}", file=sys.stderr)
    raise err

def main():
    old = {}
    if os.path.exists(OUT):
        with open(OUT) as f:
            old = json.load(f)
    old_by_name = {x["name"]: x for x in old.get("indices", [])}
    rows, dates = [], []
    for name, sym in BOARD:
        try:
            d = fetch(sym)
            prev = old_by_name.get(name)
            if prev and datetime.strptime(d["date"], "%d %b %Y") < datetime.strptime(prev["date"], "%d %b %Y"):
                # never move a close backwards in time (stale feed); keep the newer stored value
                print(f"WARN {name}: feed returned {d['date']}, keeping {prev['date']}", file=sys.stderr)
                rows.append(prev); dates.append(prev["date"])
            else:
                rows.append({"name": name, **d}); dates.append(d["date"])
        except Exception as e:
            print(f"WARN {name}: {e}", file=sys.stderr)
            if name in old_by_name: rows.append(old_by_name[name])
    # GIFT NIFTY lives in gift.json (updated each morning by a separate job); fall back to the old entry.
    gift = old_by_name.get("GIFT NIFTY")
    gpath = os.path.join(os.path.dirname(OUT), "gift.json")
    if os.path.exists(gpath):
        try:
            with open(gpath) as f:
                gift = {"name": "GIFT NIFTY", **{k: v for k, v in json.load(f).items() if k != "name"}}
        except Exception as e:
            print(f"WARN gift.json: {e}", file=sys.stderr)
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
