# Prediction Market Odds (pdata.world)

**Current odds, 24-hour moves and trading volume for prediction-market events on eight
venues: Polymarket, Kalshi, Manifold, Myriad, Limitless, Predict, Opinion and Gemini.**
Type a few words such as `fed decision`, pick a venue, or leave both empty to get the most
traded events right now. Each result is one event with its leading outcome, that outcome's
probability and 24-hour change, the event's 24-hour volume and, if you ask for them, its
other outcomes with their prices.

The data comes from [pdata.world](https://pdata.world), which collects the venues' public
market data into one read-only API. This actor reads that API; it does not scrape the
venues and needs no account or key anywhere.

## What you can do with it

- Check what the markets say about an election, a central-bank decision, a match or a
  company event, across every venue that lists it.
- Track the most traded prediction markets each day by scheduling the actor with no input.
- Feed odds into a spreadsheet, a dashboard or an AI agent through Apify's API,
  integrations and scheduler.

## How to use it

1. Enter a **search phrase**, choose a **venue**, or leave both empty.
2. Set **Maximum events** (1 to 200) and **Outcomes per event** (0 to 50).
3. Run the actor and open the **Events** or **Outcomes** view of the results, or export
   them as JSON, CSV or Excel.

## Input

| Field | Meaning | Default |
|---|---|---|
| `search` | Words to look for in event titles and descriptions | none: most traded events |
| `venue` | One of `polymarket`, `kalshi`, `manifold`, `myriad`, `limitless`, `predict`, `opinion`, `gemini` | all eight |
| `maxEvents` | How many events, most traded in the last 24 hours first | 20 |
| `outcomesPerEvent` | Outcomes to include per event; `0` keeps only the leading one | 5 |
| `includeClosed` | Also return events that stopped trading in the last 10 days | false |

```json
{ "search": "fed decision", "maxEvents": 3, "outcomesPerEvent": 3 }
```

## Output

One dataset item per event. This one came from the input above with `maxEvents: 1` and
`outcomesPerEvent: 2` on 12 November 2026; numbers are rounded and the `question` text of
each outcome is left out:

```json
{
  "title": "Fed Decision in December?",
  "venue": "polymarket",
  "eventId": "770450",
  "topOutcome": "25 bps increase",
  "topOutcomeProbability": 0.865,
  "topOutcomeChange24h": 0.01,
  "volume24h": 1416082.65,
  "volumeUnit": "shares",
  "endDate": "2026-12-10T04:59:00Z",
  "closed": false,
  "categories": ["Politics", "Economy"],
  "outcomes": [
    { "outcomeName": "25 bps increase", "outcomeProbability": 0.865, "outcomeChange24h": 0.01, "outcomeVolume24h": 210690.41, "outcomeClosed": false, "marketId": "3215008" },
    { "outcomeName": "50+ bps increase", "outcomeProbability": 0.0945, "outcomeChange24h": 0.0005, "outcomeVolume24h": 628442.72, "outcomeClosed": false, "marketId": "3215009" }
  ],
  "outcomesTotal": 5,
  "pdataUrl": "https://pdata.world/events/polymarket/770450",
  "venueUrl": "https://polymarket.com/event/fed-decision-in-december-20260729232808632",
  "citeAs": "According to pdata.world (tracking Polymarket): \"Fed Decision in December?\" — \"25 bps increase\" leads at 86% across 5 outcomes as of 2026-11-12 UTC. https://pdata.world/events/polymarket/770450",
  "asOf": "2026-11-12T08:52:39.580069Z",
  "attribution": "Data aggregated by pdata.world (https://pdata.world) from 8 prediction-market venues; CC BY 4.0; source data © each venue."
}
```

## How to read the numbers

- **Probabilities** run from 0 to 1 and are each venue's own market price, not a forecast
  made by pdata.world or by this actor.
- **24-hour changes** are in probability units: `0.03` means three percentage points.
- **Volume** is in each venue's own unit and is never converted: shares on Polymarket,
  contracts on Kalshi, play-money mana on Manifold, and each other venue's figure as it
  reports it. `volumeUnit` says which. Do not add volumes across venues.
- **Order:** events come most traded first by the 24-hour volume each venue reports. With
  no venue chosen, that order mixes units across venues; choose a venue for a like-for-like
  ranking.
- **Freshness:** `asOf` is when pdata.world served the numbers. pdata.world polls each
  venue every 10 to 60 minutes.

## Cost

The actor itself is free. Each run uses a little Apify platform time on your account: one
request to pdata.world, plus one per event when outcomes are requested.

## Tips and known limits

- Search looks at event descriptions as well as titles, so broad words also find events
  that only mention them. Use the most specific words you can, or add a venue.
- A search is slower than a plain listing: when tested on 12 November 2026, runs with a
  search took 7 to 13 seconds and a run of 10 events without one took under 4.
- Events that closed more than 10 days ago are not returned.

## Data source and licence

- **Data:** collected by pdata.world from the eight venues' public data
  ([API documentation](https://api.pdata.world/docs)), published under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit "pdata.world" when you
  reuse it; every item carries the `attribution` line and a
  `citeAs` sentence. The underlying market data remains subject to each venue's own terms.
- **Actor code:** MIT licence.
- pdata.world is independent and not affiliated with any of the venues it tracks, and
  this actor is not made or endorsed by any of them.
