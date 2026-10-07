"""Stream the archive of resolved events (about 36 MB gzipped) without saving it.

Counts, per venue, how many archived markets carry a reported result.
Run: python examples/resolved_archive.py
"""

from collections import Counter

from pdata import Client

pd = Client(timeout=120)

manifest = next(pd.iter_bulk("resolved", include_manifest=True))["_manifest"]
print(manifest["description"], "\n")

events = Counter()
with_result = Counter()
for event in pd.iter_bulk("resolved"):
    events[event["source"]] += 1
    with_result[event["source"]] += sum(1 for m in event["markets"] if m["result"] is not None)

for source, n in events.most_common():
    print(f"{source:<11} {n:>8,} events  {with_result[source]:>9,} markets with a result")

# Note: each market's `probability` here is the last price pdata saw, which is
# usually after the market settled (close to 0 or 1). It is a record of the
# result, not a forecast — for forecast accuracy see
# https://pdata.world/research/prediction-market-accuracy
