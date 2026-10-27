import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import notify_telegram as notify


class TelegramReportTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / 'content').mkdir()
        self.marker = self.root / 'content' / notify.MARKER
        self.sender, self.persist = Mock(), Mock()
        self.outcomes = {'publish': 'success', 'verify': 'success', 'checkpoint': 'success'}
        self.health = {'ok': True, 'today_count': 3, 'remaining': 9,
                       'date': '2026-10-28', 'reason': 'published_today'}
        self.addCleanup(patch.stopall)
        patch.object(notify, 'publication_health', return_value=self.health).start()
        patch.object(notify, 'deployment_state', return_value={'status': 'verified', 'fingerprint': 'version'}).start()
        patch.object(notify, 'render_fingerprint', return_value='version').start()

    def deliver(self, time='09:02:00'):
        return notify.deliver_once(self.root, datetime.fromisoformat(f'2026-10-28T{time}+09:00'),
                                   self.outcomes, '1234', self.sender, self.persist)

    def test_success_after_verification_and_same_day_retry(self):
        self.assertEqual(self.deliver(), 'sent')
        self.assertEqual(self.deliver('10:07:00'), 'already_attempted_today')
        self.sender.assert_called_once()
        self.assertIn('발행 정상', self.sender.call_args.args[0])
        self.assertEqual(json.loads(self.marker.read_text())['status'], 'sent')
        self.assertEqual(set(json.loads(self.marker.read_text())), {'date', 'status', 'updated_at', 'run_id'})

    def test_no_report_before_nine(self):
        self.assertEqual(self.deliver('08:59:59'), 'before_publication_hour')
        self.sender.assert_not_called()
        self.persist.assert_not_called()

    def test_failure_waits_for_extra_retry_then_reports(self):
        self.outcomes['verify'] = 'failure'
        self.assertEqual(self.deliver(), 'waiting_for_morning_retry')
        self.assertEqual(self.deliver('09:24:00'), 'sent')
        self.assertIn('확인 필요', self.sender.call_args.args[0])

    def test_timeout_does_not_duplicate_on_next_run(self):
        self.sender.side_effect = TimeoutError('private endpoint')
        with self.assertRaisesRegex(RuntimeError, 'not confirmed'):
            self.deliver()
        self.assertEqual(json.loads(self.marker.read_text())['status'], 'uncertain')
        self.assertEqual(self.deliver('10:07:00'), 'already_attempted_today')
        self.sender.assert_called_once()

    def test_failed_reservation_never_sends(self):
        self.persist.side_effect = RuntimeError('state conflict')
        with self.assertRaises(RuntimeError):
            self.deliver()
        self.sender.assert_not_called()

    def test_old_marker_allows_next_day(self):
        self.marker.write_text(json.dumps({'date': '2026-10-27', 'status': 'sent'}))
        self.assertEqual(self.deliver(), 'sent')

    def test_skipped_repeat_checks_can_reuse_verified_deployment(self):
        self.outcomes.update(verify='skipped', checkpoint='skipped')
        self.assertEqual(self.deliver(), 'sent')
        self.assertIn('발행 정상', self.sender.call_args.args[0])

    def test_stale_fingerprint_is_not_reported_as_healthy(self):
        notify.render_fingerprint.return_value = 'changed'
        self.assertEqual(self.deliver('10:07:00'), 'sent')
        self.assertIn('확인 필요', self.sender.call_args.args[0])

    def test_unreadable_articles_produce_warning_report(self):
        notify.publication_health.side_effect = ValueError('bad data')
        self.assertEqual(self.deliver('10:07:00'), 'sent')
        self.assertIn('확인 불가', self.sender.call_args.args[0])

    def test_transport_errors_never_expose_token(self):
        token = '123456:TEST_SECRET'
        with patch.object(notify.urllib.request, 'urlopen', side_effect=OSError(token)):
            with self.assertRaises(RuntimeError) as error:
                notify.send_message(token, '1234', 'test')
        self.assertNotIn(token, str(error.exception))


if __name__ == '__main__':
    unittest.main()
