# QQQ Signal

A bookmarkable daily TQQQ / TLT signal and a plain-language explanation of the published three-gate rule and taxable deferral exception.

The signal uses QQQ ETF daily closes, sample standard deviation, 20/250-session windows, a 35% annualized volatility limit, a 1.10 shock limit, and the 20%/10% drawdown state. A combined verdict needs two consecutive sessions. Allocation changes use the following session's open.

The deferral explanation retains all three AND conditions from the source. The page does not read brokerage holdings. It publishes the base market signal and explains how an existing TQQQ purchase may qualify for deferral.

## Hosting and updates

GitHub Pages serves `public/`. GitHub Actions refreshes closing data hourly at minute 43 from 20:00–23:59 UTC on weekdays and 00:00–03:59 UTC Tuesday–Saturday. Each run saves its data snapshot and publishes the site. Refreshing a browser reads the latest published snapshot.

The exchange calendar handles holidays, early closes and daylight-saving time. An additional 15-minute settlement buffer excludes an in-progress or just-closed bar. Missing recent sessions and regressing history are rejected. A provider failure preserves the last successful deployment, and the page independently checks its dated snapshot against the calendar before presenting it as fresh.

## Local checks

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
node --test tests/*.test.mjs
python scripts/refresh.py
python -m http.server --directory public 8765
```

## Sources

- [Original whitepaper](https://willperryyy.github.io/tqqq-gate/whitepaper.html)
- [TQQQ](https://www.proshares.com/our-etfs/leveraged-and-inverse/tqqq)
- [TLT](https://www.ishares.com/us/products/239454/ishares-20-year-treasury-bond-etf)
- [Exchange calendars](https://github.com/gerrymanoim/exchange_calendars)

Market data and scheduled jobs can be delayed. Use the date and freshness status displayed on the page. Historical loss figures are attributed to the linked paper and its T-bill assumptions.

The active QQQ feed is `public/qqq-data.json`. The legacy `data.json` is a frozen NDX snapshot retained for older page versions; current pages do not use it.
