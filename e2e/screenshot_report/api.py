"""GitHub API requests used by screenshot report storage."""
import json
import subprocess


def api(path, payload=None):
    command = ['gh', 'api', path]
    if payload is not None:
        command += ['--method', 'POST', '--input', '-']
    result = subprocess.run(command, input=json.dumps(payload) if payload else None,
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)
