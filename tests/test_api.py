import asyncio
import json
from datetime import date
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import load_modules  # noqa: F401
from nordexpress_test.api import NordExpressApi, NordExpressError


class ApiTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.response = Mock()
        self.response.raise_for_status = Mock()
        self.response.json = AsyncMock(return_value={"departures": []})
        context = Mock()
        context.__aenter__ = AsyncMock(return_value=self.response)
        context.__aexit__ = AsyncMock(return_value=False)
        self.session = Mock()
        self.session.get.return_value = context
        self.api = NordExpressApi(self.session)

    async def test_coalesces_concurrent_requests(self):
        await asyncio.gather(
            *(self.api.timetable("1301410:1360673", "105", date(2026, 11, 2)) for _ in range(5))
        )
        self.assertEqual(self.session.get.call_count, 1)

    async def test_date_is_part_of_cache_key(self):
        await self.api.timetable("a:b", "105", date(2026, 11, 2))
        await self.api.timetable("a:b", "105", date(2026, 11, 3))
        self.assertEqual(self.session.get.call_count, 2)

    async def test_base64_line_and_full_stop_id(self):
        await self.api.timetable("1301410:1360673", "105", date(2026, 11, 2))
        self.assertIn("/1301410:1360673/MTA1?date=2026-11-02", self.session.get.call_args.args[0])
        self.assertEqual(
            self.session.get.call_args.kwargs["headers"]["User-Agent"],
            "HomeAssistant/NordExpress-0.1.0",
        )

    async def test_http_failure_is_not_cached(self):
        self.response.raise_for_status.side_effect = aiohttp.ClientConnectionError("offline")
        for _ in range(2):
            with self.assertRaises(NordExpressError):
                await self.api.timetable("a:b", "105", date(2026, 11, 2))
        self.assertEqual(self.session.get.call_count, 2)

    async def test_bad_structure(self):
        self.response.json.return_value = {"departures": "error"}
        with self.assertRaises(NordExpressError):
            await self.api.timetable("a:b", "105", date(2026, 11, 2))

    async def test_bad_json(self):
        self.response.json.side_effect = json.JSONDecodeError("invalid", "x", 0)
        with self.assertRaises(NordExpressError):
            await self.api.timetable("a:b", "105", date(2026, 11, 2))

    async def test_timeout(self):
        self.response.json.side_effect = asyncio.TimeoutError()
        with self.assertRaises(NordExpressError):
            await self.api.timetable("a:b", "105", date(2026, 11, 2))

    async def test_stops_coordinates(self):
        self.response.json.return_value = {"stops": [["a:b", 51, "Główczyce", 17374931, 54619418]]}
        stops = await self.api.stops()
        self.assertEqual(stops[0]["id"], "a:b")
        self.assertAlmostEqual(stops[0]["latitude"], 54.619418)

    async def test_malformed_stop(self):
        self.response.json.return_value = {"stops": [["a:b"]]}
        with self.assertRaises(NordExpressError):
            await self.api.stops()

    async def test_expired_cache_pruned(self):
        await self.api.timetable("a:b", "105", date(2026, 11, 2))
        with patch("nordexpress_test.api.time", monotonic=lambda: 10**15):
            await self.api.timetable("a:b", "105", date(2026, 11, 3))
        self.assertEqual(len(self.api._cache), 1)

    async def test_cancellation_propagates(self):
        self.response.json.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.api.timetable("a:b", "105", date(2026, 11, 2))
