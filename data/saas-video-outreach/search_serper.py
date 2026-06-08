"""
search_serper.py — Serper.dev search provider implementation.

Uses Serper.dev's Google Search API for video search results.
"""

import requests

from search_base import SearchProvider
from utils import retry, log


class SerperProvider(SearchProvider):
    """Search provider using Serper.dev API."""

    BASE_URL = "https://google.serper.dev"

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        }

    @retry(max_attempts=3, delay=3, exceptions=(requests.RequestException,))
    def video_search(self, query, num_results=10):
        """Search Google Videos via Serper."""
        resp = requests.post(
            f"{self.BASE_URL}/videos",
            headers=self.headers,
            json={"q": query, "num": num_results},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("videos", []):
            results.append({
                "url": item.get("link", ""),
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "duration": item.get("duration", ""),
                "source": item.get("source", ""),
            })
        return results

    @retry(max_attempts=3, delay=3, exceptions=(requests.RequestException,))
    def web_search(self, query, num_results=10):
        """General web search via Serper."""
        resp = requests.post(
            f"{self.BASE_URL}/search",
            headers=self.headers,
            json={"q": query, "num": num_results},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("organic", []):
            results.append({
                "url": item.get("link", ""),
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
            })
        return results
