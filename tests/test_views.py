"""View synchronization unit tests: all API responses are mocked.

No request, badge load, or counter increment is performed by these tests.
"""

from contextlib import redirect_stdout
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError, URLError


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/sync_views.py"
SPEC = importlib.util.spec_from_file_location("sync_views", MODULE_PATH)
sync_views = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync_views)


def response(payload):
    return io.BytesIO(json.dumps(payload).encode("utf-8"))


class FetchCountTests(unittest.TestCase):
    def test_positive_count_uses_only_read_api(self):
        opener = Mock(return_value=response({"total": 42}))
        self.assertEqual(sync_views.fetch_count("test-article", opener), 42)
        request = opener.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://hits.sh/api/urns/ssy671.github.io/dogu-life-preview/post/test-article",
        )
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertIn("DoguLife", request.get_header("User-agent"))
        self.assertEqual(opener.call_args.kwargs, {"timeout": 10})

    def test_unseen_counter_is_zero(self):
        opener = Mock(side_effect=HTTPError("https://example.invalid", 404, "Not Found", {}, None))
        self.assertEqual(sync_views.fetch_count("new-article", opener), 0)

    def test_invalid_counts_are_rejected(self):
        for invalid in [-1, True, False, 1.2, "42", None]:
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                sync_views.fetch_count("test-article", Mock(return_value=response({"total": invalid})))

    def test_invalid_payloads_are_rejected(self):
        for payload in [{}, [], {"total": -10}]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                sync_views.fetch_count("test-article", Mock(return_value=response(payload)))

    def test_invalid_slug_never_calls_api(self):
        opener = Mock()
        with self.assertRaises(ValueError):
            sync_views.fetch_count("../test.svg", opener)
        opener.assert_not_called()


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.posts = self.root / "posts.json"
        self.views = self.root / "views.json"
        self.original = {"updated_at": "2026-10-14T00:00:00Z", "counts": {"article": 17, "other": 8}}
        self.posts.write_text(json.dumps([{"slug": "article"}]), encoding="utf-8")
        self.views.write_text(json.dumps(self.original), encoding="utf-8")

    def run_sync(self, opener):
        with redirect_stdout(io.StringIO()):
            return sync_views.sync(
                self.posts,
                self.views,
                opener=opener,
                now=datetime(2026, 10, 15, 1, 2, 3, tzinfo=timezone.utc),
            )

    def test_positive_update_preserves_other_counts(self):
        result = self.run_sync(Mock(return_value=response({"total": 23})))
        self.assertEqual(result["counts"], {"article": 23, "other": 8})
        self.assertEqual(result["updated_at"], "2026-10-15T01:02:03Z")
        self.assertEqual(json.loads(self.views.read_text(encoding="utf-8")), result)

    def test_404_does_not_reset_previously_counted_article(self):
        result = self.run_sync(Mock(side_effect=HTTPError("https://example.invalid", 404, "Not Found", {}, None)))
        self.assertEqual(result["counts"]["article"], 17)
        self.assertEqual(result["updated_at"], self.original["updated_at"])

    def test_unchanged_counts_do_not_rewrite_the_snapshot(self):
        before = self.views.read_bytes()
        result = self.run_sync(Mock(return_value=response({"total": 17})))
        self.assertEqual(result, self.original)
        self.assertEqual(self.views.read_bytes(), before)

    def test_404_initializes_new_article_at_zero(self):
        self.posts.write_text(json.dumps([{"slug": "new-article"}]), encoding="utf-8")
        result = self.run_sync(Mock(side_effect=HTTPError("https://example.invalid", 404, "Not Found", {}, None)))
        self.assertEqual(result["counts"]["new-article"], 0)
        self.assertEqual(result["counts"]["article"], 17)

    def test_successful_smaller_count_cannot_reset_counts(self):
        result = self.run_sync(Mock(return_value=response({"total": 0})))
        self.assertEqual(result["counts"]["article"], 17)

    def test_timeout_keeps_snapshot_and_timestamp_unchanged(self):
        before = self.views.read_bytes()
        result = self.run_sync(Mock(side_effect=TimeoutError("mock timeout")))
        self.assertEqual(result, self.original)
        self.assertEqual(self.views.read_bytes(), before)

    def test_bad_json_keeps_snapshot_and_timestamp_unchanged(self):
        before = self.views.read_bytes()
        result = self.run_sync(Mock(return_value=io.BytesIO(b"not json")))
        self.assertEqual(result, self.original)
        self.assertEqual(self.views.read_bytes(), before)

    def test_http_503_and_network_errors_keep_existing_values(self):
        for error in [
            HTTPError("https://example.invalid", 503, "Unavailable", {}, None),
            URLError("mock network failure"),
        ]:
            with self.subTest(error=error):
                self.assertEqual(self.run_sync(Mock(side_effect=error)), self.original)

    def test_negative_response_keeps_existing_snapshot(self):
        result = self.run_sync(Mock(return_value=response({"total": -1})))
        self.assertEqual(result, self.original)

    def test_partial_success_updates_timestamp_and_keeps_failed_article(self):
        self.posts.write_text(json.dumps([{"slug": "article"}, {"slug": "another"}]), encoding="utf-8")

        def fake_api(request, timeout):
            if request.full_url.endswith("/another"):
                return response({"total": 5})
            raise TimeoutError("mock timeout")

        result = self.run_sync(Mock(side_effect=fake_api))
        self.assertEqual(result["counts"], {"article": 17, "other": 8, "another": 5})
        self.assertEqual(result["updated_at"], "2026-10-15T01:02:03Z")

    def test_no_posts_makes_no_requests_and_keeps_timestamp(self):
        self.posts.write_text("[]", encoding="utf-8")
        opener = Mock()
        before = self.views.read_bytes()
        self.assertEqual(self.run_sync(opener), self.original)
        opener.assert_not_called()
        self.assertEqual(self.views.read_bytes(), before)

    def test_missing_snapshot_is_created_after_success(self):
        self.views.unlink()
        result = self.run_sync(Mock(return_value=response({"total": 3})))
        self.assertEqual(result["counts"], {"article": 3})
        self.assertTrue(self.views.exists())


if __name__ == "__main__":
    unittest.main()
