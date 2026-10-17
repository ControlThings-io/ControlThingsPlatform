"""Reproduce Flatpak's nested loopback setup in a network-free Podman build.

Requires Linux, rootless Podman with subordinate IDs, bwrap, true and ldd. Uses
only host binaries/libraries in a scratch fixture and private temporary VFS
storage. Proves NET_ADMIN resolves the observed loopback error alongside
SYS_ADMIN; does not establish complete Flatpak extra-data or disk boot success.
"""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


with tempfile.TemporaryDirectory(prefix='ct-disk-sandbox-') as temporary:
    work = Path(temporary)
    context = work / 'context'
    root = context / 'rootfs'
    (root / 'tmp').mkdir(parents=True, mode=0o1777)
    for executable in ('/usr/bin/bwrap', '/usr/bin/true'):
        dependencies = subprocess.check_output(['ldd', executable], text=True)
        for filename in [executable, *re.findall(r'(/[^\s()]+)', dependencies)]:
            source = Path(filename)
            target = root / source.relative_to('/')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    invocation = ['/usr/bin/bwrap', '--unshare-net', '--ro-bind', '/', '/', '/usr/bin/true']
    (context / 'Containerfile').write_text(
        'FROM scratch\nCOPY rootfs /\nRUN ' + json.dumps(invocation) + '\n')
    runtime = work / 'runtime'
    runtime.mkdir(mode=0o700)
    env = dict(os.environ, XDG_RUNTIME_DIR=str(runtime))
    command = ['podman', '--root', str(work / 'storage'), '--runroot', str(work / 'run'),
               '--storage-driver=vfs', '--events-backend=file', '--tmpdir', str(work / 'tmp')]
    try:
        for network_admin in (False, True):
            extra = ['--cap-add', 'NET_ADMIN'] if network_admin else []
            result = subprocess.run([
                *command, 'build', '--pull=never', '--no-cache', '--network=none',
                '--cap-add', 'SYS_ADMIN', '--security-opt', 'label=disable',
                *extra, str(context)], env=env, text=True, capture_output=True)
            output = result.stdout + result.stderr
            if network_admin:
                assert result.returncode == 0, output
                assert 'Failed RTM_NEWADDR' not in output, output
            else:
                assert result.returncode != 0, output
                assert 'loopback: Failed RTM_NEWADDR' in output, output
    finally:
        # Every storage/runtime path above belongs to this temporary fixture.
        subprocess.run([*command, 'system', 'reset', '--force'], env=env, check=True)

print('Nested bwrap loopback failure reproduced without NET_ADMIN and fixed with it')
