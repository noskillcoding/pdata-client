"""Offline tests for the actor's core; a fake opener stands in for the network.

Run from the repository root:  python -m unittest discover -s apify/tests -t apify
Set PDATA_LIVE=1 to also call the live API once.
"""

from __future__ import annotations

import io
import json
import os
import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from pdata_actor.fetch import (
    ApiError,
    InputError,
    PdataApi,
    event_page_url,
    fetch_events,
    normalize_input,
)

META = {"as_of": "2026-11-12T08:00:00Z", "attribution": "Data aggregated by pdata.world"}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class FakeOpener:
    def __init__(self, routes):
        self.routes = routes
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        answer = self.routes[urlsplit(request.full_url).path]
        if callable(answer):
            answer = answer(request.full_url)
        if isinstance(answer, HTTPError):
            raise answer
        return FakeResponse(json.dumps(answer).encode())


def query(url):
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


def event(source, event_id, **extra):
    base = {
        "source": source,
        "id": event_id,
        "title": f"Event {event_id}",
        "top_outcome": "Yes",
        "top_outcome_probability": 0.6,
        "top_outcome_prob_24h_change": 0.05,
        "volume_24hr": 1000.0,
        "end_date": "2026-12-31T00:00:00Z",
        "closed": False,
        "categories": ["Politics"],
        "url": f"https://{source}.example/{event_id}",
    }
    base.update(extra)
    return base


def detail(source, event_id, n):
    return {
        "_meta": {
            "as_of": "2026-11-12T08:01:00Z",
            "canonical_url": f"https://pdata.world/events/{source}/{event_id}",
            "cite_as": f"According to pdata.world ... {event_id}",
        },
        "markets_total": 7,
        "markets": [
            {
                "id": f"m{i}",
                "question": f"Question {i}?",
                "group_item_title": f"Outcome {i}",
                "probability": 0.5 - i / 10,
                "prob_24h_change": 0.01,
                "volume_24hr": 10.0,
                "closed": False,
            }
            for i in range(n)
        ],
    }


class InputTests(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(
            normalize_input({}),
            {
                "search": None,
                "venue": None,
                "max_events": 20,
                "outcomes_per_event": 5,
                "include_closed": False,
            },
        )

    def test_blank_search_and_venue_mean_none(self):
        opts = normalize_input({"search": "   ", "venue": ""})
        self.assertIsNone(opts["search"])
        self.assertIsNone(opts["venue"])

    def test_rejects_bad_values(self):
        for raw in (
            {"venue": "betfair"},
            {"maxEvents": 0},
            {"maxEvents": 201},
            {"maxEvents": "10"},
            {"outcomesPerEvent": 51},
            {"includeClosed": "yes"},
            {"search": "x" * 201},
        ):
            with self.subTest(raw=raw), self.assertRaises(InputError):
                normalize_input(raw)


class FetchTests(unittest.TestCase):
    def test_list_query_and_one_detail_call_per_event(self):
        events = [event("polymarket", "1"), event("kalshi", "group:26NOV12ABC")]
        opener = FakeOpener(
            {
                "/api/v1/events": {"_meta": META, "items": events},
                "/api/v1/events/polymarket/1": lambda u: detail("polymarket", "1", 2),
                "/api/v1/events/kalshi/group%3A26NOV12ABC": lambda u: detail(
                    "kalshi", "group:26NOV12ABC", 2
                ),
            }
        )
        rows = fetch_events(
            PdataApi(opener=opener), search="fed decision", venue=None, max_events=2,
            outcomes_per_event=2,
        )
        listing = query(opener.requests[0].full_url)
        self.assertEqual(
            listing,
            {"sort": "-volume_24hr", "page_size": "2", "search": "fed decision", "closed": "false"},
        )
        self.assertEqual(len(opener.requests), 3)
        self.assertEqual(query(opener.requests[1].full_url), {"markets_limit": "2"})
        self.assertTrue(opener.requests[0].get_header("User-agent").startswith("pdata-apify-actor/"))

        first = rows[0]
        self.assertEqual(first["venue"], "polymarket")
        self.assertEqual(first["volumeUnit"], "USD")
        self.assertEqual(first["outcomesTotal"], 7)
        self.assertEqual([o["outcomeName"] for o in first["outcomes"]], ["Outcome 0", "Outcome 1"])
        self.assertEqual(first["citeAs"], "According to pdata.world ... 1")
        self.assertEqual(first["asOf"], "2026-11-12T08:01:00Z")
        self.assertEqual(first["attribution"], META["attribution"])
        self.assertEqual(rows[1]["pdataUrl"], "https://pdata.world/events/kalshi/group:26NOV12ABC")
        self.assertEqual(rows[1]["volumeUnit"], "USD")

    def test_zero_outcomes_makes_a_single_request(self):
        opener = FakeOpener(
            {"/api/v1/events": {"_meta": META, "items": [event("myriad", "9", top_outcome="")]}}
        )
        rows = fetch_events(
            PdataApi(opener=opener), venue="myriad", outcomes_per_event=0, include_closed=True
        )
        self.assertEqual(len(opener.requests), 1)
        listing = query(opener.requests[0].full_url)
        self.assertEqual(listing["source"], "myriad")
        self.assertNotIn("closed", listing)
        self.assertEqual(rows[0]["outcomes"], [])
        self.assertIsNone(rows[0]["topOutcome"])
        self.assertIsNone(rows[0]["citeAs"])
        self.assertEqual(rows[0]["asOf"], META["as_of"])
        self.assertEqual(rows[0]["pdataUrl"], "https://pdata.world/events/myriad/9")
        self.assertEqual(rows[0]["volumeUnit"], "USD")

    def test_new_venues_and_manifold_use_the_documented_units(self):
        for venue, unit in (("xo", "USD"), ("manifold", "mana (play money)")):
            with self.subTest(venue=venue):
                opener = FakeOpener({"/api/v1/events": {"items": [event(venue, "1")]}})
                options = normalize_input({"venue": venue, "outcomesPerEvent": 0})
                rows = fetch_events(PdataApi(opener=opener), **options)
                self.assertEqual(query(opener.requests[0].full_url)["source"], venue)
                self.assertEqual(rows[0]["volumeUnit"], unit)

    def test_api_error_carries_the_code(self):
        body = json.dumps({"code": "unknown_param", "message": "Unknown query param(s)"})
        err = HTTPError("u", 400, "Bad Request", {}, io.BytesIO(body.encode()))
        opener = FakeOpener({"/api/v1/events": err})
        with self.assertRaises(ApiError) as caught:
            fetch_events(PdataApi(opener=opener))
        self.assertEqual((caught.exception.status, caught.exception.code), (400, "unknown_param"))

    def test_retries_a_503(self):
        calls = []

        def answer(url):
            calls.append(url)
            if len(calls) == 1:
                return HTTPError(url, 503, "Unavailable", {"Retry-After": "0"}, io.BytesIO(b""))
            return {"_meta": META, "items": []}

        opener = FakeOpener({"/api/v1/events": answer})
        self.assertEqual(fetch_events(PdataApi(opener=opener, sleep=lambda s: None)), [])
        self.assertEqual(len(calls), 2)

    def test_page_url_keeps_colon(self):
        self.assertEqual(
            event_page_url("kalshi", "group:26NOV12GUIERI"),
            "https://pdata.world/events/kalshi/group:26NOV12GUIERI",
        )


@unittest.skipUnless(os.environ.get("PDATA_LIVE"), "set PDATA_LIVE=1 to hit the live API")
class LiveTest(unittest.TestCase):
    def test_default_input_returns_rows(self):
        rows = fetch_events(PdataApi(), **normalize_input({"maxEvents": 3, "outcomesPerEvent": 2}))
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["pdataUrl"].startswith("https://pdata.world/events/") for r in rows))


if __name__ == "__main__":
    unittest.main()
