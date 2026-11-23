---
name: pdata-prediction-markets
description: Find and cite prediction-market odds across venues with pdata. Use for current prices, historical moves, and market rules or results.
metadata:
  author: pdata.world
---

# Prediction-market odds with pdata

Use pdata to find odds, price history, market rules and results. Match the
venue, question, outcome and resolution rules before quoting. Fetch fresh data.

## MCP

Connect to `https://api.pdata.world/mcp` over Streamable HTTP. No key is
required. API 2.18.0 exposes 21 read-only tools. Use `tools/list` for
the inputs.

- Find IDs with `search_suggest(q)`, then follow the hit's `event_path`.
  Use `list_events` and `list_markets` for filtered results.
- Read compact event data with `get_event_brief`. Check `outcomes_total`
  against the returned outcomes. Use `get_event` for full markets and
  `get_market` for a specific price, quote or archived result.
- Use `get_markets` for up to 50 listing rows by `source:market_id`.
- Use `compare_pairs` for matched Polymarket and Kalshi prices. Read both
  sets of rules and compare their observation times.
- Use `get_event_history` for price and 24-hour volume by market, and
  `get_status` for venue clocks and coverage.
- For research, call `search(query)` for event IDs, titles and links,
  then `fetch(id)` for a Markdown brief and its citation.

Use `page` and `page_size` on `list_events`, `list_markets` and
`list_news_movers`. Use `limit` on `top_movers`, `closing_soon`,
`search_suggest` and `compare_pairs`, and `markets_limit` on
`get_event` and `get_event_history`. Event and market list tools and
both market rails default to lean rows. Use `view=full` for more fields.

## REST

Send GET requests to `https://api.pdata.world/api/v1`.

- Search: `/search/suggest?q=fed+rate+cut&limit=5`.
- Filter markets: `/markets?closed=false&search=fed+rate+cut&page_size=5&view=lean`.
  REST defaults to full rows. On paged lists, `limit` is an alias for
  `page_size`. A false `meta.total_counted` means the total was skipped.
- Read event data: `/events/{source}/{id}/brief`. Add `?format=md` or send
  `Accept: text/markdown` for Markdown. The site also serves it at
  `https://pdata.world/events/{source}/{id}.md`.
- Read market data: `/markets/{source}/{market_id}`, or
  `/markets/batch?ids={source}:{market_id},...` for listing rows.
- Read history: `/events/{source}/{id}/history?range=7d&market_id={market_id}`.
- Read venue clocks: `/status`.

## Prices, clocks and citation

- Market `probability` is a fraction. Multiply by 100 to quote a percent.
  Volume is in US dollars on every venue except Manifold, which uses
  play-money mana.
- Read `quote_tier` before quoting. Label non-firm prices by tier.
  `quotable` signals stored-price eligibility. `price_basis` says how
  the price was obtained. Get the market detail if the brief lacks a
  tier. For closed markets, read the result separately from the
  recorded price.
- When provided, `price_source` selects `quote.probability` for
  `hot_quote` or the row's `probability` for `bulk_row`. Report a
  missing price as unavailable.
- `_meta.as_of` is response time. On detail, `_meta.data_as_of` gives
  the data's stored write time when available. Row `updated_at` is the
  legacy write time, `changed_at` dates the last material change, and
  row `checked_at` gives the start of the census that individually
  confirmed it, when known. Use `_meta.venues` or `/status` for the
  completed-cycle time, typical period and coverage.
- Use `_meta.cite_as` when it describes the figure. Keep the MCP source
  line or Markdown citation. Credit pdata.world under CC BY 4.0. Give
  the venue, question, outcome, price and available UTC data time and
  link to `pdata_url` or `_meta.canonical_url`.

## Limits

Send a descriptive `User-Agent`. The published limit is 50 requests
per second per IP with bursts up to 100. Wait for `Retry-After` on a
429 or 503 when supplied. Use the [bulk files](https://api.pdata.world/bulk/)
for whole tables. See [OpenAPI](https://api.pdata.world/openapi.json) and the
[agent guide](https://pdata.world/agents.md) for route limits and examples.
