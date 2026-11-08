"""Build screenshot reports and attach uploaded artifact links to Job Summary."""
import argparse
import os
from pathlib import Path

from .report import ScreenshotReport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloads', type=Path)
    parser.add_argument('--platform', choices=('android', 'ios', 'all'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--locale', choices=('ja', 'en'))
    parser.add_argument('--source-run', type=int)
    parser.add_argument('--artifact-url', help='Attach the uploaded artifact URL to an existing summary')
    args = parser.parse_args()
    if args.artifact_url:
        summary_path = args.output / 'summary.md'
        report = summary_path.read_text().replace('@@', args.artifact_url)
        summary_path.write_text(report)
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
            summary.write(report)
        return
    if not all((args.downloads, args.locale, args.source_run, args.platform)):
        parser.error('--downloads, --locale, --source-run and --platform are required')
    repository = os.environ['GITHUB_REPOSITORY']
    builder = ScreenshotReport(args.downloads, args.output, args.locale,
                               ('android', 'ios') if args.platform == 'all' else (args.platform,))
    report = (f'## Flutter screenshot comparison\n\n'
              f'[Source E2E run](https://github.com/{repository}/actions/runs/{args.source_run})\n\n'
              + builder.build())
    (args.output / 'summary.md').write_text(report)
    print(report)
    if builder.unavailable:
        raise SystemExit('Screenshot assertion result unavailable: ' + '; '.join(builder.unavailable))


if __name__ == '__main__':
    main()
