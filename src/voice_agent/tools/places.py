"""Place-search application boundary used by LiveKit function tools."""

from __future__ import annotations

from src.backend.services.place_search_service import PlaceSearchService
from src.voice_agent.session_data import PlaceCandidate


class PlaceToolsService:
    def __init__(self, search_service: PlaceSearchService | None = None) -> None:
        self._search_service = search_service or PlaceSearchService()

    def search(self, query: str, *, limit: int = 5) -> list[PlaceCandidate]:
        return [
            PlaceCandidate.model_validate(candidate)
            for candidate in self._search_service.search(query.strip(), limit=limit)
        ]

    async def search_async(self, query: str, *, limit: int = 5) -> list[PlaceCandidate]:
        """Async boundary for latency-sensitive voice turns.

        The active Hanoi gazetteer is local and non-blocking. A future network
        map provider must implement its I/O natively behind this awaited
        boundary instead of running a synchronous request on the event loop.
        """

        return self.search(query, limit=limit)
