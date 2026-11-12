"""The actor: read the input, fetch the events, store one dataset item per event."""

from __future__ import annotations

import asyncio

from apify import Actor

from .fetch import PdataApi, fetch_events, normalize_input


async def main() -> None:
    async with Actor:
        options = normalize_input(await Actor.get_input())
        Actor.log.info("Reading pdata.world with %s", options)
        rows = await asyncio.to_thread(fetch_events, PdataApi(), **options)
        await Actor.push_data(rows)
        if rows:
            message = f"{len(rows)} events, data as of {rows[0]['asOf']} (pdata.world, CC BY 4.0)"
        else:
            message = "No events matched; try fewer or different words, or another venue"
        await Actor.set_status_message(message)
