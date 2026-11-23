"""Offline tests: a fake opener stands in for the network.

Set PDATA_LIVE=1 to also run the live smoke test against api.pdata.world.
"""

from __future__ import annotations

import gzip
import io
import json
import os
import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pdata
from pdata import Client, PdataError


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class FakeOpener:
    """Answers each URL path from a dict; records every request."""

    def __init__(self, routes):
        self.routes = routes
        self.urls = []
        self.requests = []

    def __call__(self, request, timeout=None):
        url = request.full_url
        self.urls.append(url)
        self.requests.append(request)
        answer = self.routes[urlsplit(url).path]
        if callable(answer):
            answer = answer(url)
        if isinstance(answer, HTTPError):
            raise answer
        if isinstance(answer, bytes):
            return FakeResponse(answer)
        return FakeResponse(json.dumps(answer).encode())


def page(items, page_no, total_pages):
    return {"items": items, "meta": {"page": page_no, "total_pages": total_pages}}


def query(url):
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


class ClientTests(unittest.TestCase):
    def test_params_are_encoded(self):
        opener = FakeOpener({"/api/v1/markets": page([], 1, 1)})
        Client(opener=opener).markets(
            source=["kalshi", "polymarket"], closed=False, search=None, sort="-volume_24hr"
        )
        q = query(opener.urls[0])
        self.assertEqual(q["source"], "kalshi,polymarket")
        self.assertEqual(q["closed"], "false")
        self.assertEqual(q["sort"], "-volume_24hr")
        self.assertNotIn("search", q)

    def test_default_user_agent_names_client_version_and_agents_page(self):
        opener = FakeOpener({"/api/v1/summary": {}})
        Client(opener=opener).summary()
        Client(opener=opener, user_agent="my-project/2.0").summary()
        sent = [r.get_header("User-agent") for r in opener.requests]
        self.assertEqual(
            sent[0], f"pdata-client/{pdata.__version__} (+https://pdata.world/agents)"
        )
        self.assertEqual(sent[1], "my-project/2.0")

    def test_iter_markets_walks_pages_and_stops_at_max_items(self):
        def answer(url):
            n = int(query(url)["page"])
            return page([{"id": f"{n}-{i}"} for i in range(2)], n, 3)

        opener = FakeOpener({"/api/v1/markets": answer})
        client = Client(opener=opener)
        ids = [m["id"] for m in client.iter_markets(source="kalshi")]
        self.assertEqual(ids, ["1-0", "1-1", "2-0", "2-1", "3-0", "3-1"])
        self.assertEqual(query(opener.urls[0])["page_size"], "200")

        opener.urls.clear()
        self.assertEqual(len(list(client.iter_markets(max_items=3))), 3)
        self.assertEqual(len(opener.urls), 2)

    def test_ids_are_escaped_as_one_path_segment(self):
        opener = FakeOpener({"/api/v1/events/kalshi/A%2FB/history": {"series": []}})
        Client(opener=opener).event_history("kalshi", "A/B", range="7d")
        self.assertEqual(query(opener.urls[0]), {"range": "7d"})

    def test_lean_iterator_uses_limit_without_adding_a_conflicting_page_size(self):
        def answer(url):
            n = int(query(url)["page"])
            return {
                "items": [{"id": str(n)}] if n < 3 else [],
                "meta": {"page_size": 1, "total_pages": 0, "total_counted": False},
            }

        opener = FakeOpener({"/api/v1/events": answer})
        client = Client(opener=opener)
        self.assertEqual(
            [item["id"] for item in client.iter_events(limit=1, view="lean")], ["1", "2"]
        )
        self.assertEqual(
            [query(url) for url in opener.urls],
            [{"page": str(n), "limit": "1", "view": "lean"} for n in range(1, 4)],
        )

    def test_lean_lists_preserve_quote_tier_and_venue_clocks(self):
        payload = page([{"id": "m1", "quote_tier": "thin"}], 1, 1)
        payload["_meta"] = {
            "venues": {"kalshi": {"checked_at": "2026-11-23T17:00:00Z", "coverage": "full"}}
        }
        opener = FakeOpener({
            f"/api/v1/{route}": payload
            for route in ("events", "markets", "markets/top-movers", "markets/closing-soon")
        })
        client = Client(opener=opener)
        for method in (client.events, client.markets, client.top_movers, client.closing_soon):
            self.assertEqual(method(limit=1, view="lean"), payload)
            self.assertEqual(query(opener.urls[-1]), {"limit": "1", "view": "lean"})

    def test_status_and_batch_keep_server_fields(self):
        status = {
            "api_version": "2.18.0",
            "venues": {"xo": {"checked_at": None, "late": None, "in_totals": False}},
        }
        batch = {
            "items": [{"source": "kalshi", "id": "A/B", "quote_tier": "firm"}],
            "not_found": ["xo:missing"],
        }
        opener = FakeOpener({"/api/v1/status": status, "/api/v1/markets/batch": batch})
        client = Client(opener=opener)
        self.assertEqual(client.status(), status)
        self.assertEqual(client.markets_batch(["kalshi:A/B", "xo:missing"]), batch)
        self.assertEqual(query(opener.urls[-1]), {"ids": "kalshi:A/B,xo:missing"})
        self.assertEqual(client.markets_batch("kalshi:A/B,xo:missing"), batch)
        self.assertEqual(opener.urls[-1], opener.urls[-2])

    def test_brief_can_return_markdown_or_json(self):
        def answer(url):
            if query(url)["format"] == "md":
                return "# Question — Markdown\n".encode()
            return {"title": "Question"}

        opener = FakeOpener({"/api/v1/events/kalshi/A%2FB/brief": answer})
        client = Client(opener=opener)
        self.assertEqual(client.event_brief("kalshi", "A/B"), {"title": "Question"})
        self.assertEqual(
            client.event_brief("kalshi", "A/B", format="md"), "# Question — Markdown\n"
        )

    def test_history_compare_and_news_forward_aliases_and_options(self):
        opener = FakeOpener({
            "/api/v1/events/kalshi/X/history": {"series": []},
            "/api/v1/compare/pairs": {"pairs": []},
            "/api/v1/news/movers": {"results": []},
        })
        client = Client(opener=opener)
        client.event_history(
            "kalshi", "X", "30d", "M", 2, interval="1d", max_points=30,
            markets_limit=1, page_size=2,
        )
        client.compare_pairs("kalshi", "polymarket", page_size=5)
        client.news_movers(limit=3)
        self.assertEqual(
            [query(url) for url in opener.urls],
            [
                {
                    "range": "30d", "market_id": "M", "limit": "2", "interval": "1d",
                    "max_points": "30", "markets_limit": "1", "page_size": "2",
                },
                {"left": "kalshi", "right": "polymarket", "page_size": "5"},
                {"limit": "3"},
            ],
        )

    def test_api_error_becomes_pdata_error(self):
        body = json.dumps({"code": "not_found", "message": "Event not found: kalshi/X"})
        err = HTTPError("u", 404, "Not Found", {}, io.BytesIO(body.encode()))
        opener = FakeOpener({"/api/v1/events/kalshi/X": err})
        with self.assertRaises(PdataError) as caught:
            Client(opener=opener).event("kalshi", "X")
        self.assertEqual(caught.exception.status, 404)
        self.assertEqual(caught.exception.code, "not_found")

    def test_retries_a_503_then_succeeds(self):
        calls = []

        def answer(url):
            calls.append(url)
            if len(calls) == 1:
                return HTTPError(url, 503, "Unavailable", {"Retry-After": "0"}, io.BytesIO(b""))
            return {"ok": True}

        opener = FakeOpener({"/api/v1/summary": answer})
        self.assertEqual(Client(opener=opener).summary(), {"ok": True})
        self.assertEqual(len(calls), 2)

    def test_iter_bulk_skips_the_manifest_line(self):
        lines = [{"_manifest": {"license": "CC BY 4.0"}}, {"id": "a"}, {"id": "b"}]
        blob = gzip.compress("\n".join(json.dumps(x) for x in lines).encode())
        opener = FakeOpener({"/bulk/resolved-latest.jsonl.gz": blob})
        client = Client(opener=opener)
        self.assertEqual([r["id"] for r in client.iter_bulk("resolved")], ["a", "b"])
        first = next(client.iter_bulk("resolved", include_manifest=True))
        self.assertEqual(first["_manifest"]["license"], "CC BY 4.0")
        with self.assertRaises(ValueError):
            list(client.iter_bulk("everything"))


@unittest.skipUnless(os.environ.get("PDATA_LIVE"), "set PDATA_LIVE=1 to hit the live API")
class LiveSmokeTest(unittest.TestCase):
    def test_live_endpoints_answer(self):
        client = Client()
        top = client.markets(sort="-volume_24hr", page_size=3)
        self.assertEqual(len(top["items"]), 3)
        first = top["items"][0]
        event = client.event(first["source"], first["event_id"], markets_limit=1)
        self.assertIn(event["kind"], ("live", "tombstone"))
        self.assertTrue(client.summary())
        self.assertIn("files", client.bulk_index())


if __name__ == "__main__":
    unittest.main()
