"""Summarize Maestro screenshot assertions for the Actions job summary."""
import argparse
import base64
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import subprocess
from urllib.parse import quote



def api(path, payload=None):
    command = ['gh', 'api', path]
    if payload is not None:
        command += ['--method', 'POST', '--input', '-']
    result = subprocess.run(command, input=json.dumps(payload) if payload else None,
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def assertion(downloads, platform):
    """Return the last executed Maestro screenshot assertion and its artifacts."""
    files = list((downloads / f'maestro-{platform}-unicode').rglob('commands.json'))
    if len(files) > 1:
        raise ValueError(f'Ambiguous Maestro results: {platform}')
    if not files:
        return None, []
    commands = json.loads(files[0].read_text())
    matches = [entry for entry in commands
               if 'assertScreenshot' in json.dumps(entry.get('command', {}))]
    if not matches:
        return None, []
    result = matches[-1]
    artifacts = []
    for item in result.get('artifacts', []):
        path = item if isinstance(item, str) else item.get('relativePath', item.get('path'))
        if path:
            candidate = (files[0].parent / path).resolve()
            if candidate.is_relative_to(files[0].parent.resolve()) and candidate.is_file():
                artifacts.append(candidate)
    return result.get('status'), artifacts


def build(downloads, baselines, output, locale):
    output.mkdir(parents=True, exist_ok=True)
    sections = []
    for platform in ('android', 'ios'):
        stem = f'{platform}-unicode-field-{locale}'
        matches = list(downloads.rglob(f'{stem}.png'))
        section = [f'### {platform} / {locale}', '']
        if not matches:
            sections.append('\n'.join(section + ['No capture available. See the source job logs.', '']))
            continue
        if len(matches) != 1:
            raise ValueError(f'Ambiguous screenshot: {stem}')
        current = output / f'{stem}-current.png'
        current.write_bytes(matches[0].read_bytes())
        baseline = baselines / f'{stem}.png'
        if baseline.exists():
            reference = output / f'{stem}-baseline.png'
            reference.write_bytes(baseline.read_bytes())
            status, artifacts = assertion(downloads, platform)
            section += [f'Maestro assertScreenshot: {status or "result unavailable"}', '']
            cells = [f'![baseline](@@/{reference.name})', f'![current](@@/{current.name})']
            headings = ['Baseline', 'Current']
            diffs = [path for path in artifacts if path.suffix.lower() == '.png'
                     and 'diff' in path.name.lower()]
            if diffs:
                diff = output / f'{stem}-diff.png'
                diff.write_bytes(diffs[-1].read_bytes())
                headings.append('Diff')
                cells.append(f'![diff](@@/{diff.name})')
            section += ['| ' + ' | '.join(headings) + ' |',
                        '| ' + ' | '.join('---' for _ in headings) + ' |',
                        '| ' + ' | '.join(cells) + ' |', '']
        else:
            section += ['Not compared: no baseline for this OS/locale.', '',
                        f'![current](@@/{current.name})', '']
        screens = list(downloads.rglob(f'{platform}-unicode-input-{locale}.png'))
        if len(screens) == 1:
            full = output / screens[0].name
            full.write_bytes(screens[0].read_bytes())
            section += ['<details><summary>Full screen</summary>', '',
                        f'<img src="@@/{full.name}" alt="{platform} input screen" width="320">',
                        '', '</details>', '']
        sections.append('\n'.join(section))
    return '\n'.join(sections)


def publish(output, repository, directory):
    branch = 'screenshot-reports'
    root = f'repos/{repository}'
    try:
        parent = api(f'{root}/git/ref/heads/{branch}')['object']['sha']
    except subprocess.CalledProcessError as error:
        if '404' not in error.stderr:
            raise
        parent = None
    tree = []
    for path in sorted(output.glob('*.png')):
        blob = api(f'{root}/git/blobs', {
            'content': base64.b64encode(path.read_bytes()).decode(), 'encoding': 'base64'})
        tree.append({'path': f'{directory}/{path.name}', 'mode': '100644',
                     'type': 'blob', 'sha': blob['sha']})
    if not tree:
        return None
    payload = {'tree': tree}
    if parent:
        payload['base_tree'] = api(f'{root}/git/commits/{parent}')['tree']['sha']
    tree_sha = api(f'{root}/git/trees', payload)['sha']
    commit = api(f'{root}/git/commits', {
        'message': f'Screenshot report {directory}', 'tree': tree_sha,
        'parents': [parent] if parent else []})['sha']
    if parent:
        subprocess.run(['gh', 'api', f'{root}/git/refs/heads/{branch}', '--method', 'PATCH',
                        '--input', '-'], input=json.dumps({'sha': commit, 'force': False}),
                       text=True, capture_output=True, check=True)
    else:
        api(f'{root}/git/refs', {'ref': f'refs/heads/{branch}', 'sha': commit})
    return f'https://raw.githubusercontent.com/{repository}/{branch}/{quote(directory)}'



def cleanup(repository, *, now=None, closed_pr=None):
    """Remove report images from the branch after one day."""
    root = f'repos/{repository}'
    branch = 'screenshot-reports'
    try:
        parent = api(f'{root}/git/ref/heads/{branch}')['object']['sha']
    except subprocess.CalledProcessError as error:
        if '404' in error.stderr:
            return []
        raise
    tree_sha = api(f'{root}/git/commits/{parent}')['tree']['sha']
    listing = api(f'{root}/git/trees/{tree_sha}?recursive=1')
    if listing.get('truncated'):
        raise ValueError('Screenshot tree was truncated; refusing partial cleanup')
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)
    expired = []
    source_by_run = {}
    for entry in listing['tree']:
        if entry['type'] != 'blob' or not entry['path'].endswith('.png'):
            continue
        run_id = entry['path'].split('/', 1)[0]
        if not run_id.isdecimal():
            continue
        report_dir = entry['path'].split('/', 2)[1]
        timestamp = report_dir.split('-', 1)[0]
        if run_id not in source_by_run and (closed_pr or len(timestamp) < 10):
            source_by_run[run_id] = api(f'{root}/actions/runs/{run_id}')
        if len(timestamp) >= 10 and timestamp.isdecimal():
            created = datetime.fromtimestamp(int(timestamp), timezone.utc)
        else:
            created = datetime.fromisoformat(source_by_run[run_id]['created_at'].replace('Z', '+00:00'))
        from_closed_pr = closed_pr and any(
            pull['number'] == closed_pr for pull in source_by_run[run_id].get('pull_requests', []))
        if created <= cutoff or from_closed_pr:
            expired.append({'path': entry['path'], 'mode': entry['mode'], 'type': 'blob', 'sha': None})
    if not expired:
        return []
    new_tree = api(f'{root}/git/trees', {'base_tree': tree_sha, 'tree': expired})['sha']
    commit = api(f'{root}/git/commits', {
        'message': f'Expire {len(expired)} screenshot images', 'tree': new_tree,
        'parents': []})['sha']
    subprocess.run(['gh', 'api', f'{root}/git/refs/heads/{branch}', '--method', 'PATCH',
                    '--input', '-'], input=json.dumps({'sha': commit, 'force': True}),
                   text=True, capture_output=True, check=True)
    print(f'Expired {len(expired)} screenshot images')
    return [entry['path'] for entry in expired]


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
    if args.cleanup:
        cleanup(repository, closed_pr=args.closed_pr)
        return
    if not all((args.downloads, args.output, args.locale, args.source_run)):
        parser.error('--downloads, --output, --locale and --source-run are required')
    source = api(f'repos/{repository}/actions/runs/{args.source_run}') if args.publish else None
    if source and (source['name'] != 'E2E' or source['head_repository']['full_name'] != repository):
        raise ValueError('Only E2E runs from this repository can be published')
    report = build(args.downloads, args.baselines, args.output, args.locale)
    prefix = (f'## Flutter screenshot comparison\n\n'
              f'[Source E2E run](https://github.com/{repository}/actions/runs/{args.source_run})\n\n')
    if source:
        prefix += f'Source commit: `{source["head_sha"]}`\n\n'
        directory = (f'{args.source_run}/{int(datetime.now(timezone.utc).timestamp())}-'
                     f'{os.environ["GITHUB_RUN_ID"]}-{os.environ["GITHUB_RUN_ATTEMPT"]}')
        url = publish(args.output, repository, directory)
    else:
        url = args.output.resolve().as_uri()
    report = prefix + report.replace('@@', url or '')
    (args.output / 'summary.md').write_text(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
            summary.write(report)
    print(report)


if __name__ == '__main__':
    main()
