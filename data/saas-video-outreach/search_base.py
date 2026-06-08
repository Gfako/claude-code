"""
search_base.py — Abstract base class for search providers.

Supports swappable search backends (Serper, SerpAPI, Google CSE, etc.)
Config selects provider: search_provider: "serper" in config.yaml
"""

from abc import ABC, abstractmethod


class SearchProvider(ABC):
    """
    Abstract base for web/video search providers.
    """

    @abstractmethod
    def video_search(self, query, num_results=10):
        """
        Search for videos matching query.

        Returns list of dicts:
            - url: str (page URL or video URL)
            - title: str
            - snippet: str (optional)
        """
        ...

    @abstractmethod
    def web_search(self, query, num_results=10):
        """
        General web search.

        Returns list of dicts:
            - url: str
            - title: str
            - snippet: str (optional)
        """
        ...
