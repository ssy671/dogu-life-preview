import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts.check_publication import publication_health
from scripts.publish import release


class PublicationHealthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'content').mkdir()
        self.posts = [{'slug': 'old', 'published_at': '2026-10-26T09:00:00+09:00'}]
        self.queue = [{'slug': f'new-{i}'} for i in range(9)]
        self.state = {'last_release_date': '2026-10-26', 'publish_hour': 9, 'daily_limit': 3}
        self.write()

    def write(self):
        for name, value in [('posts.json', self.posts), ('queue.json', self.queue),
                            ('state.json', self.state)]:
            (self.root / 'content' / name).write_text(json.dumps(value))

    def check(self, stamp='2026-10-27T09:30:00+09:00'):
        before = {p.name: p.read_bytes() for p in (self.root / 'content').iterdir()}
        result = publication_health(self.root, datetime.fromisoformat(stamp))
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.root / 'content').iterdir()})
        return result

    def test_before_hour_is_not_a_failure(self):
        result = self.check('2026-10-26T23:59:59+00:00')
        self.assertTrue(result['ok'])
        self.assertEqual(result['reason'], 'before_publication_hour')

    def test_missing_publication_is_a_failure_from_nine(self):
        result = self.check('2026-10-27T00:00:00+00:00')
        self.assertFalse(result['ok'])
        self.assertEqual(result['reason'], 'missing_publication')

    def test_short_queue_cannot_report_success_after_release_skips(self):
        self.queue = self.queue[:2]
        self.write()
        now = datetime.fromisoformat('2026-10-27T09:23:00+09:00')
        self.assertEqual(release(self.root, now)['published'], 0)
        self.assertFalse(self.check()['ok'])

    def test_successful_release_and_retry_are_healthy(self):
        now = datetime.fromisoformat('2026-10-27T09:23:00+09:00')
        self.assertEqual(release(self.root, now)['published'], 3)
        self.assertTrue(self.check()['ok'])
        self.assertEqual(release(self.root, now)['published'], 0)
        self.assertTrue(self.check()['ok'])

    def test_partial_and_excess_publication_fail(self):
        for count in (1, 2, 4):
            with self.subTest(count=count):
                self.posts = [{'slug': f'today-{i}', 'published_at': '2026-10-27T09:00:00+09:00'}
                              for i in range(count)]
                self.write()
                self.assertFalse(self.check()['ok'])

    def test_state_cannot_claim_a_release_without_articles(self):
        self.state['last_release_date'] = '2026-10-27'
        self.write()
        self.assertEqual(self.check()['reason'], 'release_date_without_articles')

    def test_stale_or_future_state_is_detected(self):
        self.posts = [{'slug': f'today-{i}', 'published_at': '2026-10-27T09:00:00+09:00'}
                      for i in range(3)]
        self.write()
        self.assertEqual(self.check()['reason'], 'release_date_mismatch')
        self.state['last_release_date'] = '2026-10-28'
        self.write()
        self.assertEqual(self.check()['reason'], 'future_release_date')

    def test_duplicate_published_slugs_fail(self):
        self.posts *= 2
        self.write()
        self.assertEqual(self.check()['reason'], 'duplicate_published_slugs')

    def test_invalid_limit_fails(self):
        self.state['daily_limit'] = 4
        self.write()
        self.assertEqual(self.check()['reason'], 'invalid_daily_limit')


if __name__ == '__main__':
    unittest.main()
