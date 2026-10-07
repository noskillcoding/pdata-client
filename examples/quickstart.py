"""The five calls most people start with. Run: python examples/quickstart.py"""

from pdata import Client

pd = Client()

# 1. The most traded open markets on Kalshi and Polymarket over the last 24h.
#    Volume is in each venue's own unit (Polymarket shares, Kalshi contracts).
top = pd.markets(source=["kalshi", "polymarket"], closed=False, sort="-volume_24hr", page_size=5)
for m in top["items"]:
    print(f"{m['source']:<10} {m['probability']:>5.0%}  {m['event_title']} — {m['question']}")

# 2. One event with its markets, and the citation pdata suggests for it.
first = top["items"][0]
event = pd.event(first["source"], first["event_id"], markets_limit=3)
print("\n" + event["_meta"]["cite_as"])

# 3. That event's price history over 7 days (one series per top market).
history = pd.event_history(first["source"], first["event_id"], range="7d", limit=1)
for series in history["series"]:
    points = series["points"]
    if points:
        print(f"\n{series['name']}: {len(points)} points, "
              f"{points[0]['probability']} -> {points[-1]['probability']}")

# 4. The biggest 24h moves across all eight venues, leaving out markets that
#    are settling (now under 5% or over 95%) and ones that barely trade.
movers = pd.top_movers(
    limit=5, closed=False, volume_24hr_min=1000, probability_min=0.05, probability_max=0.95
)
for m in movers["items"]:
    print(f"{m['prob_24h_change']:+.0%}  {m['source']:<10} {m['question']}")

# 5. Search by title.
for hit in pd.search("fed", limit=3)["results"]:
    print(hit["source"], hit["title"])
