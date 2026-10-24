"""Exercise the real Chunkah recipe with mocked Podman, without building images.

Run ``python3 tests/check_rechunk.py`` from the repository root. Requires Python
3.9+, Bash, and just. Checks exact source tags, configuration transfer, Aurora
settings, bounded builder pulls, OCI import/retagging, final lint, cleanup, and
failure propagation. Pull failures and recovery are simulated; sleeps are mocked.
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
elif command == 'pull' and not args[1].startswith('oci:'):
    command = 'fetch'
with open(os.environ['RECHUNK_CALLS'], 'a') as log:
    log.write(json.dumps(args) + '\n')
if command == os.environ.get('RECHUNK_FAIL'):
    sys.exit(42)
if command == 'inspect':
    assert args == ['inspect', os.environ['RECHUNK_SOURCE']]
    print(json.dumps([{'Architecture': 'amd64', 'Config': {'Labels': {
        'containers.bootc': '1', 'org.opencontainers.image.version': 'fixture-version'
    }}}]))
elif command == 'fetch':
    assert args[:3] == ['pull', '--retry=0', '--policy=missing']
    assert len(args) == 4 and args[3].startswith('quay.io/coreos/chunkah:latest@sha256:')
    calls = [json.loads(line) for line in pathlib.Path(os.environ['RECHUNK_CALLS']).read_text().splitlines()]
    attempts = sum(call[0] == 'pull' and not call[1].startswith('oci:') for call in calls)
    if attempts <= int(os.environ.get('RECHUNK_TRANSIENT', '0')):
        print('received unexpected HTTP status: 503 Service Unavailable', file=sys.stderr)
        sys.exit(125)
elif command == 'builder':
    assert '--pull=never' in args
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

SLEEP = r'''#!/usr/bin/env python3
import os, pathlib, sys
assert sys.argv[1:] == ['5']
with pathlib.Path(os.environ['RECHUNK_WAITS']).open('a') as log:
    log.write('5\n')
'''

with tempfile.TemporaryDirectory(prefix='ct-rechunk-') as directory:
    root = Path(directory)
    binary_dir = root / 'bin'
    binary_dir.mkdir()
    mock = binary_dir / 'podman'
    mock.write_text(MOCK)
    mock.chmod(0o755)
    sleep = binary_dir / 'sleep'
    sleep.write_text(SLEEP)
    sleep.chmod(0o755)
    # Include spaces to exercise shell quoting for file mounts and OCI imports.
    scratch = root / 'temporary output'
    scratch.mkdir()
    calls_file = root / 'calls.jsonl'
    waits_file = root / 'waits'
    env = dict(os.environ, PATH=str(binary_dir) + os.pathsep + os.environ['PATH'],
               XDG_RUNTIME_DIR=str(root), TMPDIR=str(scratch),
               RECHUNK_CALLS=str(calls_file), RECHUNK_WAITS=str(waits_file))
    for tag in ('latest', 'pr-12', 'ics410_l01'):
        scenarios = [(failure, 0) for failure in ('', 'inspect', 'fetch', 'builder', 'pull', 'tag', 'lint')]
        scenarios += [('', transient) for transient in (1, 2, 3)]
        for failure, transient in scenarios:
            calls_file.write_text('')
            waits_file.write_text('')
            result = subprocess.run(
                ['just', 'rechunk', 'localhost/fixture', tag],
                env=dict(env, RECHUNK_SOURCE=f'localhost/fixture:{tag}', RECHUNK_FAIL=failure,
                         RECHUNK_TRANSIENT=str(transient)),
                text=True, capture_output=True,
            )
            calls = [json.loads(line) for line in calls_file.read_text().splitlines()]
            stages = [
                (('lint' if '--entrypoint' in args else 'builder') if args[0] == 'run'
                 else 'fetch' if args[0] == 'pull' and not args[1].startswith('oci:') else args[0])
                for args in calls
            ]
            fetches = 3 if failure == 'fetch' else min(transient + 1, 3)
            expected = ['inspect'] + ['fetch'] * fetches + ['builder', 'pull', 'tag', 'lint']
            if transient == 3:
                failure = 'fetch'
            if failure:
                stop = len(expected) - 1 - expected[::-1].index(failure)
                expected = expected[:stop + 1]
                assert result.returncode != 0, result.stderr
            else:
                assert result.returncode == 0, result.stderr
            assert stages == expected, (stages, expected, result.stderr)
            assert waits_file.read_text().splitlines() == ['5'] * max(stages.count('fetch') - 1, 0)
            assert not list(scratch.iterdir()), list(scratch.iterdir())
    print('PASS 3 source tags; success, all 6 failure stages, transient recovery and retry exhaustion; configuration transfer and cleanup')
