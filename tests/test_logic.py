"""Tests for the pure logic: filters, the bounded duplicate cache, and task
state lifecycle. These cover the bugs that were fixed, so a regression fails
loudly.

Run with:  python -m unittest discover -s tests
"""

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("API_ID", "12345")
os.environ.setdefault("API_HASH", "dummy")
os.environ.setdefault("BOT_TOKEN", "123:ABC")
os.environ.setdefault("DATABASE_URI", "mongodb://localhost:27017")
os.environ.setdefault("BOT_OWNER", "999")

from config import temp  # noqa: E402
from plugins.regix import (  # noqa: E402
    _compile_extensions,
    _compile_list,
    extension_skip,
    get_size,
    keyword_skip,
    size_skip,
)
from plugins.utils import STATUS, STS, DupStore, status_size, sweep_status  # noqa: E402


def run(coro):
    return asyncio.run(coro)


class SizeFilterTests(unittest.TestCase):
    """The original bug: a max limit with min at its default 0 never applied."""

    def test_no_limits_never_skips(self):
        self.assertFalse(size_skip(0, 0, 500 * 1024 * 1024))

    def test_max_only_skips_larger_files(self):
        max_mb = 100
        self.assertTrue(size_skip(0, max_mb, 200 * 1024 * 1024))
        self.assertFalse(size_skip(0, max_mb, 50 * 1024 * 1024))

    def test_min_only_skips_smaller_files(self):
        self.assertTrue(size_skip(50, 0, 10 * 1024 * 1024))
        self.assertFalse(size_skip(50, 0, 80 * 1024 * 1024))

    def test_window_keeps_only_files_inside(self):
        self.assertTrue(size_skip(50, 100, 10 * 1024 * 1024))
        self.assertTrue(size_skip(50, 100, 500 * 1024 * 1024))
        self.assertFalse(size_skip(50, 100, 75 * 1024 * 1024))

    def test_boundaries_are_inclusive(self):
        self.assertFalse(size_skip(50, 100, 50 * 1024 * 1024))
        self.assertFalse(size_skip(50, 100, 100 * 1024 * 1024))

    def test_unknown_size_never_skips(self):
        self.assertFalse(size_skip(50, 100, None))
        self.assertFalse(size_skip(50, 100, 0))


class KeywordFilterTests(unittest.TestCase):
    def test_no_keywords_allows_everything(self):
        self.assertFalse(keyword_skip(None, "anything.mkv"))

    def test_matching_name_is_kept(self):
        pattern = _compile_list(["1080p", "hdrip"])
        self.assertFalse(keyword_skip(pattern, "Movie.1080p.mkv"))

    def test_non_matching_name_is_skipped(self):
        pattern = _compile_list(["1080p"])
        self.assertTrue(keyword_skip(pattern, "Movie.480p.mkv"))

    def test_match_is_case_insensitive(self):
        pattern = _compile_list(["HDRip"])
        self.assertFalse(keyword_skip(pattern, "movie.hdrip.mkv"))

    def test_unnamed_file_is_skipped_when_keywords_set(self):
        self.assertTrue(keyword_skip(_compile_list(["1080p"]), None))

    def test_special_characters_are_escaped_not_interpreted(self):
        # Without escaping, "a+b" would be an invalid/greedy regex.
        pattern = _compile_list(["a+b", "c(d"])
        self.assertFalse(keyword_skip(pattern, "file a+b here.mkv"))
        self.assertTrue(keyword_skip(pattern, "file aab here.mkv"))


class ExtensionFilterTests(unittest.TestCase):
    def test_no_extensions_allows_everything(self):
        self.assertFalse(extension_skip(None, "movie.mkv"))

    def test_blocked_extension_is_skipped(self):
        pattern = _compile_extensions([".mkv", ".avi"])
        self.assertTrue(extension_skip(pattern, "movie.mkv"))

    def test_allowed_extension_passes(self):
        pattern = _compile_extensions([".mkv"])
        self.assertFalse(extension_skip(pattern, "movie.mp4"))

    def test_dot_is_literal_not_a_wildcard(self):
        pattern = _compile_extensions([".mp4"])
        self.assertFalse(extension_skip(pattern, "movieXmp4"))

    def test_leading_dot_is_optional_when_configured(self):
        self.assertEqual(_compile_extensions(["mp4"]), _compile_extensions([".mp4"]))

    def test_match_is_case_insensitive(self):
        pattern = _compile_extensions(["mp4"])
        self.assertTrue(extension_skip(pattern, "Movie.MP4"))

    def test_only_matches_at_the_end_of_the_name(self):
        # The old un-anchored regex skipped this file too.
        pattern = _compile_extensions(["mp4"])
        self.assertFalse(extension_skip(pattern, "movie.mp4.part"))
        self.assertFalse(extension_skip(pattern, "mp4-collection.mkv"))

    def test_allow_mode_forwards_only_listed_extensions(self):
        pattern = _compile_extensions(["mkv", "mp4"])
        self.assertFalse(extension_skip(pattern, "movie.mkv", "allow"))
        self.assertFalse(extension_skip(pattern, "movie.mp4", "allow"))
        self.assertTrue(extension_skip(pattern, "movie.avi", "allow"))

    def test_allow_mode_skips_files_without_a_name(self):
        pattern = _compile_extensions(["mkv"])
        self.assertTrue(extension_skip(pattern, None, "allow"))

    def test_block_mode_keeps_files_without_a_name(self):
        pattern = _compile_extensions(["mkv"])
        self.assertFalse(extension_skip(pattern, None, "block"))

    def test_empty_list_compiles_to_nothing(self):
        self.assertIsNone(_compile_extensions([]))
        self.assertIsNone(_compile_extensions(["", ".", "  "]))


class FakeUserDB:
    """Stands in for plugins.db.MongoDB with an atomic ``mark``."""

    def __init__(self):
        self.stored = set()
        self.calls = 0

    async def mark(self, file_id):
        self.calls += 1
        existed = file_id in self.stored
        self.stored.add(file_id)
        return existed

    async def count(self):
        return len(self.stored)


class DupStoreTests(unittest.TestCase):
    """The store replaced an in-RAM set that grew with every file."""

    def test_first_sight_is_not_a_duplicate_second_is(self):
        store = DupStore("task-1", user_db=FakeUserDB())
        self.assertFalse(run(store.check_and_add("a")))
        self.assertTrue(run(store.check_and_add("a")))
        self.assertFalse(run(store.check_and_add("b")))

    def test_nothing_is_held_in_ram(self):
        store = DupStore("task-2", user_db=FakeUserDB())
        for i in range(1000):
            run(store.check_and_add(f"id{i}"))
        self.assertEqual(len(store), 0)

    def test_every_check_is_one_database_round_trip(self):
        fake = FakeUserDB()
        store = DupStore("task-3", user_db=fake)
        for i in range(10):
            run(store.check_and_add(f"id{i}"))
        self.assertEqual(fake.calls, 10)

    def test_empty_ids_are_ignored(self):
        fake = FakeUserDB()
        store = DupStore("task-4", user_db=fake)
        self.assertFalse(run(store.check_and_add(None)))
        self.assertFalse(run(store.check_and_add("")))
        self.assertEqual(fake.calls, 0)

    def test_hot_cache_answers_without_touching_the_database(self):
        fake = FakeUserDB()
        store = DupStore("task-5", user_db=fake, hot_limit=10)
        run(store.check_and_add("a"))       # 1 call, records it
        self.assertTrue(run(store.check_and_add("a")))  # served from RAM
        self.assertEqual(fake.calls, 1)
        self.assertEqual(len(store), 1)

    def test_hot_cache_stops_growing_at_its_limit(self):
        store = DupStore("task-6", user_db=FakeUserDB(), hot_limit=5)
        for i in range(50):
            run(store.check_and_add(f"id{i}"))
        self.assertEqual(len(store), 5)

    def test_database_errors_never_drop_a_message(self):
        class BrokenDB:
            async def mark(self, file_id):
                raise RuntimeError("mongo down")

        store = DupStore("task-7", user_db=BrokenDB())
        # Treated as unseen, so the file is forwarded rather than lost.
        self.assertFalse(run(store.check_and_add("a")))

    def test_counters_track_checks_and_hits(self):
        store = DupStore("task-8", user_db=FakeUserDB())
        run(store.check_and_add("a"))
        run(store.check_and_add("a"))
        self.assertEqual(store.checked, 2)
        self.assertEqual(store.hits, 1)

    def test_backend_reports_which_database_is_used(self):
        self.assertEqual(DupStore("k", user_db=FakeUserDB()).backend, "user-db")
        self.assertEqual(DupStore("k").backend, "bot-db")

    def test_clear_frees_everything(self):
        store = DupStore("task-9", user_db=FakeUserDB(), hot_limit=10)
        run(store.check_and_add("a"))
        store.clear()
        self.assertEqual(len(store), 0)


class TaskStateTests(unittest.TestCase):
    """STATUS used to grow one entry per /forward, forever."""

    def setUp(self):
        STATUS.clear()

    def tearDown(self):
        STATUS.clear()

    def test_store_then_release_leaves_nothing_behind(self):
        sts = STS("user-1").store("src", "dst", 0, 100)
        self.assertEqual(status_size(), 1)
        sts.release()
        self.assertEqual(status_size(), 0)

    def test_release_is_idempotent(self):
        sts = STS("user-1").store("src", "dst", 0, 100)
        sts.release()
        sts.release()
        self.assertEqual(status_size(), 0)

    def test_verify_reports_missing_state(self):
        sts = STS("ghost")
        self.assertFalse(sts.verify())

    def test_get_on_missing_state_returns_default_instead_of_raising(self):
        sts = STS("ghost")
        self.assertIsNone(sts.get("fetched"))
        self.assertEqual(sts.get("fetched", default=0), 0)

    def test_counters_increment(self):
        sts = STS("u").store("src", "dst", 0, 100)
        sts.add("fetched")
        sts.add("fetched", 4)
        self.assertEqual(sts.get("fetched"), 5)

    def test_total_defaults_to_the_id_span(self):
        sts = STS("u").store("src", "dst", 100, 600, start_id=100)
        self.assertEqual(sts.get("total"), 500)

    def test_explicit_total_wins(self):
        sts = STS("u").store("src", "dst", 0, 10000, total=42)
        self.assertEqual(sts.get("total"), 42)

    def test_fanout_targets_are_deduplicated_and_ordered(self):
        sts = STS("u").store("src", "main", 0, 10, extra_targets=["a", "b", "main"])
        self.assertEqual(sts.all_targets(), ["main", "a", "b"])

    def test_db_writes_are_rate_limited(self):
        sts = STS("u").store("src", "dst", 0, 100)
        self.assertTrue(sts.should_write_db(interval=3600))
        self.assertFalse(sts.should_write_db(interval=3600))

    def test_sweep_drops_stale_states(self):
        STS("old").store("src", "dst", 0, 10)
        STS("new").store("src", "dst", 0, 10)
        self.assertEqual(status_size(), 2)
        self.assertEqual(sweep_status(ttl=0), 2)
        self.assertEqual(status_size(), 0)

    def test_sweep_keeps_fresh_states(self):
        STS("fresh").store("src", "dst", 0, 10)
        self.assertEqual(sweep_status(ttl=3600), 0)
        self.assertEqual(status_size(), 1)

    def test_snapshot_is_a_copy(self):
        sts = STS("u").store("src", "dst", 0, 100)
        snap = sts.snapshot()
        snap["fetched"] = 999
        self.assertEqual(sts.get("fetched"), 0)


class TempStateTests(unittest.TestCase):
    """temp.lock / temp.CANCEL used to grow one entry per user, forever."""

    def setUp(self):
        temp.lock.clear()
        temp.CANCEL.clear()
        temp.IS_FRWD_CHAT.clear()

    def test_begin_then_end_leaves_nothing_behind(self):
        temp.begin_task(1, to_chat=-100)
        self.assertTrue(temp.is_locked(1))
        self.assertIn(-100, temp.IS_FRWD_CHAT)

        temp.end_task(1, to_chat=-100)
        self.assertFalse(temp.is_locked(1))
        self.assertEqual(len(temp.lock), 0)
        self.assertEqual(len(temp.CANCEL), 0)
        self.assertEqual(len(temp.IS_FRWD_CHAT), 0)

    def test_end_task_is_idempotent(self):
        temp.begin_task(1, to_chat=-100)
        temp.end_task(1, to_chat=-100)
        temp.end_task(1, to_chat=-100)  # must not raise
        self.assertEqual(len(temp.lock), 0)

    def test_discarding_an_absent_chat_does_not_raise(self):
        temp.end_task(42, to_chat=-999)

    def test_cancel_request_unlocks_and_flags(self):
        temp.begin_task(7)
        self.assertTrue(temp.request_cancel(7))
        self.assertTrue(temp.is_cancelled(7))
        self.assertFalse(temp.is_locked(7))

    def test_cancel_without_a_task_records_nothing(self):
        # An old cancel button used to leave a CANCEL entry behind forever.
        self.assertFalse(temp.request_cancel(1234))
        self.assertEqual(len(temp.CANCEL), 0)

    def test_ids_are_normalised_to_int(self):
        temp.begin_task("55")
        self.assertTrue(temp.is_locked(55))


class HelperTests(unittest.TestCase):
    def test_size_formatting(self):
        self.assertEqual(get_size(0), "0.00 Bytes")
        self.assertEqual(get_size(1024), "1.00 KB")
        self.assertEqual(get_size(1024 ** 3), "1.00 GB")

    def test_compile_list_handles_empties(self):
        self.assertIsNone(_compile_list(None))
        self.assertIsNone(_compile_list([]))
        self.assertIsNone(_compile_list(["", "  "]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
