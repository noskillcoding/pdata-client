-- pdata.world's public read-only Postgres. The password is published and
-- never rotated; it is part of the address, not a secret.
--
--   psql 'postgresql://pdata_readonly:pdata_public_2026@pg.pdata.world:6433/pdata_new'
--
-- Readable: events, markets, source_stats (views, unqualified names work),
-- public.market_snapshots and public.event_snapshots (price and volume
-- history since May 2026; rows older than 7 days are 12-hour buckets), and
-- public.market_status_log. Every table and column has a comment: \d+ markets

-- Queries are capped at 5 seconds. Per-venue totals are precomputed in
-- source_stats (24h volume in each venue's own unit):
SELECT source, markets_active, events_active, round(volume_24hr_total) AS volume_24h, computed_at
FROM source_stats
ORDER BY volume_24h DESC NULLS LAST;

-- The 10 most traded open Kalshi markets right now.
SELECT e.title AS event, m.question, m.probability, m.volume_24hr
FROM markets m
JOIN events e ON e.source = m.source AND e.id = m.event_id
WHERE m.source = 'kalshi' AND NOT m.closed
ORDER BY m.volume_24hr DESC NULLS LAST
LIMIT 10;

-- One market's hourly price over the last two days.
SELECT date_trunc('hour', recorded_at) AS hour, avg(probability) AS probability
FROM public.market_snapshots
WHERE source = 'kalshi' AND market_id = 'KXU3MAX-30-10'
  AND recorded_at > now() - interval '2 days'
GROUP BY 1
ORDER BY 1;
