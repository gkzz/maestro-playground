import tempfile
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import unittest
from pathlib import Path

from e2e.screenshot_report.report import ScreenshotReport
from e2e.screenshot_report.store import ScreenshotReportStore
from e2e.screenshot_report_cli import main


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
            (flow / 'assert-screenshot').mkdir()
            (flow / 'assert-screenshot' / 'example-diff.png').write_bytes(b'maestro diff')
            (flow / 'commands.json').write_text(json.dumps([
                {'command': {'assertScreenshotCommand': {}},
                 'metadata': {'status': 'FAILED', 'artifacts': [
                     {'type': 'SCREENSHOT_DIFF',
                      'path': 'assert-screenshot/example-diff.png'}]}}]))
            report = ScreenshotReport(downloads, root / 'baselines', root / 'report', 'ja').build()
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
            report = ScreenshotReport(downloads, baselines, root / 'report', 'ja').build()
            self.assertIn('No capture available', report)
            self.assertIn('Not compared: no baseline', report)
            self.assertNotIn('PASS', report)
            (baselines / 'ios-unicode-field-ja.png').write_bytes(b'baseline')
            builder = ScreenshotReport(downloads, baselines, root / 'report2', 'ja')
            report = builder.build()
            self.assertIn('result unavailable', report)
            self.assertNotIn('![diff]', report)
            self.assertEqual(builder.unavailable, ['ios: Maestro assertion result unavailable'])

    def test_unavailable_result_keeps_summary_and_fails_job(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads, baselines = root / 'downloads', root / 'baselines'
            downloads.mkdir()
            baselines.mkdir()
            (downloads / 'ios-unicode-field-ja.png').write_bytes(b'current')
            (baselines / 'ios-unicode-field-ja.png').write_bytes(b'baseline')
            output = root / 'report'
            summary = root / 'job-summary.md'
            argv = ['screenshot_report_cli.py', '--downloads', str(downloads),
                    '--baselines', str(baselines), '--output', str(output),
                    '--locale', 'ja', '--source-run', '123']
            with patch('sys.argv', argv), patch.dict('os.environ', {
                    'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_STEP_SUMMARY': str(summary)}):
                with self.assertRaisesRegex(SystemExit, 'result unavailable'):
                    main()
            self.assertIn('result unavailable', summary.read_text())
            self.assertIn('result unavailable', (output / 'summary.md').read_text())
            self.assertTrue((output / 'ios-unicode-field-ja-current.png').exists())

    def test_malformed_maestro_result_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flow = root / 'downloads' / 'maestro-ios-unicode' / 'flow'
            flow.mkdir(parents=True)
            (flow / 'commands.json').write_text('{invalid')
            (root / 'downloads' / 'ios-unicode-field-ja.png').write_bytes(b'current')
            baselines = root / 'baselines'
            baselines.mkdir()
            (baselines / 'ios-unicode-field-ja.png').write_bytes(b'baseline')
            builder = ScreenshotReport(root / 'downloads', baselines, root / 'report', 'ja')
            report = builder.build()
            self.assertIn('result unavailable', report)
            self.assertEqual(builder.unavailable, ['ios: Maestro assertion result unavailable'])

    def test_completed_maestro_result_is_available(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flow = root / 'downloads' / 'maestro-ios-unicode' / 'flow'
            flow.mkdir(parents=True)
            (flow / 'commands.json').write_text(json.dumps([
                {'command': {'assertScreenshotCommand': {}},
                 'metadata': {'status': 'COMPLETED'}}]))
            (root / 'downloads' / 'ios-unicode-field-ja.png').write_bytes(b'current')
            baselines = root / 'baselines'
            baselines.mkdir()
            (baselines / 'ios-unicode-field-ja.png').write_bytes(b'baseline')
            builder = ScreenshotReport(root / 'downloads', baselines, root / 'report', 'ja')
            report = builder.build()
            self.assertIn('Maestro assertScreenshot: COMPLETED', report)
            self.assertEqual(builder.unavailable, [])

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

        with patch('e2e.screenshot_report.store.api', side_effect=fake_api), \
                patch('e2e.screenshot_report.store.subprocess.run') as run:
            self.assertEqual(ScreenshotReportStore('owner/repo').cleanup(now=now, closed_pr=34), [entries[0]['path']])
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

        with patch('e2e.screenshot_report.store.api', side_effect=fake_api), \
                patch('e2e.screenshot_report.store.subprocess.run') as run:
            removed = ScreenshotReportStore('owner/repo').cleanup(now=now)
        self.assertEqual(removed, [entries[0]['path'], entries[2]['path']])
        deletion = next(payload for path, payload in calls if path.endswith('/git/trees'))
        self.assertEqual([item['sha'] for item in deletion['tree']], [None, None])
        run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
