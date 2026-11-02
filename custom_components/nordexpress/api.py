"""Small asynchronous client with shared bounded caching and request coalescing."""

from __future__ import annotations

import asyncio
import base64
import time
from datetime import date
from urllib.parse import quote

import aiohttp

from .const import BASE_URL


class NordExpressError(Exception):
    """Network error or unexpected upstream contract."""


class NordExpressApi:
    def __init__(self, session: aiohttp.ClientSession, base_url: str = BASE_URL) -> None:
        self.session = session
        self.base_url = base_url
        self._cache: dict[str, tuple[float, dict]] = {}
        self._lock = asyncio.Lock()

    async def _get(self, path: str, ttl: int, field: str, kind: type) -> dict:
        async with self._lock:
            now = time.monotonic()
            # Prune expired data so dated timetable keys cannot grow forever.
            self._cache = {key: value for key, value in self._cache.items() if value[0] > now}
            if path in self._cache:
                return self._cache[path][1]
            try:
                async with self.session.get(
                    self.base_url + path,
                    headers={
                        "User-Agent": "HomeAssistant/NordExpress-0.1.0",
                        "Accept": "application/json",
                    },
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                if not isinstance(data, dict) or not isinstance(data.get(field), kind):
                    raise ValueError("Unexpected response structure")
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
                raise NordExpressError(f"Cannot read {path}: {error}") from error
            self._cache[path] = (time.monotonic() + ttl, data)
            return data

    async def stops(self) -> list[dict]:
        data = await self._get("/stops", 86400, "stops", list)
        try:
            return [
                {
                    "id": str(row[0]),
                    "number": row[1],
                    "name": str(row[2]),
                    "longitude": row[3] / 1e6,
                    "latitude": row[4] / 1e6,
                }
                for row in data["stops"]
            ]
        except (IndexError, TypeError, ValueError) as error:
            raise NordExpressError("Invalid stops") from error

    async def directions(self, stop: str, day: date) -> list[dict]:
        data = await self._get(
            f"/api/directions/{quote(stop, safe=':')}?date={day.isoformat()}",
            3600,
            "directions",
            list,
        )
        return data["directions"]

    async def timetable(self, stop: str, line: str, day: date) -> dict:
        encoded = base64.urlsafe_b64encode(line.encode()).decode().rstrip("=")
        return await self._get(
            f"/api/timetable/{quote(stop, safe=':')}/{encoded}?date={day.isoformat()}",
            3600,
            "departures",
            list,
        )

    async def departures(self, stop: str) -> dict:
        return await self._get(
            f"/api/departures/{quote(stop, safe=':')}",
            25,
            "rows",
            list,
        )
