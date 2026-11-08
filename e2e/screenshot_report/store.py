"""Publish and expire screenshot report images."""
import base64
from datetime import datetime, timezone, timedelta
import subprocess
from urllib.parse import quote

from .github_api import GitHubApi


class ScreenshotReportStore:
    def __init__(self, repository, api=None):
        self.repository = repository
        self.api = api or GitHubApi()

    def publish(self, output, directory):
        branch = 'screenshot-reports'
        root = f'repos/{self.repository}'
        try:
            parent = self.api.request(f'{root}/git/ref/heads/{branch}')['object']['sha']
        except subprocess.CalledProcessError as error:
            if '404' not in error.stderr:
                raise
            parent = None
        tree = []
        for path in sorted(output.glob('*.png')):
            blob = self.api.request(f'{root}/git/blobs', {
                'content': base64.b64encode(path.read_bytes()).decode(), 'encoding': 'base64'})
            tree.append({'path': f'{directory}/{path.name}', 'mode': '100644',
                         'type': 'blob', 'sha': blob['sha']})
        if not tree:
            return None
        payload = {'tree': tree}
        if parent:
            payload['base_tree'] = self.api.request(f'{root}/git/commits/{parent}')['tree']['sha']
        tree_sha = self.api.request(f'{root}/git/trees', payload)['sha']
        commit = self.api.request(f'{root}/git/commits', {
            'message': f'Screenshot report {directory}', 'tree': tree_sha,
            'parents': [parent] if parent else []})['sha']
        if parent:
            self.api.update_ref(f'{root}/git/refs/heads/{branch}', commit, force=False)
        else:
            self.api.request(f'{root}/git/refs', {'ref': f'refs/heads/{branch}', 'sha': commit})
        return f'https://raw.githubusercontent.com/{self.repository}/{branch}/{quote(directory)}'

    def cleanup(self, *, now=None, closed_pr=None):
        """Remove report images from the branch after one day."""
        root = f'repos/{self.repository}'
        branch = 'screenshot-reports'
        try:
            parent = self.api.request(f'{root}/git/ref/heads/{branch}')['object']['sha']
        except subprocess.CalledProcessError as error:
            if '404' in error.stderr:
                return []
            raise
        tree_sha = self.api.request(f'{root}/git/commits/{parent}')['tree']['sha']
        listing = self.api.request(f'{root}/git/trees/{tree_sha}?recursive=1')
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
                source_by_run[run_id] = self.api.request(f'{root}/actions/runs/{run_id}')
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
        new_tree = self.api.request(f'{root}/git/trees', {'base_tree': tree_sha, 'tree': expired})['sha']
        commit = self.api.request(f'{root}/git/commits', {
            'message': f'Expire {len(expired)} screenshot images', 'tree': new_tree,
            'parents': []})['sha']
        self.api.update_ref(f'{root}/git/refs/heads/{branch}', commit, force=True)
        print(f'Expired {len(expired)} screenshot images')
        return [entry['path'] for entry in expired]
