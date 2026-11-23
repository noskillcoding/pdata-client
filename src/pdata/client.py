"""Client for pdata.world REST endpoints and nightly bulk files.

JSON methods return the API's data as plain dicts and lists, unchanged, so
the API reference at https://api.pdata.world/docs describes the fields.
Market and event lists return ``items``, pagination details in ``meta`` and
response metadata in ``_meta``. The ``iter_*`` methods walk the pages for you.

Probability and prices are 0-1. Volume is in US dollars on every venue except
Manifold, which uses play-money mana.
"""

from __future__ import annotations

import gzip
import json
import time
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, Callable, Literal, TypedDict, overload
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from ._version import __version__

API_BASE = "https://api.pdata.world/api/v1"
BULK_BASE = "https://api.pdata.world/bulk"
# Sent unless the caller passes its own; names the client and where to read
# about pdata.world's agent and API access.
USER_AGENT = f"pdata-client/{__version__} (+https://pdata.world/agents)"
VENUES = (
    "polymarket",
    "kalshi",
    "manifold",
    "myriad",
    "limitless",
    "predict",
    "opinion",
    "gemini",
    "hyperliquid",
    "mnx",
    "seer",
    "xo",
)
BULK_KINDS = ("markets-open", "events-open", "resolved", "resolved-markets")

# The API caps page_size at 200.
MAX_PAGE_SIZE = 200
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})

JSON = dict[str, Any]
View = Literal["lean", "full"]
HistoryInterval = Literal["auto", "1d"]


class VenueClock(TypedDict, total=False):
    checked_at: str | None
    cycle_period_s: float | None
    coverage: str | None


class StatusVenue(VenueClock):
    late: bool | None
    in_totals: bool


class ResponseMeta(TypedDict, total=False):
    venues: dict[str, VenueClock]
    as_of: str
    data_as_of: str | None
    canonical_url: str
    attribution: str
    docs: str
    cite_as: str


class StatusResponse(TypedDict):
    api_version: str
    as_of: str
    venues: dict[str, StatusVenue]
    _meta: ResponseMeta


class MarketRow(TypedDict, total=False):
    """Common market listing fields. The wire row can carry additional fields."""

    source: str
    id: str
    event_id: str
    question: str
    probability: float | None
    quotable: bool
    quote_tier: str | None
    volume_24hr: float | None
    checked_at: str | None
    pdata_url: str


class MarketsBatchResponse(TypedDict):
    items: list[MarketRow]
    not_found: list[str]
    _meta: ResponseMeta


class ComparePairsResponse(TypedDict):
    left: str
    right: str
    pairs: list[JSON]
    total: int
    matched: int
    method: str
    _meta: ResponseMeta


class PdataError(Exception):
    """An error answer from the API.

    ``code`` is the API's machine-readable code (``not_found``,
    ``unknown_param``, ``invalid_source``, ...) and ``message`` its
    explanation. An ``unknown_param`` message lists every allowed parameter.
    """

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(f"{status} {code}: {message}")
        self.status = status
        self.code = code
        self.message = message


def _encode(params: Mapping[str, Any]) -> str:
    """Query string: None dropped, booleans as true/false, sequences comma-joined."""
    out: list[tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            out.append((key, "true" if value else "false"))
        elif isinstance(value, (list, tuple, set, frozenset)):
            out.append((key, ",".join(str(v) for v in value)))
        else:
            out.append((key, str(value)))
    return urlencode(out)


def _seg(value: str) -> str:
    """One URL path segment (ids can hold characters that need escaping)."""
    return quote(str(value), safe="")


class Client:
    """pdata.world API client.

    Args:
        base_url: API root, default ``https://api.pdata.world/api/v1``.
        bulk_url: bulk-file root, default ``https://api.pdata.world/bulk``.
        timeout: seconds per request.
        retries: extra attempts on 429/5xx and network errors, with backoff.
        user_agent: sent on every request instead of ``USER_AGENT``; if you
            set one, name your project in it.
        opener: a ``urlopen``-compatible callable, for tests or a custom
            transport.
    """

    def __init__(
        self,
        base_url: str = API_BASE,
        *,
        bulk_url: str = BULK_BASE,
        timeout: float = 30.0,
        retries: int = 2,
        user_agent: str | None = None,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.bulk_url = bulk_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.user_agent = user_agent or USER_AGENT
        self._opener = opener or urlopen

    # ── transport ────────────────────────────────────────────────────────

    def _open(self, url: str) -> Any:
        request = Request(url, headers={"User-Agent": self.user_agent, "Accept": "*/*"})
        attempt = 0
        while True:
            try:
                return self._opener(request, timeout=self.timeout)
            except HTTPError as err:
                if err.code in _RETRY_STATUSES and attempt < self.retries:
                    retry_after = err.headers.get("Retry-After") if err.headers else None
                    time.sleep(float(retry_after) if retry_after else 1.5 * 2**attempt)
                    attempt += 1
                    continue
                raise self._error(err) from None
            except URLError:
                if attempt < self.retries:
                    time.sleep(1.5 * 2**attempt)
                    attempt += 1
                    continue
                raise

    @staticmethod
    def _error(err: HTTPError) -> PdataError:
        try:
            body = json.loads(err.read().decode("utf-8"))
        except (ValueError, OSError):
            body = {}
        code = body.get("code") or "http_error"
        message = body.get("message")
        if message is None and "detail" in body:  # request validation errors
            message = json.dumps(body["detail"])
        return PdataError(err.code, code, message or str(err.reason))

    def get(self, path: str, **params: Any) -> Any:
        """GET ``base_url + path`` with ``params``; returns the decoded JSON."""
        return json.loads(self._get_text(path, **params))

    def _get_text(self, path: str, **params: Any) -> str:
        query = _encode(params)
        url = f"{self.base_url}{path}" + (f"?{query}" if query else "")
        with self._open(url) as resp:
            return resp.read().decode("utf-8")

    def _iterate(self, path: str, max_items: int | None, params: dict[str, Any]) -> Iterator[JSON]:
        if params.get("limit") is None:
            params.setdefault("page_size", MAX_PAGE_SIZE)
        page = int(params.pop("page", 1))
        seen = 0
        while True:
            body = self.get(path, page=page, **params)
            items = body.get("items", [])
            for item in items:
                yield item
                seen += 1
                if max_items is not None and seen >= max_items:
                    return
            meta = body.get("meta") or {}
            if meta.get("total_counted") is False:
                if len(items) < int(meta.get("page_size") or MAX_PAGE_SIZE):
                    return
            elif page >= int(meta.get("total_pages") or page):
                return
            page += 1

    # ── markets ──────────────────────────────────────────────────────────

    def markets(
        self, *, limit: int | None = None, view: View | None = None, **filters: Any
    ) -> JSON:
        """One page of markets (``GET /markets``).

        Common filters: ``source`` (a venue or a list), ``search``,
        ``categories``, ``closed``, ``probability_min``/``_max``,
        ``volume_24hr_min``, ``ends_before``/``ends_after`` (ISO 8601),
        ``sort`` (e.g. ``"-volume_24hr"``, ``"-prob_24h_change"``), ``page``,
        ``page_size`` or ``limit`` (max 200). Set ``view="lean"`` for smaller
        rows. Market rows include quote quality in ``quote_tier`` when
        available. Venue clocks are under ``_meta.venues``.
        """
        return self.get("/markets", limit=limit, view=view, **filters)

    def iter_markets(
        self,
        max_items: int | None = None,
        *,
        limit: int | None = None,
        view: View | None = None,
        **filters: Any,
    ) -> Iterator[JSON]:
        """Every market matching ``filters``, page by page."""
        return self._iterate("/markets", max_items, dict(filters, limit=limit, view=view))

    def market(self, source: str, market_id: str) -> JSON:
        """One market by venue and id (``GET /markets/{source}/{market_id}``)."""
        return self.get(f"/markets/{_seg(source)}/{_seg(market_id)}")

    def markets_batch(self, ids: str | Sequence[str]) -> MarketsBatchResponse:
        """Fetch up to 50 ``source:market_id`` keys as a sequence or CSV string.

        Rows follow input order, with duplicates removed. Missing keys are
        reported in ``not_found``.
        """
        return self.get("/markets/batch", ids=ids if isinstance(ids, str) else ",".join(ids))

    def top_movers(
        self, limit: int | None = None, *, view: View | None = None, **filters: Any
    ) -> JSON:
        """Markets with the largest probability change over 24 hours."""
        return self.get("/markets/top-movers", limit=limit, view=view, **filters)

    def closing_soon(
        self, limit: int | None = None, *, view: View | None = None, **filters: Any
    ) -> JSON:
        """Markets closing soon, with optional status and sort filters."""
        return self.get("/markets/closing-soon", limit=limit, view=view, **filters)

    # ── events ───────────────────────────────────────────────────────────

    def events(
        self, *, limit: int | None = None, view: View | None = None, **filters: Any
    ) -> JSON:
        """One page of events. Use ``page_size`` or ``limit`` and optionally ``view="lean"``."""
        return self.get("/events", limit=limit, view=view, **filters)

    def iter_events(
        self,
        max_items: int | None = None,
        *,
        limit: int | None = None,
        view: View | None = None,
        **filters: Any,
    ) -> Iterator[JSON]:
        """Every event matching ``filters``, page by page."""
        return self._iterate("/events", max_items, dict(filters, limit=limit, view=view))

    def event(self, source: str, event_id: str, markets_limit: int | None = None) -> JSON:
        """One event with its markets.

        Events closed more than 10 days ago come back as
        ``{"kind": "tombstone", ...}`` with each top market's final result;
        live ones as ``{"kind": "live", ...}``. Check ``kind`` first.
        ``_meta.cite_as`` holds a ready-made citation sentence.
        """
        return self.get(
            f"/events/{_seg(source)}/{_seg(event_id)}", markets_limit=markets_limit
        )

    @overload
    def event_brief(self, source: str, event_id: str, *, format: Literal["md"]) -> str: ...

    @overload
    def event_brief(
        self, source: str, event_id: str, *, format: Literal["json"] = "json"
    ) -> JSON: ...

    def event_brief(
        self, source: str, event_id: str, *, format: Literal["md", "json"] = "json"
    ) -> JSON | str:
        """A compact event brief, as JSON by default or Markdown with ``format="md"``."""
        path = f"/events/{_seg(source)}/{_seg(event_id)}/brief"
        if format == "md":
            return self._get_text(path, format=format)
        return self.get(path, format=format)

    def event_history(
        self,
        source: str,
        event_id: str,
        range: str = "24h",
        market_id: str | None = None,
        limit: int | None = None,
        *,
        interval: HistoryInterval | None = None,
        max_points: int | None = None,
        markets_limit: int | None = None,
        page_size: int | None = None,
    ) -> JSON:
        """Price and 24h-volume series for an event's top markets.

        ``range`` is ``"24h"``, ``"7d"``, ``"30d"`` or ``"all"``.
        Use ``interval="1d"`` for daily buckets and ``max_points`` to target
        a smaller series. ``markets_limit`` caps the number of series and
        takes precedence over ``limit`` or its alias ``page_size``.
        """
        return self.get(
            f"/events/{_seg(source)}/{_seg(event_id)}/history",
            range=range,
            market_id=market_id,
            limit=limit,
            interval=interval,
            max_points=max_points,
            markets_limit=markets_limit,
            page_size=page_size,
        )

    def similar_events(
        self, source: str, event_id: str, limit: int | None = None, *, page_size: int | None = None
    ) -> JSON:
        """Events on other venues (and the same one) asking a similar question."""
        return self.get(
            f"/events/{_seg(source)}/{_seg(event_id)}/similar", limit=limit, page_size=page_size
        )

    def compare_pairs(
        self,
        left: Literal["polymarket", "kalshi"] = "polymarket",
        right: Literal["polymarket", "kalshi"] = "kalshi",
        limit: int | None = None,
        *,
        page_size: int | None = None,
    ) -> ComparePairsResponse:
        """Matched Polymarket and Kalshi prices with the largest gaps first."""
        return self.get("/compare/pairs", left=left, right=right, limit=limit, page_size=page_size)

    # ── search, summary, news ───────────────────────────────────────────

    def search(self, q: str, limit: int | None = None, *, page_size: int | None = None) -> JSON:
        """Events and markets whose titles match ``q``."""
        return self.get("/search/suggest", q=q, limit=limit, page_size=page_size)

    def status(self) -> StatusResponse:
        """API version, completed-cycle clocks, coverage and totals eligibility."""
        return self.get("/status")

    def summary(self) -> JSON:
        """Per-venue totals: open markets, events and 24h volume."""
        return self.get("/summary")

    def news_movers(self, *, limit: int | None = None, **filters: Any) -> JSON:
        """The /news feed: markets whose price moved most, scored by move and volume."""
        return self.get("/news/movers", limit=limit, **filters)

    # ── bulk files ───────────────────────────────────────────────────────

    def bulk_index(self) -> JSON:
        """The bulk-file index: each file's URL, row count, size, sha256 and time."""
        with self._open(f"{self.bulk_url}/index.json") as resp:
            return json.loads(resp.read().decode("utf-8"))

    def iter_bulk(self, kind: str, *, include_manifest: bool = False) -> Iterator[JSON]:
        """Stream a nightly bulk file, one record at a time.

        ``kind`` is ``"markets-open"``, ``"events-open"``, ``"resolved"`` or
        ``"resolved-markets"``.
        Line 1 of each file is a manifest (``{"_manifest": {...}}``) giving
        the licence and every field's meaning and unit; it is skipped unless
        ``include_manifest`` is true. Nothing is written to disk.
        """
        if kind not in BULK_KINDS:
            raise ValueError(f"kind must be one of {BULK_KINDS}, not {kind!r}")
        url = f"{self.bulk_url}/{kind}-latest.jsonl.gz"
        with self._open(url) as resp, gzip.GzipFile(fileobj=resp) as lines:
            for i, line in enumerate(lines):
                row = json.loads(line)
                if i == 0 and "_manifest" in row and not include_manifest:
                    continue
                yield row
