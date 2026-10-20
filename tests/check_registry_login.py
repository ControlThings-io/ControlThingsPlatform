"""Check rootful registry credential transport and cleanup with a mocked Podman."""
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap

workflow = Path('.github/workflows/build.yml').read_text()


def step(name):
    """Return a named workflow step without requiring a YAML dependency."""
    return workflow.split(f'      - name: {name}\n', 1)[1].split('\n      - name:', 1)[0]


login = step('Login rootful Podman to GitHub Container Registry')
condition = login.split('        if: >\n')[1].split('        env:')[0].strip()
assert condition == step('Push To GHCR').split('        if: >\n')[1].split('        id:')[0].strip()
assert workflow.index('- name: Login rootful Podman') < workflow.index('- name: Build Image')
assert 'uses: docker/login-action@' in step('Login to GitHub Container Registry')
cleanup = step('Remove registry credentials')
assert 'if: always()' in cleanup
login_script = textwrap.dedent(login.split('        run: |\n', 1)[1])
cleanup_script = cleanup.split('        run: ', 1)[1].strip()
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    mock = root / 'bin'
    mock.mkdir()
    sudo = mock / 'sudo'
    sudo.write_text('''#!/usr/bin/env python3
import os, sys
from pathlib import Path
if sys.argv[1] == 'podman':
    assert sys.argv[2] == 'login'
    assert '--password-stdin' in sys.argv
    assert sys.stdin.read() == 'fixture-registry-token'
    path = Path(sys.argv[sys.argv.index('--authfile') + 1])
    path.write_text('fixture auth')
    path.chmod(0o600)
    raise SystemExit(int(os.environ['LOGIN_EXIT']))
assert sys.argv[1:3] == ['rm', '-f']
Path(sys.argv[3]).unlink(missing_ok=True)
''')
    sudo.chmod(0o755)
    for status in (0, 1):
        env_file = root / 'env'
        env_file.write_text('')
        env = dict(os.environ, PATH=f'{mock}:{os.environ["PATH"]}', RUNNER_TEMP=tmp,
                   REGISTRY_TOKEN='fixture-registry-token', GITHUB_ACTOR='fixture',
                   GITHUB_ENV=str(env_file), LOGIN_EXIT=str(status))
        result = subprocess.run(['bash', '-c', login_script], env=env, capture_output=True, text=True)
        assert result.returncode == status, result.stderr
        assert 'fixture-registry-token' not in result.stdout + result.stderr
        assert env_file.read_text() == (f'REGISTRY_AUTH_FILE={tmp}/ghcr-auth.json\n' if status == 0 else '')
        subprocess.run(['bash', '-c', cleanup_script], env=env, check=True)
        assert not (root / 'ghcr-auth.json').exists()
print('PASS registry login before build, matching publication conditions, stdin credentials, auth-file export and cleanup on success/failure')
