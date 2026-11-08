"""Command-line entry point for screenshot reports and image cleanup."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path

from .github_api import GitHubApi
from .report import ScreenshotReport
from .store import ScreenshotReportStore


def usage():
    """Show the commands used by the screenshot report workflows."""
    return """Examples (run from the repository root):
  GITHUB_REPOSITORY=owner/repo python3 -m e2e.screenshot_report.cli \\
    --downloads /tmp/captures --output artifacts/screenshot-report \\
    --locale ja --platform android --source-run 123

  # Publish images for a GitHub Actions Job Summary (requires GITHUB_RUN_ID and
  # GITHUB_RUN_ATTEMPT in addition to GITHUB_REPOSITORY):
  python3 -m e2e.screenshot_report.cli \\
    --downloads /tmp/captures --output artifacts/screenshot-report \\
    --locale ja --platform android --source-run 123 --publish

  GITHUB_REPOSITORY=owner/repo python3 -m e2e.screenshot_report.cli --cleanup
  GITHUB_REPOSITORY=owner/repo python3 -m e2e.screenshot_report.cli \\
    --cleanup --closed-pr 123"""


def main():
    parser = argparse.ArgumentParser(
        epilog=usage(), formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--downloads', type=Path)
    parser.add_argument('--platform', choices=('android', 'ios', 'all'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--locale', choices=('ja', 'en'))
    parser.add_argument('--source-run', type=int)
    parser.add_argument('--cleanup', action='store_true')
    parser.add_argument('--closed-pr', type=int)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    repository = os.environ['GITHUB_REPOSITORY']
    api = GitHubApi()
    store = ScreenshotReportStore(repository, api)
    if args.cleanup:
        store.cleanup(closed_pr=args.closed_pr)
        return
    if not all((args.downloads, args.output, args.locale, args.source_run, args.platform)):
        parser.error('--downloads, --output, --locale, --source-run and --platform are required')
    source = api.request(f'repos/{repository}/actions/runs/{args.source_run}') if args.publish else None
    if source and (source['name'] != 'E2E' or source['head_repository']['full_name'] != repository):
        raise ValueError('Only E2E runs from this repository can be published')
    screenshot_report = ScreenshotReport(args.downloads, args.output, args.locale,
                                         ('android', 'ios') if args.platform == 'all' else (args.platform,))
    report = screenshot_report.build()
    prefix = (f'## Flutter screenshot comparison\n\n'
              f'[Source E2E run](https://github.com/{repository}/actions/runs/{args.source_run})\n\n')
    if source:
        prefix += f'Source commit: `{source["head_sha"]}`\n\n'
        directory = (f'{args.source_run}/{int(datetime.now(timezone.utc).timestamp())}-'
                     f'{os.environ["GITHUB_RUN_ID"]}-{os.environ["GITHUB_RUN_ATTEMPT"]}')
        url = store.publish(args.output, directory)
    else:
        url = args.output.resolve().as_uri()
    report = prefix + report.replace('@@', url or '')
    (args.output / 'summary.md').write_text(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
            summary.write(report)
    print(report)
    if screenshot_report.unavailable:
        raise SystemExit('Screenshot assertion result unavailable: ' + '; '.join(screenshot_report.unavailable))


if __name__ == '__main__':
    main()
