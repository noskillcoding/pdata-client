# pdata-client

Python client, AI-assistant plugins and sample data for **[pdata.world](https://pdata.world)**,
a free, read-only API for prediction-market data from 12 venues. It covers Polymarket, Kalshi,
Manifold, Myriad, Limitless, Predict, Opinion, Gemini, Hyperliquid, MNX, Seer and XO Market.

```bash
pip install pdata-client
```

```python
from pdata import Client

pd = Client()
page = pd.markets(source=["kalshi", "polymarket"], closed=False, sort="-volume_24hr", page_size=5)
for market in page["items"]:
    print(market["source"], market["question"], market.get("probability"), market.get("quote_tier"))
```

**Cite as** pdata.world, *Prediction-market prices, volumes and results*, snapshot
2026-11-23, CC BY 4.0. [Snapshot DOI 10.5281/zenodo.24476601](https://doi.org/10.5281/zenodo.24476601).
For the dataset across versions, use [concept DOI 10.5281/zenodo.23211610](https://doi.org/10.5281/zenodo.23211610).

## Install

```bash
pip install pdata-client
# or the latest commit:
pip install git+https://github.com/noskillcoding/pdata-client
```

The client uses only the standard library and runs on Python 3.9 or later. To embed it,
copy [`src/pdata/client.py`](https://github.com/noskillcoding/pdata-client/blob/main/src/pdata/client.py) and [`src/pdata/_version.py`](https://github.com/noskillcoding/pdata-client/blob/main/src/pdata/_version.py)
into the same package. It sends `pdata-client/<version> (+https://pdata.world/agents)` as
its User-Agent. Pass `user_agent=` to name your own project.

## What the client covers

API 2.18.0 serves REST at `https://api.pdata.world/api/v1` with no API key or signup.

| Method | API operation | What it returns |
|---|---|---|
| `markets(**filters)`, `iter_markets(...)` | `GET /markets` | Markets, one page or all pages |
| `market(source, id)` | `GET /markets/{source}/{id}` | One market |
| `markets_batch(ids)` | `GET /markets/batch` | Up to 50 markets by `source:market_id`, with missing keys in `not_found` |
| `top_movers(...)`, `closing_soon(...)` | `GET /markets/top-movers`, `/markets/closing-soon` | Large 24-hour price changes or upcoming closes |
| `events(**filters)`, `iter_events(...)` | `GET /events` | Events that group the markets of a question |
| `event(source, id)` | `GET /events/{source}/{id}` | One event with its markets or archived results |
| `event_brief(source, id, format="md")` | `GET /events/{source}/{id}/brief` | A compact event brief, as Markdown or JSON |
| `event_history(source, id, range=...)` | `GET /events/{source}/{id}/history` | Price and 24-hour volume series for `24h`, `7d`, `30d` or `all` |
| `similar_events(source, id)` | `GET /events/{source}/{id}/similar` | Similar events |
| `compare_pairs(...)` | `GET /compare/pairs` | Matched Polymarket and Kalshi questions with firm prices |
| `search(q)` | `GET /search/suggest` | Events and markets by title |
| `status()` | `GET /status` | API version and venue clocks for all 12 venues |
| `summary()` | `GET /summary` | Per-venue counts and 24-hour volume |
| `news_movers(...)` | `GET /news/movers` | Stories grouped from qualifying price moves |
| `bulk_index()`, `iter_bulk(kind)` | `/bulk/` | Nightly files, streamed without saving |

```python
status = pd.status()  # status["venues"]["kalshi"]["checked_at"]
batch = pd.markets_batch(["polymarket:561261"])
brief = pd.event_brief("polymarket", "31552", format="md")
history = pd.event_history("polymarket", "31552", range="7d",
                           interval="1d", max_points=7, markets_limit=1)
pairs = pd.compare_pairs(left="polymarket", right="kalshi", limit=1)
lean = pd.markets(source="polymarket", view="lean", limit=5)
tier = lean["items"][0].get("quote_tier") if lean["items"] else None
clocks = lean["_meta"].get("venues", {})
```

REST defaults to full rows. Use `view="lean"` on market and event lists, top movers and
closing soon. `limit` aliases `page_size` on paged lists, including `news_movers`.
Give both aliases the same value if you supply both. Market rows expose `quote_tier`
when available. Label non-firm prices with their tier. Where present, `_meta.venues`
gives the latest completed cycle's `checked_at`, typical `cycle_period_s` and census
`coverage` by venue.

JSON methods return the decoded response unchanged. A Markdown brief returns a string.
API errors raise `PdataError` with a `code` and `message`. See the
[API reference](https://api.pdata.world/docs) and [OpenAPI](https://api.pdata.world/openapi.json).

Runnable examples include [`quickstart.py`](https://github.com/noskillcoding/pdata-client/blob/main/examples/quickstart.py) and
[`resolved_archive.py`](https://github.com/noskillcoding/pdata-client/blob/main/examples/resolved_archive.py).

## The MCP server and the assistant plugins

pdata.world hosts a read-only MCP server with 21 tools at `https://api.pdata.world/mcp`
over Streamable HTTP. It needs no API key or sign-in. The official MCP registry lists
the server as `world.pdata/mcp`.

- **Claude** — Open **Customize → Connectors → + Add → Add custom connector**. Enter
  `pdata` and the server URL, select **No sign in**, then **Add**. On Team and Enterprise,
  an owner adds it under **Organization settings → Connectors → Add → Custom → Web**.
  Enable pdata from **+ → Connectors** in the chat.
- **Claude Code** — Run `claude mcp add --transport http pdata https://api.pdata.world/mcp`.
  Check with `claude mcp get pdata`.
- **ChatGPT** — In an eligible web workspace, use **Plugins → + → Add custom MCP server**,
  enter `pdata` and the server URL, choose **No authentication**, then **Create as a plugin**.
  Install it and select it with `@` in a chat. In the Developer Mode interface, use
  **Settings → Apps → Advanced settings**, then **Apps → Create → Scan Tools → Create**.
- **Cursor** — Copy [`examples/mcp.json`](https://github.com/noskillcoding/pdata-client/blob/main/examples/mcp.json) to `.cursor/mcp.json` or
  `~/.cursor/mcp.json`, or merge the `pdata` entry into an existing `mcpServers` object.
- **VS Code** — In `~/.copilot/mcp-config.json` or `$COPILOT_HOME/mcp-config.json`,
  add `"pdata": {"type":"http","url":"https://api.pdata.world/mcp","tools":["*"]}`
  under `mcpServers`. For an editor-managed setup, add the entry with `type` and `url`
  under `servers` in `.vscode/mcp.json`.

See the Connect section of the [agent guide](https://pdata.world/agents.md) for full setup instructions.

- **Claude Code plugin** — For the server and skill together, run
  `claude plugin marketplace add noskillcoding/pdata-client` followed by
  `claude plugin install pdata@pdata-world`.
- **Gemini CLI** — `gemini extensions install https://github.com/noskillcoding/pdata-client`
  adds the same server and skill.
- **Skill installer** — `npx skills add noskillcoding/pdata-client` discovers
  [`pdata-prediction-markets`](https://github.com/noskillcoding/pdata-client/blob/main/skills/pdata-prediction-markets/SKILL.md).

## What is in this repository

| Path | What it is |
|---|---|
| [`src/pdata/`](https://github.com/noskillcoding/pdata-client/tree/main/src/pdata/) | The Python client, published on PyPI as `pdata-client` |
| [`.claude-plugin/`](https://github.com/noskillcoding/pdata-client/tree/main/.claude-plugin/), [`.mcp.json`](https://github.com/noskillcoding/pdata-client/blob/main/.mcp.json), [`skills/`](https://github.com/noskillcoding/pdata-client/tree/main/skills/) | Claude Code plugin, marketplace and shared skill |
| [`gemini-extension.json`](https://github.com/noskillcoding/pdata-client/blob/main/gemini-extension.json) | Gemini CLI extension |
| [`apify/`](https://github.com/noskillcoding/pdata-client/tree/main/apify/) | Source of an Apify actor that returns events with current prices |
| [`data/`](https://github.com/noskillcoding/pdata-client/tree/main/data/) | Historical samples of the bulk files, CC BY 4.0 |
| [`examples/`](https://github.com/noskillcoding/pdata-client/tree/main/examples/) | Runnable scripts and an MCP client config |

## Other ways to get the same data

- **Nightly bulk files** include `markets-open`, `events-open`, `resolved` (archived
  events) and `resolved-markets` (archived markets) as gzipped JSON Lines. Line 1 of each
  file is a manifest with the licence and field definitions. [Bulk downloads](https://api.pdata.world/bulk/)
- **Dataset snapshot** — The 2026-11-23 Zenodo snapshot contains four Parquet exports.
  The corresponding Hugging Face tag is
  [`2026-11-23`](https://huggingface.co/datasets/lowskillcoding/pdata-prediction-markets/tree/2026-11-23).
  The dataset is also listed on [Kaggle](https://www.kaggle.com/datasets/pdpdpa/pdata-prediction-markets).
- **Read-only Postgres** — The agent guide includes connection details and supported views.
  [SQL examples](https://github.com/noskillcoding/pdata-client/blob/main/examples/postgres.sql)
- **The website** — Event pages use `https://pdata.world/events/{source}/{id}`.
  [Data downloads and access methods](https://pdata.world/data)

## Sample data

The samples from 7 October 2026 include 1,000 open markets, 500 open events and 1,000
settled events. Each file starts with the manifest for that snapshot.
[`data/`](https://github.com/noskillcoding/pdata-client/tree/main/data/)

## Units and things to know

- `probability` and market prices are on a 0–1 scale.
- Volume is in US dollars on every venue except Manifold, which uses play-money mana.
- In the `resolved` archive, `probability` records the last price pdata saw. Use
  the separate result field for the reported settlement.
- A pruned event can return `"kind": "tombstone"` with archived resolutions.
  The [agent guide](https://pdata.world/agents.md) describes history and data freshness.

## Research using this data

- [How accurate were prediction-market prices a day before the result?](https://pdata.world/research/prediction-market-accuracy)
- [How prediction-market venues count volume](https://pdata.world/research/prediction-market-volume)
- [What each prediction-market API gives you](https://pdata.world/research/prediction-market-apis)
- [Same question, different price: prediction markets across venues](https://pdata.world/research/cross-venue-prices)
- [Prediction-market coverage by category](https://pdata.world/research/prediction-market-coverage)

## Citing

Credit pdata.world and link to the source. Event detail can carry a ready-made citation in
`_meta.cite_as`. When citing a specific dataset snapshot, use
[10.5281/zenodo.24476601](https://doi.org/10.5281/zenodo.24476601) for the 2026-11-23 release.
[10.5281/zenodo.23211610](https://doi.org/10.5281/zenodo.23211610) is the stable concept
DOI for all versions. GitHub's **Cite this repository** button uses
[`CITATION.cff`](https://github.com/noskillcoding/pdata-client/blob/main/CITATION.cff).

## Licence

The code, plugin files and Apify actor are under the [MIT licence](https://github.com/noskillcoding/pdata-client/blob/main/LICENSE). The pdata.world
aggregation and samples are under [CC BY 4.0](https://github.com/noskillcoding/pdata-client/blob/main/data/LICENSE.md). The underlying market data
remains subject to each venue's own terms.

pdata.world is independent and has no affiliation with the venues it tracks.

## Releasing

Keep the version in [`src/pdata/_version.py`](https://github.com/noskillcoding/pdata-client/blob/main/src/pdata/_version.py),
[`.claude-plugin/plugin.json`](https://github.com/noskillcoding/pdata-client/blob/main/.claude-plugin/plugin.json) and
[`gemini-extension.json`](https://github.com/noskillcoding/pdata-client/blob/main/gemini-extension.json) in sync. A push of a matching
`v<version>` tag triggers [`publish.yml`](https://github.com/noskillcoding/pdata-client/blob/main/.github/workflows/publish.yml), which builds
the distributions, tests the wheel and uses PyPI trusted publishing.
