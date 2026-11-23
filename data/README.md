# Sample data

Random samples of three pdata.world nightly bulk files, taken from the files
built at 07:58 UTC on 7 October 2026. Rows were drawn at random with an equal
share per venue where the venue had enough rows (seed 20261007).

| File | Rows | Full file |
|---|---|---|
| `sample-markets-open.jsonl` | 1,000 of 417,132 open markets | <https://api.pdata.world/bulk/markets-open-latest.jsonl.gz> |
| `sample-events-open.jsonl` | 500 of 38,356 open events | <https://api.pdata.world/bulk/events-open-latest.jsonl.gz> |
| `sample-resolved.jsonl` | 1,000 of 450,216 settled events | <https://api.pdata.world/bulk/resolved-latest.jsonl.gz> |

Line 1 of each file is a manifest (`{"_manifest": {...}}`) giving the licence
and the meaning and unit of every field at the time of the snapshot. Every
other line is one record.

The current nightly release covers 12 venues and includes a fourth export,
[`resolved-markets`](https://api.pdata.world/bulk/resolved-markets-latest.jsonl.gz),
with one record per archived market. Current volume is in US dollars on
every venue except Manifold, which uses play-money mana. The
[bulk index](https://api.pdata.world/bulk/index.json) lists sizes, row counts
and SHA-256 hashes for all four exports.

Licence: CC BY 4.0 — see [LICENSE.md](LICENSE.md).
