---
name: pdata-prediction-markets
description: Current prediction-market odds, 24-hour moves, volume and cross-venue matches from Polymarket, Kalshi, Manifold, Myriad, Limitless, Predict, Opinion and Gemini, read from pdata.world's read-only MCP server or REST API. Use when the user asks for the odds or market probability of a real-world event, what moved in prediction markets today, which markets close soon, or how two venues price the same question.
license: MIT
---

# pdata.world prediction-market data

pdata.world collects public data from 8 prediction-market venues (Polymarket, Kalshi,
Manifold, Myriad, Limitless, Predict, Opinion, Gemini) into one read-only service. There is
no key and no account.

## Looking something up

With the `pdata` MCP tools connected:

1. `search_suggest` with `q` set to a few distinctive words returns matching events and
   markets, each with its `source` and `id`.
2. `get_event` with that `source` and `event_id` returns the event, its markets and their
   current probabilities. `get_market` does the same for one market (`source`, `market_id`).
3. `get_event_similar` (`source`, `event_id`) finds the same or a similar question on other
   venues.
4. `top_movers` lists the largest 24-hour probability changes, `list_news_movers` the price
   spikes behind the news feed, and `closing_soon` markets that resolve within 36 hours.
5. `get_summary` gives per-venue counts and 24-hour volume.

Without the MCP tools, the same data is a plain HTTPS GET under
`https://api.pdata.world/api/v1`:

- `/search/suggest?q=<words>`
- `/events/{source}/{event_id}` and `/events/{source}/{event_id}/similar`
- `/markets/{source}/{market_id}`
- `/markets/top-movers?limit=10`, `/markets/closing-soon`, `/news/movers`
- `/summary`

An unknown query parameter returns `400` with the list of allowed ones.

## Reading the numbers

- A market's `probability` is the venue's own price for its first outcome (usually YES),
  between 0 and 1. It is what the market says, not a forecast made by pdata.world.
- Volume is in each venue's own unit and is not converted: shares on Polymarket, contracts
  on Kalshi, play-money mana on Manifold. Do not add volumes across venues.
- Every response carries `_meta.as_of`. Say how fresh a number is when you quote it.
- An event that closed more than 10 days ago comes back with `"kind": "tombstone"` and its
  final results. Those prices record the outcome; they are not a forecast.

## Citing

Single-event and single-market answers carry `_meta.cite_as`, a ready-made sentence naming
the venue, the leading or chosen outcome with its probability, the date, and the event's page at
`https://pdata.world/events/{source}/{id}`. Quote it, or link that page. The data is
published under CC BY 4.0 with the credit "pdata.world".
