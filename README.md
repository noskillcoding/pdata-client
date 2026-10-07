# pdata-client

A small Python client, examples and sample data for **[pdata.world](https://pdata.world)**, a
free, read-only API for prediction-market data from eight venues: Polymarket, Kalshi,
Manifold, Myriad, Limitless, Predict, Opinion and Gemini.

pdata.world polls each venue every 10 to 60 minutes and keeps prices, 24-hour volume and
results in one schema, so one request can compare venues that otherwise each need their own
integration. There is no API key and no signup. The data is published under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): use it, and credit pdata.world.

```python
from pdata import Client

pd = Client()
page = pd.markets(source=["kalshi", "polymarket"], closed=False, sort="-volume_24hr", page_size=5)
for m in page["items"]:
    print(m["source"], f"{m['probability']:.0%}", m["event_title"], "—", m["question"])
```

## Install

```bash
pip install git+https://github.com/noskillcoding/pdata-client
```

The client uses only the standard library (`urllib`, `json`, `gzip`) and runs on Python 3.9
or later. You can also copy [`src/pdata/client.py`](src/pdata/client.py) into a project.

## What the client covers

| Method | API operation | What it returns |
|---|---|---|
| `markets(**filters)`, `iter_markets(...)` | `GET /markets` | Markets, filtered and sorted, one page or all pages |
| `market(source, id)` | `GET /markets/{source}/{id}` | One market |
| `top_movers(...)`, `closing_soon(...)` | `GET /markets/top-movers`, `/closing-soon` | Largest 24h price changes; markets closing next |
| `events(**filters)`, `iter_events(...)` | `GET /events` | Events (an event groups the markets of one question) |
| `event(source, id)` | `GET /events/{source}/{id}` | One event with its markets, or its final results once archived |
| `event_history(source, id, range=...)` | `GET /events/{source}/{id}/history` | Price and 24h-volume series, `24h` / `7d` / `30d` / `all` |
| `similar_events(source, id)` | `GET /events/{source}/{id}/similar` | The same or similar question on other venues |
| `search(q)` | `GET /search/suggest` | Events and markets by title |
| `summary()` | `GET /summary` | Per-venue counts and 24h volume |
| `news_movers(...)` | `GET /news/movers` | The price moves behind pdata.world/news |
| `bulk_index()`, `iter_bulk(kind)` | `/bulk/` | Nightly full files, streamed without saving |

Every method returns the API's JSON unchanged, so the
[API reference](https://api.pdata.world/docs) describes every field. Unknown filters are
rejected with a message listing every allowed one. Errors raise `PdataError` with the API's
`code` and `message`.

Runnable examples are in [`examples/`](examples/):
[`quickstart.py`](examples/quickstart.py) makes five common calls, and
[`resolved_archive.py`](examples/resolved_archive.py) streams the archive of settled events.

## Other ways to get the same data

- **MCP server for AI assistants:** `https://api.pdata.world/mcp`, remote over Streamable
  HTTP, no key. Add `{"mcpServers": {"pdata": {"url": "https://api.pdata.world/mcp"}}}`
  to the client config ([`examples/mcp.json`](examples/mcp.json)), or run
  `claude mcp add --transport http pdata https://api.pdata.world/mcp`. It is listed in the
  official MCP registry as `world.pdata/mcp`.
- **Nightly bulk files** at <https://api.pdata.world/bulk/>: every open market
  (`markets-open`), every open event (`events-open`) and the archive of settled events with
  their results (`resolved`), as gzipped JSON lines. Line 1 of each file is a manifest
  giving the licence and every field's meaning and unit.
- **Read-only Postgres** with full SQL:
  `postgresql://pdata_readonly:pdata_public_2026@pg.pdata.world:6433/pdata_new`. The
  password is published on purpose and is never rotated. Queries are capped at 5 seconds.
  See [`examples/postgres.sql`](examples/postgres.sql).
- **The website:** every event has a page at `https://pdata.world/events/{source}/{id}`,
  and <https://pdata.world/data> describes all of the above.

## Sample data

[`data/`](data/) holds random samples of the three bulk files as of 7 October 2026: 1,000
open markets, 500 open events and 1,000 settled events, with an equal share per venue where
the venue had enough rows. Each file starts with the manifest line. They are for looking at
the shape of the data; the full files are rebuilt every night.

## Units and things to know

- `probability` and prices are on a 0–1 scale.
- `volume` and `volume_24hr` are in each venue's own unit and are **not** converted across
  venues: shares for Polymarket and contracts for Kalshi (each pays $1 at resolution),
  play-money mana for Manifold, and each other venue's figure as it reports it.
  [How eight venues count volume](https://pdata.world/research/prediction-market-volume)
  explains each one.
- Price history starts in May 2026. Points older than 7 days are kept as 12-hour buckets,
  and a market's history is deleted 10 days after it closes. After that, the event's URL
  returns `"kind": "tombstone"` with each top market's final result.
- In the `resolved` archive, each market's `probability` is the last price pdata saw, which
  is usually after the market settled. It records the result; it is not a forecast.
- Events that closed between 2 June and 11 August 2026 are missing from the `resolved`
  archive: they were pruned before a backup was taken.
- pdata groups Kalshi's sibling events for one game under a single group event
  (`is_group`); its volume is the sum of its children.

## Research using this data

pdata.world publishes dated reports built from this data, each with its method and limits:

- [How accurate were prediction-market prices a day before the result?](https://pdata.world/research/prediction-market-accuracy)
  For 39,681 Polymarket and Kalshi markets that settled between 28 September and
  5 October 2026, grouped into 10-point bands by their price 24 hours before close, the
  share that resolved YES was on average 0.96 percentage points from the band's average
  price (Brier score 0.110, against 0.199 for always guessing the base rate).
- [How eight prediction-market venues count volume](https://pdata.world/research/prediction-market-volume)
- [What each prediction-market API gives you](https://pdata.world/research/prediction-market-apis)
- [Same question, different price: prediction markets across venues](https://pdata.world/research/cross-venue-prices)
- [What eight prediction-market venues list, by category](https://pdata.world/research/prediction-market-coverage)

## Citing

The data is CC BY 4.0. A credit such as "Data: pdata.world" with a link is enough. Every
single-event API answer also carries `_meta.cite_as`, a ready-made citation sentence. For
papers, GitHub's "Cite this repository" button uses [`CITATION.cff`](CITATION.cff).

## Licence

The code in this repository is under the [MIT licence](LICENSE). The data, including the
files in `data/`, is under [CC BY 4.0](data/LICENSE.md); the underlying market data remains
subject to each venue's own terms.

pdata.world is independent and not affiliated with any of the venues it tracks.
