"""A small Python client for pdata.world, the prediction-market data API.

pdata.world collects prices, volumes and results from eight venues —
Polymarket, Kalshi, Manifold, Myriad, Limitless, Predict, Opinion and
Gemini — and serves them through one read-only API. No key, no signup.
The data is published under CC BY 4.0: use it, and credit pdata.world.

    >>> from pdata import Client
    >>> pd = Client()
    >>> page = pd.markets(source="kalshi", sort="-volume_24hr", page_size=5)
    >>> [m["question"] for m in page["items"]]

Standard library only (urllib + json + gzip), Python 3.9+.
"""

from __future__ import annotations

from .client import API_BASE, BULK_BASE, VENUES, Client, PdataError

__all__ = ["API_BASE", "BULK_BASE", "VENUES", "Client", "PdataError", "__version__"]
__version__ = "0.1.0"
