"""Command-line entry point for screenshot reports and image cleanup."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path

from e2e.screenshot_report.api import api
from e2e.screenshot_report.report import ScreenshotReport
from e2e.screenshot_report.store import ScreenshotReportStore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--downloads', type=Path)
    parser.add_argument('--baselines', type=Path, default=Path('e2e/baselines'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--locale', choices=('ja', 'en'))
    parser.add_argument('--source-run', type=int)
    parser.add_argument('--cleanup', action='store_true')
    parser.add_argument('--closed-pr', type=int)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    repository = os.environ['GITHUB_REPOSITORY']
    store = ScreenshotReportStore(repository)
    if args.cleanup:
        store.cleanup(closed_pr=args.closed_pr)
        return
    if not all((args.downloads, args.output, args.locale, args.source_run)):
        parser.error('--downloads, --output, --locale and --source-run are required')
    source = api(f'repos/{repository}/actions/runs/{args.source_run}') if args.publish else None
    if source and (source['name'] != 'E2E' or source['head_repository']['full_name'] != repository):
        raise ValueError('Only E2E runs from this repository can be published')
    screenshot_report = ScreenshotReport(args.downloads, args.baselines, args.output, args.locale)
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
