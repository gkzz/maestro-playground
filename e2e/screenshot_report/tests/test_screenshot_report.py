import os
import subprocess
import tomllib
import tempfile
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
import unittest
from pathlib import Path

from e2e.screenshot_report.report import ScreenshotReport
from e2e.screenshot_report.store import ScreenshotReportStore
from e2e.screenshot_report.github_api import GitHubApi
from e2e.screenshot_report.cli import main


class ScreenshotReportTest(unittest.TestCase):
    """Verify report generation, CLI failure handling, and image cleanup."""

    def baseline(self, artifact, platform, present=True):
        stem = f'{platform}-unicode-field-ja'
        (artifact / f'{stem}-baseline-state.txt').write_text('present' if present else 'absent')
        if present:
            (artifact / f'{stem}-baseline.png').write_bytes(b'baseline')

    def test_e2e_tasks_use_the_artifact_baseline_snapshot(self):
        config = tomllib.loads(Path('.config/mise/config.toml').read_text())
        for platform in ('android', 'ios'):
            for source in ('default', 'override', 'absent'):
                with self.subTest(platform=platform, source=source), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    binary = root / 'maestro'
                    binary.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> "$GITHUB_WORKSPACE/args"\n')
                    binary.chmod(0o755)
                    env = dict(os.environ, GITHUB_WORKSPACE=str(root),
                               E2E_FLOW='unicode', E2E_LOCALE='ja',
                               E2E_SCREENSHOT_BASELINE='', PATH=f'{root}:/usr/bin:/bin')
                    if source != 'absent':
                        baseline = (root / 'override.png' if source == 'override' else
                                    root / 'e2e/baselines' / f'{platform}-unicode-field-ja.png')
                        baseline.parent.mkdir(parents=True, exist_ok=True)
                        baseline.write_bytes(b'selected baseline')
                        if source == 'override':
                            env['E2E_SCREENSHOT_BASELINE'] = str(baseline)
                    subprocess.run(['sh', '-c', config['tasks'][f'maestro:test-{platform}']['run']],
                                   env=env, check=True, capture_output=True)
                    artifact = root / 'artifacts/maestro' / platform / 'unicode'
                    stem = f'{platform}-unicode-field-ja'
                    snapshot = artifact / f'{stem}-baseline.png'
                    self.assertEqual((artifact / f'{stem}-baseline-state.txt').read_text().strip(),
                                     'absent' if source == 'absent' else 'present')
                    if source != 'absent':
                        self.assertEqual(snapshot.read_bytes(), b'selected baseline')
                        self.assertIn(f'SCREENSHOT_BASELINE={snapshot}', (root / 'args').read_text())
                    else:
                        self.assertFalse(snapshot.exists())

    def test_missing_target_capture_fails_cli_after_summary(self):
        for platform in ('android', 'ios', 'all'):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                argv = ['cli.py', '--downloads', str(root / 'empty'),
                        '--output', str(root / 'report'), '--platform', platform,
                        '--locale', 'ja', '--source-run', '123']
                with patch('sys.argv', argv), patch.dict('os.environ', {
                        'GITHUB_REPOSITORY': 'owner/repo'}), patch('builtins.print'):
                    with self.assertRaisesRegex(SystemExit, 'capture unavailable'):
                        main()
                summary = (root / 'report' / 'summary.md').read_text()
                self.assertIn('No capture available', summary)
                if platform == 'android':
                    self.assertNotIn('### ios', summary)

    def test_artifact_baseline_update_and_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads = root / 'downloads'
            downloads.mkdir()
            (downloads / 'android-unicode-field-ja.png').write_bytes(b'current')
            # A checkout baseline must never affect the report.
            (root / 'baselines').mkdir()
            (root / 'baselines' / 'android-unicode-field-ja.png').write_bytes(b'old')
            self.baseline(downloads, 'android')
            (downloads / 'commands.json').write_text(json.dumps([{
                'command': {'assertScreenshotCommand': {}},
                'metadata': {'status': 'COMPLETED'}}]))
            builder = ScreenshotReport(downloads, root / 'report', 'ja', ('android',))
            builder.build()
            self.assertEqual(builder.unavailable, [])
            self.assertEqual((root / 'report' / 'android-unicode-field-ja-baseline.png').read_bytes(),
                             b'baseline')
            (downloads / 'android-unicode-field-ja-baseline.png').unlink()
            (downloads / 'commands.json').unlink()
            self.baseline(downloads, 'android', present=False)
            builder = ScreenshotReport(downloads, root / 'deleted', 'ja', ('android',))
            self.assertIn('Not compared: no baseline', builder.build())
            self.assertEqual(builder.unavailable, [])

    def test_github_api_updates_ref_with_patch(self):
        """Updating the image branch sends the requested SHA and force flag."""
        with patch('e2e.screenshot_report.github_api.subprocess.run') as run:
            run.return_value.stdout = '{}'
            GitHubApi().update_ref('repos/owner/repo/git/refs/heads/screenshot-reports',
                                   'new-commit', force=True)
        self.assertEqual(run.call_args.args[0][-4:], ['--method', 'PATCH', '--input', '-'])
        self.assertEqual(json.loads(run.call_args.kwargs['input']),
                         {'sha': 'new-commit', 'force': True})

    def test_maestro_result_and_diff_are_reported_without_comparing_images(self):
        """The summary uses Maestro's failure and Diff without comparing pixels."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads = root / 'downloads'
            flow = downloads / 'maestro-ios-unicode' / 'session' / 'flow'
            flow.mkdir(parents=True)
            (downloads / 'ios-unicode-field-ja.png').write_bytes(b'current')
            (root / 'baselines').mkdir()
            self.baseline(downloads, 'ios')
            (flow / 'assert-screenshot').mkdir()
            (flow / 'assert-screenshot' / 'example-diff.png').write_bytes(b'maestro diff')
            (flow / 'commands.json').write_text(json.dumps([
                {'command': {'assertScreenshotCommand': {}},
                 'metadata': {'status': 'FAILED', 'artifacts': [
                     {'type': 'SCREENSHOT_DIFF',
                      'path': 'assert-screenshot/example-diff.png'}]}}]))
            report = ScreenshotReport(downloads, root / 'report', 'ja', ('ios',)).build()
            self.assertIn('Maestro assertScreenshot: FAILED', report)
            self.assertIn('![diff]', report)
            self.assertEqual((root / 'report' / 'ios-unicode-field-ja-diff.png').read_bytes(),
                             b'maestro diff')

    def test_absent_capture_and_absent_baseline_are_explicit(self):
        """Missing captures, missing baselines, and missing results stay distinct."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads, baselines = root / 'downloads', root / 'baselines'
            downloads.mkdir()
            baselines.mkdir()
            (downloads / 'ios-unicode-field-ja.png').write_bytes(b'current')
            self.baseline(downloads, 'ios', present=False)
            report = ScreenshotReport(downloads, root / 'report', 'ja', ('ios',)).build()
            self.assertIn('Not compared: no baseline', report)
            self.assertNotIn('PASS', report)
            self.baseline(root / 'downloads', 'ios')
            builder = ScreenshotReport(downloads, root / 'report2', 'ja', ('ios',))
            report = builder.build()
            self.assertIn('result unavailable', report)
            self.assertNotIn('![diff]', report)
            self.assertEqual(builder.unavailable, ['ios: Maestro assertion result unavailable'])

    def test_unavailable_result_keeps_summary_and_fails_job(self):
        """A missing assertion fails the CLI after writing the summary and images."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads, baselines = root / 'downloads', root / 'baselines'
            downloads.mkdir()
            baselines.mkdir()
            (downloads / 'ios-unicode-field-ja.png').write_bytes(b'current')
            self.baseline(root / 'downloads', 'ios')
            output = root / 'report'
            summary = root / 'job-summary.md'
            argv = ['cli.py', '--downloads', str(downloads),
                    '--platform', 'ios', '--output', str(output),
                    '--locale', 'ja', '--source-run', '123']
            with patch('sys.argv', argv), patch.dict('os.environ', {
                    'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_STEP_SUMMARY': str(summary)}):
                with self.assertRaisesRegex(SystemExit, 'result unavailable'):
                    main()
            self.assertIn('result unavailable', summary.read_text())
            self.assertIn('result unavailable', (output / 'summary.md').read_text())
            self.assertTrue((output / 'ios-unicode-field-ja-current.png').exists())

    def test_malformed_maestro_result_is_unavailable(self):
        """An unreadable commands.json becomes an unavailable assertion result."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flow = root / 'downloads' / 'maestro-ios-unicode' / 'flow'
            flow.mkdir(parents=True)
            (flow / 'commands.json').write_text('{invalid')
            (root / 'downloads' / 'ios-unicode-field-ja.png').write_bytes(b'current')
            baselines = root / 'baselines'
            baselines.mkdir()
            self.baseline(root / 'downloads', 'ios')
            builder = ScreenshotReport(root / 'downloads', root / 'report', 'ja', ('ios',))
            report = builder.build()
            self.assertIn('result unavailable', report)
            self.assertEqual(builder.unavailable, ['ios: Maestro assertion result unavailable'])

    def test_completed_maestro_result_is_available(self):
        """Maestro's real success status is accepted as a known result."""
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
            self.baseline(root / 'downloads', 'ios')
            builder = ScreenshotReport(root / 'downloads', root / 'report', 'ja', ('ios',))
            report = builder.build()
            self.assertIn('Maestro assertScreenshot: COMPLETED', report)
            self.assertEqual(builder.unavailable, [])

    def test_download_layouts_and_unavailable_results(self):
        """Single and multiple downloads preserve OS identity and CLI failures."""
        cases = [
            ('flat', {'android': 'COMPLETED'}, False),
            ('flat', {'android': 'FAILED'}, False),
            ('flat', {'ios': 'COMPLETED'}, False),
            ('named', {'android': 'COMPLETED', 'ios': 'FAILED'}, False),
            ('flat', {'android': None}, True),
            ('flat', {'android': 'malformed'}, True),
            ('flat', {'android': 'ambiguous'}, True),
            ('flat', {'android': 'COMPLETED', 'ios': None}, True),
            ('named', {'android': None, 'ios': 'COMPLETED'}, True),
        ]
        for layout, results, unavailable in cases:
            with self.subTest(layout=layout, results=results):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    downloads, baselines = root / 'downloads', root / 'baselines'
                    downloads.mkdir()
                    baselines.mkdir()
                    for platform, status in results.items():
                        artifact = downloads / f'maestro-{platform}-unicode' if layout == 'named' else downloads
                        flow = artifact / 'session' / platform
                        flow.mkdir(parents=True)
                        stem = f'{platform}-unicode-field-ja.png'
                        (artifact / stem).write_bytes(b'current')
                        self.baseline(artifact, platform)
                        if status is not None:
                            commands = json.dumps([{
                                'command': {'assertScreenshotCommand': {}},
                                'metadata': {'status': status}}])
                            (flow / 'commands.json').write_text(
                                '{invalid' if status == 'malformed' else commands)
                            if status == 'ambiguous':
                                (flow / 'retry').mkdir()
                                (flow / 'retry' / 'commands.json').write_text(commands)
                    output = root / 'report'
                    summary = root / 'job-summary.md'
                    argv = ['cli.py', '--downloads', str(downloads),
                            '--platform', 'all' if len(results) == 2 else next(iter(results)),
                            '--output', str(output),
                            '--locale', 'ja', '--source-run', '123']
                    with patch('sys.argv', argv), patch.dict('os.environ', {
                            'GITHUB_REPOSITORY': 'owner/repo',
                            'GITHUB_STEP_SUMMARY': str(summary)}), patch('builtins.print'):
                        if unavailable:
                            with self.assertRaisesRegex(SystemExit, 'result unavailable'):
                                main()
                        else:
                            main()
                    report = summary.read_text()
                    self.assertEqual(report, (output / 'summary.md').read_text())
                    if not unavailable:
                        for platform, status in results.items():
                            section = report.split(f'### {platform} / ja')[1].split('### ')[0]
                            self.assertIn(f'Maestro assertScreenshot: {status}', section)
                    else:
                        self.assertIn('result unavailable', report)
                    if layout == 'flat':
                        builder = ScreenshotReport(downloads, output, 'ja', tuple(results))
                        other = 'android' if set(results) == {'ios'} else 'ios'
                        self.assertEqual(builder.assertion(other), (None, []))

    def test_closed_pr_images_are_removed_early(self):
        """Closing a PR removes only images associated with that PR."""
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

        api = Mock()
        api.request.side_effect = fake_api
        self.assertEqual(ScreenshotReportStore('owner/repo', api).cleanup(now=now, closed_pr=34),
                         [entries[0]['path']])
        api.update_ref.assert_called_once_with(
            'repos/owner/repo/git/refs/heads/screenshot-reports', 'new-commit', force=True)

    def test_cleanup_deletes_only_images_older_than_one_day(self):
        """Scheduled cleanup expires old images and preserves recent images."""
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

        api = Mock()
        api.request.side_effect = fake_api
        removed = ScreenshotReportStore('owner/repo', api).cleanup(now=now)
        self.assertEqual(removed, [entries[0]['path'], entries[2]['path']])
        deletion = next(payload for path, payload in calls if path.endswith('/git/trees'))
        self.assertEqual([item['sha'] for item in deletion['tree']], [None, None])
        api.update_ref.assert_called_once_with(
            'repos/owner/repo/git/refs/heads/screenshot-reports', 'new-commit', force=True)


if __name__ == '__main__':
    unittest.main()
