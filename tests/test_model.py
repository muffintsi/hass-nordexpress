import json
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import load_modules  # noqa: F401
from nordexpress_test.const import validate_calendar_days
from nordexpress_test.model import (
    WARSAW,
    configured_directions,
    display_instant,
    instant,
    merge_live,
    normalize_directions,
    timetable,
    upcoming,
)
from nordexpress_test.presentation import calendar_records, zim_attributes

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8-sig"))


def payload(seconds=36000, symbols="", trip=1, index=0):
    return {
        "departures": [{"departure": seconds, "symbols": symbols, "trip_id": trip, "index": index}],
        "main_direction": {"name": "Słupsk"},
        "directions": [{"symbol": "A", "name": "Cecenowo"}],
        "platform": "1",
    }


def live(reference, **kwargs):
    row = {
        "trip_id": 1,
        "trip_index": 0,
        "line_name": "105",
        "time": "5 min",
        "is_estimated": True,
        "canceled": False,
        "direction_id": 5,
    }
    row.update(kwargs)
    return {"timestamp": reference.timestamp(), "rows": [row], "directions": {"5": "Słupsk"}}


class ModelTests(unittest.TestCase):
    def test_multiple_directions_are_sorted_together(self):
        day = date(2026, 11, 2)
        data = timetable(payload(36000), day, "105")
        data += timetable(payload(36600, symbols="A", trip=2), day, "105")
        data += timetable(payload(37200, trip=3), day, "105")
        selected = upcoming(data, ["Słupsk", "Cecenowo"], datetime(2026, 11, 2, 9, tzinfo=WARSAW))
        self.assertEqual([item.trip_id for item in selected], [1, 2, 3])
        attrs = zim_attributes(selected, {"line": "105", "stop_name": "Test"})
        self.assertEqual(attrs["Direction"], "Słupsk")
        self.assertEqual(attrs["NextBusDirection"], "Cecenowo")

    def test_multiple_calendar_directions_keep_individual_titles(self):
        now = datetime(2026, 11, 2, 9, tzinfo=WARSAW)
        data = timetable(payload(36000), now.date(), "105")
        data += timetable(payload(36600, symbols="A", trip=2), now.date(), "105")
        records = calendar_records(data, ["Słupsk", "Cecenowo"], now, now + timedelta(days=1))
        self.assertEqual(
            [row["summary"] for row in records], ["Linia 105 → Słupsk", "Linia 105 → Cecenowo"]
        )

    def test_legacy_single_direction_configuration(self):
        self.assertEqual(configured_directions({"direction": "Słupsk"}), ("Słupsk",))

    def test_options_override_original_directions(self):
        self.assertEqual(
            configured_directions({"direction": "Słupsk"}, {"directions": ["Słupsk", "Cecenowo"]}),
            ("Cecenowo", "Słupsk"),
        )

    def test_direction_selection_order_and_duplicates(self):
        self.assertEqual(
            normalize_directions(["Słupsk", "Cecenowo", "Słupsk"]), ("Cecenowo", "Słupsk")
        )

    def test_empty_direction_selection_rejected(self):
        for value in ([], [""], None, [1]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_directions(value)

    def setUp(self):
        self.day = date(2026, 11, 2)
        self.now = datetime(2026, 11, 2, 10, tzinfo=WARSAW)

    def test_real_fixture_variant(self):
        data = timetable(fixture("timetable_105_glowczyce"), self.day, "105")
        bus = next(item for item in data if item.scheduled.strftime("%H:%M") == "08:46")
        self.assertEqual(bus.direction, "Cecenowo")
        self.assertNotIn(bus, upcoming(data, "Słupsk, Dworzec Autobusowy", bus.scheduled))

    def test_symbols_can_include_non_direction_legend(self):
        data = timetable(payload(symbols="XA"), self.day, "105")
        self.assertEqual(data[0].direction, "Cecenowo")

    def test_previous_day_after_24_hours(self):
        data = timetable(payload(25 * 3600), self.day, "105")
        self.assertEqual(data[0].scheduled, datetime(2026, 11, 3, 1, tzinfo=WARSAW))

    def test_rollover_uses_service_date(self):
        data = timetable(payload(8 * 3600), self.day, "105")
        data += timetable(payload(8 * 3600), self.day + timedelta(days=1), "105")
        now = datetime(2026, 11, 3, 0, 1, tzinfo=WARSAW)
        self.assertEqual(upcoming(data, "Słupsk", now)[0].scheduled.date(), now.date())

    def test_day_without_departures_does_not_block_later_day(self):
        data = timetable({"departures": []}, self.day, "105")
        data += timetable(payload(), self.day + timedelta(days=2), "105")
        self.assertEqual(upcoming(data, "Słupsk", self.now)[0].scheduled.date(), date(2026, 11, 4))

    def test_unsorted_input(self):
        p = payload(40000)
        p["departures"] += payload(30000, trip=2)["departures"]
        self.assertEqual(timetable(p, self.day, "105")[0].trip_id, 2)

    def test_delay_keeps_scheduled_past_trip(self):
        data = timetable(payload(9 * 3600 + 50 * 60), self.day, "105")
        merged = merge_live(data, live(self.now), self.now)
        self.assertEqual(upcoming(merged, "Słupsk", self.now)[0].when.hour, 10)
        self.assertEqual(merged[0].when.minute, 5)
        self.assertEqual(merged[0].scheduled.hour, 9)

    def test_canceled_not_next(self):
        data = timetable(payload(), self.day, "105")
        merged = merge_live(data, live(self.now, canceled=True), self.now)
        self.assertTrue(merged[0].canceled)
        self.assertEqual(upcoming(merged, "Słupsk", self.now), [])

    def test_wrong_stop_index_is_not_merged(self):
        data = timetable(payload(index=7), self.day, "105")
        self.assertFalse(merge_live(data, live(self.now), self.now)[0].estimated)

    def test_reused_trip_id_different_day(self):
        data = timetable(payload(), self.day, "105")
        data += timetable(payload(), self.day + timedelta(days=1), "105")
        merged = merge_live(data, live(self.now), self.now)
        self.assertEqual(sum(item.estimated for item in merged), 1)
        self.assertFalse(merged[-1].estimated)

    def test_stale_live_rejected(self):
        with self.assertRaises(ValueError):
            merge_live([], live(self.now - timedelta(minutes=3)), self.now)

    def test_future_live_rejected(self):
        with self.assertRaises(ValueError):
            merge_live([], live(self.now + timedelta(minutes=3)), self.now)

    def test_unknown_live_format_preserves_schedule(self):
        merged = merge_live(
            timetable(payload(), self.day, "105"), live(self.now, time="???"), self.now
        )
        self.assertFalse(merged[0].estimated)
        self.assertIsNone(merged[0].expected)

    def test_relative_time_uses_server_timestamp(self):
        server = self.now - timedelta(seconds=20)
        merged = merge_live(timetable(payload(), self.day, "105"), live(server), self.now)
        self.assertEqual(merged[0].when, server + timedelta(minutes=5))

    def test_less_than_minute_is_imminent_and_expires(self):
        merged = merge_live(
            timetable(payload(), self.day, "105"), live(self.now, time="< 1 min"), self.now
        )
        self.assertTrue(upcoming(merged, "Słupsk", self.now + timedelta(seconds=30)))
        self.assertFalse(upcoming(merged, "Słupsk", self.now + timedelta(seconds=61)))

    def test_clock_time_crosses_midnight(self):
        now = datetime(2026, 11, 2, 23, 59, tzinfo=WARSAW)
        self.assertEqual(display_instant("00:05", now).date(), date(2026, 11, 3))

    def test_invalid_clock(self):
        self.assertIsNone(display_instant("25:15", self.now))

    def test_spring_dst_nonexistent_time_not_shifted(self):
        self.assertEqual(timetable(payload(2 * 3600 + 30 * 60), date(2026, 3, 29), "105"), [])

    def test_dst_day_preserves_8am_wall_time(self):
        item = timetable(payload(8 * 3600), date(2026, 3, 29), "105")[0]
        self.assertEqual(item.scheduled.hour, 8)
        self.assertEqual(item.scheduled.utcoffset(), timedelta(hours=2))

    def test_relative_time_during_autumn_fold(self):
        now = datetime(2026, 10, 25, 2, 55, tzinfo=WARSAW, fold=0)
        expected = display_instant("10 min", now)
        self.assertEqual(expected.fold, 1)
        self.assertEqual((instant(expected) - instant(now)).total_seconds(), 600)

    def test_zim_attribute_contract(self):
        data = timetable(payload(36000), self.day, "105")
        data += timetable(payload(40000, trip=2), self.day, "105")
        config = {
            "line": "105",
            "stop_name": "Główczyce",
            "stop_code": "51",
            "latitude": 54.6,
            "longitude": 17.3,
        }
        attrs = zim_attributes(data, config)
        self.assertEqual(attrs["BusHour"], "10:00")
        self.assertEqual(attrs["NextBusHour"], "11:06")
        self.assertEqual(attrs["NextBusTime"], "2026-11-02 11:06")
        self.assertEqual(
            set(attrs),
            {
                "line",
                "Direction",
                "BusHour",
                "NextBusDirection",
                "NextBusTime",
                "NextBusHour",
                "latitude",
                "longitude",
                "stop_name",
                "stop_code",
            },
        )

    def test_zim_empty_attributes(self):
        attrs = zim_attributes([], {"line": "105", "stop_name": "Główczyce"})
        self.assertIsNone(attrs["BusHour"])
        self.assertIsNone(attrs["NextBusHour"])

    def test_calendar_zim_titles_and_duration(self):
        data = timetable(payload(), self.day, "105")
        records = calendar_records(data, "Słupsk", self.now, self.now + timedelta(hours=1))
        self.assertEqual(records[0]["summary"], "Linia 105 → Słupsk")
        self.assertEqual(records[0]["end"] - records[0]["start"], timedelta(minutes=1))

    def test_calendar_exclusive_end_and_overlapping_start(self):
        data = timetable(payload(), self.day, "105")
        self.assertEqual(
            calendar_records(data, "Słupsk", self.now - timedelta(hours=1), self.now), []
        )
        self.assertTrue(
            calendar_records(
                data, "Słupsk", self.now + timedelta(seconds=30), self.now + timedelta(hours=1)
            )
        )

    def test_calendar_uses_planned_time(self):
        data = merge_live(timetable(payload(), self.day, "105"), live(self.now), self.now)
        records = calendar_records(data, "Słupsk", self.now, self.now + timedelta(hours=1))
        self.assertEqual(records[0]["start"], self.now)

    def test_calendar_days_validation(self):
        self.assertEqual(validate_calendar_days(14.0), 14)
        for value in (True, 0, 15, 2.5, "7", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_calendar_days(value)

    def test_saved_live_fixture_can_be_merged(self):
        p = fixture("live_105_glowczyce")
        now = datetime.fromtimestamp(p["timestamp"], timezone.utc)
        data = timetable(fixture("timetable_105_glowczyce"), self.day, "105")
        merged = merge_live(data, p, now)
        self.assertEqual(len(data), len(merged))
        self.assertTrue(any(item.estimated for item in merged))


if __name__ == "__main__":
    unittest.main()
