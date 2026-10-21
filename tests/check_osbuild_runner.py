"""Exercise container setup ordering/failure handling with mocked system commands.

Run with python3 tests/check_osbuild_runner.py. No mounts, labels, or real builds
are performed; privileged runtime integration still requires a full CI build.
"""

import json
import os
from pathlib import Path
import subprocess
import tempfile

script = Path('scripts/run-osbuild.sh').read_text()
subprocess.run(['bash', '-n'], input=script, text=True, check=True)
with tempfile.TemporaryDirectory(prefix='ct-osbuild-runner-') as temporary:
    root = Path(temporary)
    manifest = root / 'disk.osbuild-manifest.json'
    manifest.write_text('{}')
    capture = root / 'commands'
    mock = root / 'mock'
    mock.write_text('''#!/usr/bin/python3
import json, os, sys
from pathlib import Path
p = Path(os.environ['CAPTURE'])
lines = p.read_text().splitlines() if p.exists() else []
with p.open('a') as out:
    out.write(json.dumps([Path(sys.argv[0]).name, *sys.argv[1:]]) + '\\n')
if str(len(lines)) == os.environ.get('FAIL_AT'):
    sys.exit(23)
''')
    mock.chmod(0o755)
    for name in ('mkdir', 'chcon', 'mount', 'cp', 'mock-osbuild'):
        (root / name).symlink_to(mock)
    # Keep the production absolute entrypoint; substitute it only in this fixture.
    fixture = root / 'runner.sh'
    fixture.write_text(script.replace('exec /usr/bin/osbuild ', 'exec mock-osbuild '))
    env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ['PATH'], CAPTURE=str(capture))
    subprocess.run(['bash', str(fixture), str(manifest)], env=env, check=True)
    commands = [json.loads(line) for line in capture.read_text().splitlines()]
    assert commands == [
        ['mkdir', '-p', '/var/cache/image-builder/store', '/run/osbuild'],
        ['chcon', 'system_u:object_r:root_t:s0', '/var/cache/image-builder/store'],
        ['mount', '-t', 'tmpfs', 'tmpfs', '/run/osbuild'],
        ['cp', '-p', '/usr/bin/osbuild', '/run/osbuild/osbuild'],
        ['chcon', 'system_u:object_r:install_exec_t:s0', '/run/osbuild/osbuild'],
        ['mount', '-t', 'devtmpfs', 'devtmpfs', '/dev'],
        ['mount', '--bind', '/run/osbuild/osbuild', '/usr/bin/osbuild'],
        ['mock-osbuild', '--store', '/var/cache/image-builder/store',
         '--output-directory', '/output', '--export', 'vmdk', str(manifest)],
    ]
    for index in range(len(commands)):
        capture.unlink()
        failed = subprocess.run(['bash', str(fixture), str(manifest)],
                                env=dict(env, FAIL_AT=str(index)))
        assert failed.returncode == 23
        assert len(capture.read_text().splitlines()) == index + 1
    for args in ([], [str(root / 'missing')], [str(manifest), 'extra']):
        capture.unlink(missing_ok=True)
        assert subprocess.run(['bash', str(fixture), *args], env=env).returncode != 0
        assert not capture.exists()
print('PASS OSBuild runner setup order, arguments and failure boundaries (mocked)')
