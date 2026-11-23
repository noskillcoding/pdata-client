"""Read prediction-market events with current prices from pdata.world's API.

Standard library only, so it runs and is tested without the Apify SDK; the
actor in ``main.py`` only reads the input and stores the rows this returns.

One request lists the events (``GET /api/v1/events``, most traded in the last
24 hours first). When outcomes are wanted, one more request per event reads
its markets (``GET /api/v1/events/{source}/{id}?markets_limit=N``), which the
API orders traded-in-the-last-24-hours first, then by probability.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

API_BASE = "https://api.pdata.world/api/v1"
SITE_BASE = "https://pdata.world"
USER_AGENT = "pdata-apify-actor/0.1 (+https://pdata.world/agents)"
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
MAX_EVENTS = 200  # the API's page_size cap
MAX_OUTCOMES = 50
MAX_SEARCH_LENGTH = 200
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})

Row = Dict[str, Any]


class InputError(ValueError):
    """The actor input cannot be used as given."""


class ApiError(RuntimeError):
    """An error answer from the pdata.world API."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(f"pdata.world API answered {status} {code}: {message}")
        self.status = status
        self.code = code


def normalize_input(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Check the actor input and return keyword arguments for ``fetch_events``.

    The platform validates input against ``.actor/input_schema.json`` before a
    run starts; this repeats the checks so local runs and tests fail the same way.
    """
    raw = raw or {}
    search = raw.get("search")
    if search is not None and not isinstance(search, str):
        raise InputError("search must be text")
    search = (search or "").strip() or None
    if search is not None and len(search) > MAX_SEARCH_LENGTH:
        raise InputError(f"search must be at most {MAX_SEARCH_LENGTH} characters")

    venue = raw.get("venue")
    venue = (venue or "").strip().lower() or None
    if venue is not None and venue not in VENUES:
        raise InputError(f"venue must be one of {', '.join(VENUES)}, not {venue!r}")

    def integer(key: str, default: int, low: int, high: int) -> int:
        value = raw.get(key, default)
        if value is None:
            value = default
        if isinstance(value, bool) or not isinstance(value, int):
            raise InputError(f"{key} must be a whole number")
        if not low <= value <= high:
            raise InputError(f"{key} must be between {low} and {high}, not {value}")
        return value

    include_closed = raw.get("includeClosed", False)
    if not isinstance(include_closed, bool):
        raise InputError("includeClosed must be true or false")

    return {
        "search": search,
        "venue": venue,
        "max_events": integer("maxEvents", 20, 1, MAX_EVENTS),
        "outcomes_per_event": integer("outcomesPerEvent", 5, 0, MAX_OUTCOMES),
        "include_closed": include_closed,
    }


class PdataApi:
    """Minimal GET client with retries on 429 and 5xx."""

    def __init__(
        self,
        base_url: str = API_BASE,
        *,
        timeout: float = 60.0,
        retries: int = 2,
        opener: Optional[Callable[..., Any]] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self._opener = opener or urlopen
        self._sleep = sleep

    def get(self, path: str, **params: Any) -> Any:
        query = urlencode([(k, str(v)) for k, v in params.items() if v is not None])
        url = f"{self.base_url}{path}" + (f"?{query}" if query else "")
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        attempt = 0
        while True:
            try:
                with self._opener(request, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except HTTPError as err:
                if err.code in _RETRY_STATUSES and attempt < self.retries:
                    retry_after = err.headers.get("Retry-After") if err.headers else None
                    self._sleep(float(retry_after) if retry_after else 2.0 * 2**attempt)
                    attempt += 1
                    continue
                raise _api_error(err) from None
            except URLError:
                if attempt < self.retries:
                    self._sleep(2.0 * 2**attempt)
                    attempt += 1
                    continue
                raise


def _api_error(err: HTTPError) -> ApiError:
    try:
        body = json.loads(err.read().decode("utf-8"))
    except (ValueError, OSError):
        body = {}
    if not isinstance(body, dict):
        body = {}
    message = body.get("message") or (json.dumps(body["detail"]) if "detail" in body else "")
    return ApiError(err.code, body.get("code") or "http_error", message or str(err.reason))


def _segment(value: Any) -> str:
    return quote(str(value), safe="")


def event_page_url(source: str, event_id: str) -> str:
    """The event's page on pdata.world (ids keep a literal ':', as the API's own links do)."""
    return f"{SITE_BASE}/events/{quote(source, safe='')}/{quote(event_id, safe=':')}"


def _outcome(market: Dict[str, Any]) -> Row:
    return {
        "outcomeName": market.get("group_item_title") or market.get("question"),
        "outcomeProbability": market.get("probability"),
        "outcomeChange24h": market.get("prob_24h_change"),
        "outcomeVolume24h": market.get("volume_24hr"),
        "outcomeClosed": market.get("closed"),
        "question": market.get("question"),
        "marketId": market.get("id"),
    }


def to_row(
    event: Dict[str, Any], detail: Optional[Dict[str, Any]], page_meta: Dict[str, Any]
) -> Row:
    """One dataset item: the event, its leading outcome and, if read, its outcomes."""
    source = str(event.get("source"))
    event_id = str(event.get("id"))
    detail_meta = (detail or {}).get("_meta") or {}
    markets = (detail or {}).get("markets") or []
    return {
        "title": event.get("title"),
        "venue": source,
        "eventId": event_id,
        # The API sends "" for some leading outcomes that have no label.
        "topOutcome": event.get("top_outcome") or None,
        "topOutcomeProbability": event.get("top_outcome_probability"),
        "topOutcomeChange24h": event.get("top_outcome_prob_24h_change"),
        "volume24h": event.get("volume_24hr"),
        "volumeUnit": "mana (play money)" if source == "manifold" else "USD",
        "endDate": event.get("end_date"),
        "closed": event.get("closed"),
        "categories": event.get("categories") or [],
        "outcomes": [_outcome(m) for m in markets],
        "outcomesTotal": (detail or {}).get("markets_total"),
        "pdataUrl": detail_meta.get("canonical_url") or event_page_url(source, event_id),
        "venueUrl": event.get("url"),
        "citeAs": detail_meta.get("cite_as"),
        "asOf": detail_meta.get("as_of") or page_meta.get("as_of"),
        "attribution": page_meta.get("attribution"),
    }


def fetch_events(
    api: PdataApi,
    *,
    search: Optional[str] = None,
    venue: Optional[str] = None,
    max_events: int = 20,
    outcomes_per_event: int = 5,
    include_closed: bool = False,
) -> List[Row]:
    """Events matching ``search`` and ``venue``, most traded in the last 24 hours first."""
    params: Dict[str, Any] = {"sort": "-volume_24hr", "page_size": max_events}
    if search:
        params["search"] = search
    if venue:
        params["source"] = venue
    if not include_closed:
        params["closed"] = "false"
    page = api.get("/events", **params)
    page_meta = page.get("_meta") or {}
    rows: List[Row] = []
    for event in (page.get("items") or [])[:max_events]:
        detail = None
        if outcomes_per_event > 0:
            detail = api.get(
                f"/events/{_segment(event['source'])}/{_segment(event['id'])}",
                markets_limit=outcomes_per_event,
            )
        rows.append(to_row(event, detail, page_meta))
    return rows
