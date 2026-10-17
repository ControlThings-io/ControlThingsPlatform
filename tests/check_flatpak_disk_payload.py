"""Verify a populated Flatpak store survives copying into a disk payload.

Requires flatpak and ostree. Creates a tiny app/runtime remote and deploys it,
then copies the populated store and removes its source. This tests dependencies,
exports and extra-data retention without internet, root or host changes. A local
HTTP server supplies extra-data during build. Real apply_extra sandbox scripts,
OCI COPY ownership/hardlinks, bootc /var import and graphical launches need CI/VM.
"""

from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading


def run(*args: str, env: dict[str, str]) -> str:
    """Capture successful command output; include stderr on failure."""
    result = subprocess.run(args, env=env, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f'{args}:\n{result.stdout}\n{result.stderr}')
    return result.stdout.strip()


with tempfile.TemporaryDirectory(prefix='ct-flatpak-cache-') as temporary:
    root = Path(temporary)
    env = dict(os.environ, FLATPAK_USER_DIR=str(root / 'cached'),
               XDG_CACHE_HOME=str(root / 'xdg-cache'),
               XDG_DATA_HOME=str(root / 'xdg-data'))
    arch = run('flatpak', '--default-arch', env=env)
    remote = root / 'remote'
    runtime = root / 'runtime'
    (runtime / 'files').mkdir(parents=True)
    (runtime / 'files/fixture').write_text('runtime dependency\n')
    (runtime / 'metadata').write_text(
        f'[Runtime]\nname=org.controlthings.TestRuntime\nruntime=org.controlthings.TestRuntime/{arch}/stable\n')
    run('flatpak', 'build-export', '--disable-sandbox', '--runtime', '--files=files',
        str(remote), str(runtime), 'stable', env=env)
    app = root / 'app'
    (app / 'files/bin').mkdir(parents=True)
    (app / 'files/bin/fixture').write_text('#!/bin/sh\necho fixture\n')
    (app / 'files/bin/fixture').chmod(0o755)
    desktop = app / 'files/share/applications/org.controlthings.TestApp.desktop'
    desktop.parent.mkdir(parents=True)
    desktop.write_text('[Desktop Entry]\nType=Application\nName=Test app\nExec=fixture\n')
    (app / 'metadata').write_text(
        f'[Application]\nname=org.controlthings.TestApp\nruntime=org.controlthings.TestRuntime/{arch}/stable\ncommand=fixture\n')
    extra = b'offline extra-data fixture\n'
    (root / 'extra.dat').write_bytes(extra)

    class Handler(SimpleHTTPRequestHandler):
        """Serve the fixture without routine request logging."""

        def log_message(self, format: str, *args: object) -> None:
            pass

    with ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(root))) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        uri = f'http://127.0.0.1:{server.server_port}/extra.dat'
        try:
            run('flatpak', 'build-finish',
                f'--extra-data=extra.dat:{hashlib.sha256(extra).hexdigest()}:{len(extra)}:{len(extra)}:{uri}',
                str(app), env=env)
            run('flatpak', 'build-export', '--disable-sandbox', str(remote), str(app), 'stable', env=env)
            run('flatpak', 'remote-add', '--user', '--no-gpg-verify', 'flathub', remote.as_uri(), env=env)
            run('flatpak', 'install', '--user', '--noninteractive', '--assumeyes',
                'flathub', 'org.controlthings.TestApp', env=env)
        finally:
            server.shutdown()
            worker.join()
    deployed = root / 'deployed'
    shutil.copytree(root / 'cached', deployed, symlinks=True)
    shutil.rmtree(remote)
    shutil.rmtree(root / 'cached')
    shutil.rmtree(root / 'xdg-cache', ignore_errors=True)
    (root / 'extra.dat').unlink()
    env['FLATPAK_USER_DIR'] = str(deployed)
    assert run('flatpak', 'info', '--user', '--show-location',
               'org.controlthings.TestApp', env=env).startswith(str(deployed))
    refs = run('flatpak', 'list', '--user', '--columns=ref', env=env).splitlines()
    assert set(refs) == {f'org.controlthings.TestApp/{arch}/stable',
                         f'org.controlthings.TestRuntime/{arch}/stable'}, refs
    assert (deployed / 'exports/share/applications/org.controlthings.TestApp.desktop').exists()
    assert (deployed / f'runtime/org.controlthings.TestRuntime/{arch}/stable/active/files/fixture').read_text() == 'runtime dependency\n'
    assert (deployed / f'app/org.controlthings.TestApp/{arch}/stable/active/files/extra/extra.dat').read_bytes() == extra

print('Copied Flatpak store retained app, runtime, extra-data and desktop export with sources removed')
