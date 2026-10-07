# Sample data

Random samples of pdata.world's three nightly bulk files, taken from the files
built at 07:58 UTC on 7 October 2026. Rows were drawn at random with an equal
share per venue where the venue had enough rows (seed 20261007).

| File | Rows | Full file |
|---|---|---|
| `sample-markets-open.jsonl` | 1,000 of 417,132 open markets | <https://api.pdata.world/bulk/markets-open-latest.jsonl.gz> |
| `sample-events-open.jsonl` | 500 of 38,356 open events | <https://api.pdata.world/bulk/events-open-latest.jsonl.gz> |
| `sample-resolved.jsonl` | 1,000 of 450,216 settled events | <https://api.pdata.world/bulk/resolved-latest.jsonl.gz> |

Line 1 of each file is a manifest (`{"_manifest": {...}}`) giving the licence
and the meaning and unit of every field; every other line is one record. The
full files are rebuilt every night, and <https://api.pdata.world/bulk/index.json>
lists their sizes, row counts and sha256 hashes.

Licence: CC BY 4.0 — see [LICENSE.md](LICENSE.md).
