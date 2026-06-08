"""
discover_base.py — Abstract base class for discovery sources.

All discovery sources (Capterra, G2, Crunchbase, etc.) implement this
interface so the pipeline can call them uniformly.
"""

from abc import ABC, abstractmethod


class DiscoverySource(ABC):
    """
    Abstract base for SaaS company discovery.

    Each source returns a list of dicts with at minimum:
        - name: str
        - website_url: str
        - description: str (optional)
        - rating: float (optional)
        - review_count: int (optional)
        - employee_count: int (optional)
    """

    @abstractmethod
    def discover_category(self, category_slug, category_url, limit=200):
        """
        Discover companies from a single category.

        Args:
            category_slug: Short identifier like 'crm-software'
            category_url: Full URL of the category page
            limit: Max number of listings to return

        Returns:
            List of company dicts
        """
        ...

    @property
    @abstractmethod
    def source_name(self):
        """Return the source identifier, e.g. 'capterra', 'g2'."""
        ...
