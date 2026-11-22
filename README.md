# cnm-market-data
Daily closing levels for the index board on the CNM Securities website.
`indices.json` is refreshed after market close every weekday by `.github/workflows/update.yml`
(Nifty 50, Sensex, Bank Nifty, Nifty Midcap 100 from Yahoo Finance end-of-day data).
GIFT Nifty is written to `gift.json` each morning and merged in by `.github/workflows/gift.yml`. Data is for information only.
