-- pdata.world's public read-only Postgres.
--
--   psql 'postgresql://pdata_readonly:pdata_public_2026@pg.pdata.world:6433/pdata_new'
--
-- Public views: events, markets, source_stats, source_status and
-- resolved_markets in pdata_public. The public.market_snapshots and
-- public.event_snapshots tables hold history. Use \d+ markets for field descriptions.

-- Per-venue totals are precomputed in source_stats.
-- Volume is in US dollars except on Manifold, which uses play-money mana.
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
