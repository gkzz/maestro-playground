import tempfile
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import unittest
from pathlib import Path

from PIL import Image
from screenshot_report import build, compare, cleanup


class ScreenshotReportTest(unittest.TestCase):
    def test_exact_match_and_single_changed_pixel(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, current, diff = [root / name for name in ('base.png', 'current.png', 'diff.png')]
            image = Image.new('RGBA', (10, 10), 'white')
            image.save(baseline)
            image.save(current)
            self.assertIn('PASS: 100.0000%', compare(baseline, current, diff))
            image.putpixel((3, 4), (0, 0, 0, 255))
            image.save(current)
            self.assertIn('FAIL: 99.0000% match; 1 changed pixels', compare(baseline, current, diff))
            with Image.open(diff) as result:
                self.assertEqual(result.getpixel((3, 4)), (255, 0, 80))
                self.assertEqual(result.getpixel((0, 0)), (255, 255, 255))

    def test_alpha_changes_and_different_sizes_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, current, diff = [Path(directory) / name for name in ('base.png', 'current.png', 'diff.png')]
            Image.new('RGBA', (2, 2), (0, 0, 0, 0)).save(baseline)
            Image.new('RGBA', (2, 2), (0, 0, 0, 255)).save(current)
            self.assertIn('FAIL: 0.0000%', compare(baseline, current, diff))
            Image.new('RGBA', (3, 2), (0, 0, 0, 0)).save(current)
            self.assertIn('FAIL:', compare(baseline, current, diff))

    def test_absent_capture_and_absent_baseline_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads, baselines = root / 'downloads', root / 'baselines'
            downloads.mkdir()
            baselines.mkdir()
            Image.new('RGB', (2, 2), 'white').save(downloads / 'ios-unicode-field-ja.png')
            report = build(downloads, baselines, root / 'report', 'ja')
            self.assertIn('No capture available', report)
            self.assertIn('Not compared: no baseline', report)
            self.assertNotIn('PASS', report)
            Image.new('RGB', (2, 2), 'white').save(baselines / 'ios-unicode-field-ja.png')
            self.assertIn('PASS: 100.0000%', build(downloads, baselines, root / 'report2', 'ja'))

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
