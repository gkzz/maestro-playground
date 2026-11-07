"""GitHub API requests used by screenshot report storage."""
import json
import subprocess


class GitHubApi:
    def request(self, path, payload=None, *, method='POST'):
        command = ['gh', 'api', path]
        if payload is not None:
            command += ['--method', method, '--input', '-']
        result = subprocess.run(command, input=json.dumps(payload) if payload else None,
                                text=True, capture_output=True, check=True)
        return json.loads(result.stdout)

    def update_ref(self, path, sha, *, force):
        self.request(path, {'sha': sha, 'force': force}, method='PATCH')
