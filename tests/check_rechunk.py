"""Exercise the real Chunkah recipe with mocked Podman, without building images.

Run ``python3 tests/check_rechunk.py`` from the repository root. Requires Python
3.9+, Bash, and just. Checks exact source tags, configuration transfer, Aurora
settings, OCI import/retagging, final lint, cleanup, and failure propagation.
Actual Chunkah output and VM boot/update behavior need integration validation.
"""

import json
import os
from pathlib import Path
import subprocess
import tempfile


MOCK = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
command = args[0]
if command == 'run':
    command = 'lint' if '--entrypoint' in args else 'builder'
with open(os.environ['RECHUNK_CALLS'], 'a') as log:
    log.write(json.dumps(args) + '\n')
if command == os.environ.get('RECHUNK_FAIL'):
    sys.exit(42)
if command == 'inspect':
    assert args == ['inspect', os.environ['RECHUNK_SOURCE']]
    print(json.dumps([{'Architecture': 'amd64', 'Config': {'Labels': {
        'containers.bootc': '1', 'org.opencontainers.image.version': 'fixture-version'
    }}}]))
elif command == 'builder':
    assert '--mount=type=image,src=' + os.environ['RECHUNK_SOURCE'] + ',target=/chunkah' in args
    assert args[args.index('--max-layers') + 1] == '256'
    assert args[args.index('--prune') + 1] == '/sysroot/'
    assert args[args.index('--config') + 1] == '/chunkah-config.json'
    assert args[args.index('--output') + 1] == 'oci:/run/out/chunked'
    assert '--compressed' in args
    assert 'ostree.commit-' in args and 'ostree.final-diffid-' in args
    assert any(a.startswith('quay.io/coreos/chunkah:latest@sha256:') for a in args)
    config_mount = next(a for a in args if a.endswith(':/chunkah-config.json:ro,Z'))
    config = pathlib.Path(config_mount.removesuffix(':/chunkah-config.json:ro,Z'))
    metadata = json.loads(config.read_text())[0]
    assert metadata['Architecture'] == 'amd64'
    assert metadata['Config']['Labels']['containers.bootc'] == '1'
    assert metadata['Config']['Labels']['org.opencontainers.image.version'] == 'fixture-version'
    output_mount = next(a for a in args if a.endswith(':/run/out:Z'))
    output = pathlib.Path(output_mount.removesuffix(':/run/out:Z')) / 'chunked'
    output.mkdir()
    (output / 'index.json').write_text('{}')
elif command == 'pull':
    assert args[1].startswith('oci:')
    assert pathlib.Path(args[1][4:], 'index.json').exists()
    print('sha256:fixture-output')
elif command == 'tag':
    assert args == ['tag', 'sha256:fixture-output', os.environ['RECHUNK_SOURCE']]
elif command == 'lint':
    assert args == ['run', '--rm', '--entrypoint', 'bootc', os.environ['RECHUNK_SOURCE'], 'container', 'lint']
else:
    raise AssertionError(args)
'''

with tempfile.TemporaryDirectory(prefix='ct-rechunk-') as directory:
    root = Path(directory)
    binary_dir = root / 'bin'
    binary_dir.mkdir()
    mock = binary_dir / 'podman'
    mock.write_text(MOCK)
    mock.chmod(0o755)
    # Include spaces to exercise shell quoting for file mounts and OCI imports.
    scratch = root / 'temporary output'
    scratch.mkdir()
    calls_file = root / 'calls.jsonl'
    env = dict(os.environ, PATH=str(binary_dir) + os.pathsep + os.environ['PATH'],
               XDG_RUNTIME_DIR=str(root), TMPDIR=str(scratch),
               RECHUNK_CALLS=str(calls_file))
    for tag in ('latest', 'pr-12', 'ics410_l01'):
        for failure in ('', 'inspect', 'builder', 'pull', 'tag', 'lint'):
            calls_file.write_text('')
            result = subprocess.run(
                ['just', 'rechunk', 'localhost/fixture', tag],
                env=dict(env, RECHUNK_SOURCE=f'localhost/fixture:{tag}', RECHUNK_FAIL=failure),
                text=True, capture_output=True,
            )
            calls = [json.loads(line) for line in calls_file.read_text().splitlines()]
            stages = [
                ('lint' if '--entrypoint' in args else 'builder') if args[0] == 'run' else args[0]
                for args in calls
            ]
            expected = ['inspect', 'builder', 'pull', 'tag', 'lint']
            if failure:
                expected = expected[:expected.index(failure) + 1]
                assert result.returncode != 0, result.stderr
            else:
                assert result.returncode == 0, result.stderr
            assert stages == expected, (stages, expected, result.stderr)
            assert not list(scratch.iterdir()), list(scratch.iterdir())
    print('PASS 3 source tags; success and all 5 failure stages; configuration transfer and cleanup')
