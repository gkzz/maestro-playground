import tempfile
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import unittest
from pathlib import Path

from screenshot_report import build, cleanup


class ScreenshotReportTest(unittest.TestCase):
    def test_maestro_result_and_diff_are_reported_without_comparing_images(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads = root / 'downloads'
            flow = downloads / 'maestro-ios-unicode' / 'session' / 'flow'
            flow.mkdir(parents=True)
            (downloads / 'ios-unicode-field-ja.png').write_bytes(b'current')
            (root / 'baselines').mkdir()
            (root / 'baselines' / 'ios-unicode-field-ja.png').write_bytes(b'baseline')
            (flow / 'diff.png').write_bytes(b'maestro diff')
            (flow / 'commands.json').write_text(json.dumps([
                {'command': {'assertScreenshot': {'path': 'baseline.png'}},
                 'status': 'FAILED', 'artifacts': [{'relativePath': 'diff.png'}]}]))
            report = build(downloads, root / 'baselines', root / 'report', 'ja')
            self.assertIn('Maestro assertScreenshot: FAILED', report)
            self.assertIn('![diff]', report)
            self.assertEqual((root / 'report' / 'ios-unicode-field-ja-diff.png').read_bytes(),
                             b'maestro diff')

    def test_absent_capture_and_absent_baseline_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads, baselines = root / 'downloads', root / 'baselines'
            downloads.mkdir()
            baselines.mkdir()
            (downloads / 'ios-unicode-field-ja.png').write_bytes(b'current')
            report = build(downloads, baselines, root / 'report', 'ja')
            self.assertIn('No capture available', report)
            self.assertIn('Not compared: no baseline', report)
            self.assertNotIn('PASS', report)
            (baselines / 'ios-unicode-field-ja.png').write_bytes(b'baseline')
            report = build(downloads, baselines, root / 'report2', 'ja')
            self.assertIn('result unavailable', report)
            self.assertNotIn('![diff]', report)

    def test_closed_pr_images_are_removed_early(self):
        now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
        fresh = int((now - timedelta(hours=1)).timestamp())
        entries = [
            {'path': f'10/{fresh}-11-1/pr.png', 'type': 'blob', 'mode': '100644'},
            {'path': f'20/{fresh}-12-1/other.png', 'type': 'blob', 'mode': '100644'},
        ]

        def fake_api(path, payload=None):
            if path.endswith('/git/ref/heads/screenshot-reports'):
                return {'object': {'sha': 'parent'}}
            if path.endswith('/git/commits/parent'):
                return {'tree': {'sha': 'tree'}}
            if path.endswith('/git/trees/tree?recursive=1'):
                return {'tree': entries, 'truncated': False}
            if path.endswith('/actions/runs/10'):
                return {'pull_requests': [{'number': 34}]}
            if path.endswith('/actions/runs/20'):
                return {'pull_requests': [{'number': 35}]}
            if path.endswith('/git/trees'):
                self.assertEqual([item['path'] for item in payload['tree']], [entries[0]['path']])
                return {'sha': 'new-tree'}
            if path.endswith('/git/commits'):
                self.assertEqual(payload['parents'], [])
                return {'sha': 'new-commit'}
            raise AssertionError(path)

        with patch('screenshot_report.api', side_effect=fake_api), \
                patch('screenshot_report.subprocess.run') as run:
            self.assertEqual(cleanup('owner/repo', now=now, closed_pr=34), [entries[0]['path']])
        self.assertTrue(json.loads(run.call_args.kwargs['input'])['force'])

    def test_cleanup_deletes_only_images_older_than_one_day(self):
        now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
        old = int((now - timedelta(days=1, minutes=1)).timestamp())
        fresh = int((now - timedelta(hours=23)).timestamp())
        entries = [
            {'path': f'1/{old}-11-1/old.png', 'type': 'blob', 'mode': '100644'},
            {'path': f'2/{fresh}-12-1/fresh.png', 'type': 'blob', 'mode': '100644'},
            {'path': '3/legacy-1/legacy.png', 'type': 'blob', 'mode': '100644'},
        ]
        calls = []

        def fake_api(path, payload=None):
            calls.append((path, payload))
            if path.endswith('/git/ref/heads/screenshot-reports'):
                return {'object': {'sha': 'parent'}}
            if path.endswith('/git/commits/parent'):
                return {'tree': {'sha': 'tree'}}
            if path.endswith('/git/trees/tree?recursive=1'):
                return {'tree': entries, 'truncated': False}
            if path.endswith('/actions/runs/3'):
                return {'created_at': '2026-11-01T00:00:00Z'}
            if path.endswith('/git/trees'):
                return {'sha': 'new-tree'}
            if path.endswith('/git/commits'):
                return {'sha': 'new-commit'}
            raise AssertionError(path)

        with patch('screenshot_report.api', side_effect=fake_api), \
                patch('screenshot_report.subprocess.run') as run:
            removed = cleanup('owner/repo', now=now)
        self.assertEqual(removed, [entries[0]['path'], entries[2]['path']])
        deletion = next(payload for path, payload in calls if path.endswith('/git/trees'))
        self.assertEqual([item['sha'] for item in deletion['tree']], [None, None])
        run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
