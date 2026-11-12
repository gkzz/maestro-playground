import copy
import json
import os
import subprocess
import tomllib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from e2e.screenshot_report.cli import main
from e2e.screenshot_report.report import ScreenshotReport


class ScreenshotReportTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.downloads = self.root / 'downloads'
        self.output = self.root / 'report'

    def fixture(self, platform='android', named=True, state='present', status='COMPLETED', percentage=99.125):
        artifact = self.downloads / f'maestro-{platform}-unicode' if named else self.downloads
        flow = artifact / platform
        flow.mkdir(parents=True)
        (artifact / f'{platform}-unicode-field-ja-baseline-state.txt').write_text(state)
        # These are deliberately different from the assertion image, and must not be copied.
        (artifact / f'{platform}-unicode-field-ja-baseline.png').write_bytes(b'baseline')
        (flow / f'{platform}-unicode-field-ja.png').write_bytes(b'takeScreenshot')
        (flow / 'screenshots').mkdir()
        (flow / 'screenshots/step-001-actual.png').write_bytes(b'assertion actual')
        entry = {'command': {'assertScreenshotCommand': {}}, 'metadata': {
            'status': status,
            'screenshotComparison': {'matchPercentage': percentage, 'thresholdPercentage': 95,
                                     'actualPath': 'screenshots/step-001-actual.png', 'sizeMismatch': False},
            'artifacts': [{'type': 'SCREENSHOT', 'path': 'screenshots/step-001-actual.png'}]}}
        commands = flow / 'commands.json'
        commands.write_text(json.dumps([entry] if state == 'present' else []))
        return flow, commands, entry

    def build(self, platforms=('android',)):
        builder = ScreenshotReport(self.downloads, self.output, 'ja', platforms)
        return builder, builder.build()

    def cli(self, platform='android', artifact_url=None):
        argv = ['cli.py', '--output', str(self.output)]
        if artifact_url:
            argv += ['--artifact-url', artifact_url]
        else:
            argv += ['--downloads', str(self.downloads), '--platform', platform,
                     '--locale', 'ja', '--source-run', '123']
        with patch('sys.argv', argv), patch.dict(os.environ, {
                'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_STEP_SUMMARY': str(self.root / 'job.md')}), \
                patch('builtins.print'):
            main()

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

    def test_actual_assertion_image_and_measured_percentage(self):
        self.fixture()
        builder, report = self.build()
        self.assertEqual(builder.unavailable, [])
        self.assertIn('COMPLETED | 99.125% | 95%', report)
        self.assertIn('[Download assertion images](@@)', report)
        self.assertEqual((self.output / 'android-assertion-1-actual.png').read_bytes(), b'assertion actual')
        self.assertEqual([p.name for p in self.output.iterdir()], ['android-assertion-1-actual.png'])
        self.assertNotIn('![', report)

    def test_multiple_assertions_do_not_include_container_or_overwrite_images(self):
        flow, commands, entry = self.fixture()
        other = copy.deepcopy(entry)
        other['metadata']['status'] = 'FAILED'
        other['metadata']['screenshotComparison']['matchPercentage'] = 42.5
        other['metadata']['screenshotComparison']['actualPath'] = 'screenshots/step-002-actual.png'
        other['metadata']['artifacts'][0]['path'] = 'screenshots/step-002-actual.png'
        (flow / 'screenshots/step-002-actual.png').write_bytes(b'second actual')
        commands.write_text(json.dumps([
            {'command': {'runFlowCommand': {'commands': [entry['command']]}}, 'metadata': {'status': 'FAILED'}},
            entry, other]))
        builder, report = self.build()
        self.assertEqual(builder.unavailable, [])
        self.assertIn('| 2 | FAILED | 42.5%', report)
        self.assertEqual((self.output / 'android-assertion-2-actual.png').read_bytes(), b'second actual')

    def test_failure_diff_is_copied_from_maestro(self):
        flow, commands, entry = self.fixture(status='FAILED', percentage=42)
        (flow / 'diff.png').write_bytes(b'Maestro diff')
        entry['metadata']['artifacts'].append({'type': 'SCREENSHOT_DIFF', 'path': 'diff.png'})
        commands.write_text(json.dumps([entry]))
        builder, report = self.build()
        self.assertEqual(builder.unavailable, [])
        self.assertIn('FAILED | 42%', report)
        self.assertEqual((self.output / 'android-assertion-1-diff.png').read_bytes(), b'Maestro diff')

    def test_size_mismatch_does_not_invent_percentage(self):
        _, commands, entry = self.fixture(status='FAILED')
        comparison = entry['metadata']['screenshotComparison']
        del comparison['matchPercentage']
        comparison['sizeMismatch'] = True
        commands.write_text(json.dumps([entry]))
        builder, report = self.build()
        self.assertEqual(builder.unavailable, [])
        self.assertIn('N/A (image size mismatch)', report)

    def test_missing_invalid_and_legacy_metrics_fail(self):
        _, commands, entry = self.fixture()
        for value in (None, True, -1, 101, float('nan'), '99.9'):
            with self.subTest(value=value):
                entry['metadata']['screenshotComparison']['matchPercentage'] = value
                commands.write_text(json.dumps([entry]))
                builder, report = self.build()
                self.assertTrue(builder.unavailable)
                self.assertIn('measured match percentage unavailable', report)
        del entry['metadata']['screenshotComparison']
        commands.write_text(json.dumps([entry]))
        self.assertTrue(self.build()[0].unavailable)

    def test_actual_image_cannot_be_replaced_by_take_screenshot_or_baseline(self):
        flow, commands, entry = self.fixture()
        for path in (None, '/etc/passwd', '../../outside.png', 'screenshots/missing.png'):
            with self.subTest(path=path):
                entry['metadata']['screenshotComparison']['actualPath'] = path
                commands.write_text(json.dumps([entry]))
                builder, _ = self.build()
                self.assertTrue(builder.unavailable)
                self.assertFalse(list(self.output.glob('*.png')))
        (flow / 'screenshots/escape.png').symlink_to('/etc/passwd')
        entry['metadata']['screenshotComparison']['actualPath'] = 'screenshots/escape.png'
        commands.write_text(json.dumps([entry]))
        self.assertTrue(self.build()[0].unavailable)

    def test_missing_image_registration_is_unavailable(self):
        _, commands, entry = self.fixture()
        for artifacts in ([], [{'type': 'TAKE_SCREENSHOT', 'path': 'screenshots/step-001-actual.png'}]):
            with self.subTest(artifacts=artifacts):
                entry['metadata']['artifacts'] = artifacts
                commands.write_text(json.dumps([entry]))
                self.assertIn('actual image not registered', self.build()[1])

    def test_match_percentage_is_not_rounded_up_to_100(self):
        self.fixture(status='FAILED', percentage=99.99999999)
        _, report = self.build()
        self.assertIn('99.99999999%', report)

    def test_missing_baseline_and_unknown_results_are_distinct(self):
        artifact, commands, _ = self.fixture(state='absent')
        builder, report = self.build()
        self.assertEqual(builder.unavailable, [])
        self.assertIn('Not compared: no baseline', report)
        self.assertFalse(list(self.output.glob('*.png')))
        commands.unlink()
        builder, report = self.build()
        self.assertTrue(builder.unavailable)
        self.assertIn('commands.json missing', report)

    def test_executed_assertion_with_absent_baseline_is_invalid(self):
        _, commands, entry = self.fixture(state='absent')
        commands.write_text(json.dumps([entry]))
        self.assertTrue(self.build()[0].unavailable)

    def test_malformed_ambiguous_and_parent_only_results_fail(self):
        flow, commands, entry = self.fixture()
        for content in ('{bad', '{}', 'null', json.dumps([{'command': {'runFlowCommand': {
                'commands': [entry['command']]}}, 'metadata': {'status': 'COMPLETED'}}])):
            with self.subTest(content=content):
                commands.write_text(content)
                self.assertTrue(self.build()[0].unavailable)
        (flow / 'other').mkdir()
        (flow / 'other/commands.json').write_text('[]')
        self.assertIn('ambiguous', self.build()[1])

    def test_flat_and_named_platform_layouts(self):
        self.fixture(named=False)
        self.assertEqual(self.build()[0].unavailable, [])
        self.assertTrue(self.build(('ios',))[0].unavailable)

    def test_two_platforms_use_their_own_results(self):
        self.fixture('android', percentage=100)
        self.fixture('ios', status='FAILED', percentage=90)
        builder, report = self.build(('android', 'ios'))
        self.assertEqual(builder.unavailable, [])
        self.assertIn('COMPLETED | 100%', report.split('### ios')[0])
        self.assertIn('FAILED | 90%', report.split('### ios')[1])

    def test_missing_platform_fails_after_retaining_other_platform_evidence(self):
        self.fixture('ios')
        with self.assertRaisesRegex(SystemExit, 'android'):
            self.cli('all')
        self.assertTrue((self.output / 'summary.md').exists())
        self.assertTrue((self.output / 'ios-assertion-1-actual.png').exists())

    def test_cli_writes_failure_summary_and_final_artifact_link(self):
        with self.assertRaises(SystemExit):
            self.cli()
        self.cli(artifact_url='https://github.com/owner/repo/actions/runs/123/artifacts/456')
        self.assertIn('Assertion result unavailable', (self.root / 'job.md').read_text())

    def test_cli_final_summary_links_to_uploaded_artifact(self):
        self.fixture()
        self.cli()
        url = 'https://github.com/owner/repo/actions/runs/123/artifacts/456'
        self.cli(artifact_url=url)
        summary = (self.root / 'job.md').read_text()
        self.assertIn(f'[Download assertion images]({url})', summary)
        self.assertNotIn('@@', summary)
        self.assertIn('[Source E2E run](https://github.com/owner/repo/actions/runs/123)', summary)


if __name__ == '__main__':
    unittest.main()
