"""Summarize Maestro screenshot assertions for the Actions job summary."""
import base64
import json
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


class ScreenshotReport:
    def __init__(self, downloads, baselines, output, locale):
        self.downloads = downloads
        self.baselines = baselines
        self.output = output
        self.locale = locale
        self.unavailable = []

    def assertion(self, platform):
        """Return the last executed Maestro screenshot assertion and its artifacts."""
        files = list((self.downloads / f'maestro-{platform}-unicode').rglob('commands.json'))
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
        metadata = result.get('metadata', {})
        artifacts = []
        for item in metadata.get('artifacts', []):
            path = item.get('path')
            if path:
                candidate = (files[0].parent / path).resolve()
                if candidate.is_relative_to(files[0].parent.resolve()) and candidate.is_file():
                    artifacts.append(candidate)
        return metadata.get('status'), artifacts

    def build(self):
        self.output.mkdir(parents=True, exist_ok=True)
        sections = []
        for platform in ('android', 'ios'):
            stem = f'{platform}-unicode-field-{self.locale}'
            matches = list(self.downloads.rglob(f'{stem}.png'))
            section = [f'### {platform} / {self.locale}', '']
            if not matches:
                sections.append('\n'.join(section + ['No capture available. See the source job logs.', '']))
                continue
            if len(matches) != 1:
                raise ValueError(f'Ambiguous screenshot: {stem}')
            current = self.output / f'{stem}-current.png'
            current.write_bytes(matches[0].read_bytes())
            baseline = self.baselines / f'{stem}.png'
            if baseline.exists():
                reference = self.output / f'{stem}-baseline.png'
                reference.write_bytes(baseline.read_bytes())
                try:
                    status, artifacts = self.assertion(platform)
                except (ValueError, OSError, TypeError, AttributeError):
                    status, artifacts = None, []
                if status not in ('COMPLETED', 'FAILED'):
                    self.unavailable.append(f'{platform}: Maestro assertion result unavailable')
                section += [f'Maestro assertScreenshot: {status or "result unavailable"}', '']
                cells = [f'![baseline](@@/{reference.name})', f'![current](@@/{current.name})']
                headings = ['Baseline', 'Current']
                diffs = [path for path in artifacts if path.suffix.lower() == '.png'
                         and 'diff' in path.name.lower()]
                if diffs:
                    diff = self.output / f'{stem}-diff.png'
                    diff.write_bytes(diffs[-1].read_bytes())
                    headings.append('Diff')
                    cells.append(f'![diff](@@/{diff.name})')
                section += ['| ' + ' | '.join(headings) + ' |',
                            '| ' + ' | '.join('---' for _ in headings) + ' |',
                            '| ' + ' | '.join(cells) + ' |', '']
            else:
                section += ['Not compared: no baseline for this OS/locale.', '',
                            f'![current](@@/{current.name})', '']
            screens = list(self.downloads.rglob(f'{platform}-unicode-input-{self.locale}.png'))
            if len(screens) == 1:
                full = self.output / screens[0].name
                full.write_bytes(screens[0].read_bytes())
                section += ['<details><summary>Full screen</summary>', '',
                            f'<img src="@@/{full.name}" alt="{platform} input screen" width="320">',
                            '', '</details>', '']
            sections.append('\n'.join(section))
        return '\n'.join(sections)


class ScreenshotReportStore:
    def __init__(self, repository):
        self.repository = repository

    def publish(self, output, directory):
        branch = 'screenshot-reports'
        root = f'repos/{self.repository}'
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
        return f'https://raw.githubusercontent.com/{self.repository}/{branch}/{quote(directory)}'

    def cleanup(self, *, now=None, closed_pr=None):
        """Remove report images from the branch after one day."""
        root = f'repos/{self.repository}'
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
