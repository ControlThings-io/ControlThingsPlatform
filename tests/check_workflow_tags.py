"""Check workflow tags with ``python3 tests/check_workflow_tags.py`` from the repo root.

Execute the workflow's tag-selection shell block for PR, main, and course refs.
Validate generated alias tags and arguments passed by the actual build recipe
to a mocked Podman. Check build/rechunk shell syntax without building images;
rootful image building and rechunking still require separate integration checks.
Requires Python 3.9+, Bash, Git, and just; uses only the Python standard library.
"""
import os
import json
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap

workflow = Path('.github/workflows/build.yml').read_text()
step = workflow.split('        id: gen-default-tag\n', 1)[1]
body = step.split('        run: |\n', 1)[1].split('\n      - name:', 1)[0]
script = textwrap.dedent(body)
subprocess.run(['bash', '-n'], input=script, text=True, check=True)
tag_pattern = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}')
cases = [
    ('pull_request', '3/merge', '3', 'pr-3'),
    ('pull_request', '8/merge', '8', 'pr-8'),
    ('pull_request', '9/merge', '9', 'pr-9'),
    ('push', 'main', '', 'latest'),
    ('schedule', 'main', '', 'latest'),
    ('workflow_dispatch', 'main', '', 'latest'),
    ('push', 'ics410_l01', '', 'ics410_l01'),
    ('push', 'ICS410_L01', '', 'ics410_l01'),
]
with tempfile.TemporaryDirectory(prefix='ct-pr3-tests-') as temp:
    mock_bin = Path(temp) / 'bin'
    mock_bin.mkdir()
    podman = mock_bin / 'podman'
    podman.write_text('#!/usr/bin/env python3\nimport json, os, sys\nwith open(os.environ["CAPTURE_ARGS"], "w") as f: json.dump(sys.argv[1:], f)\n')
    podman.chmod(0o755)
    capture = Path(temp) / 'args.json'
    env = dict(os.environ, XDG_RUNTIME_DIR=temp, CAPTURE_ARGS=str(capture),
               PATH=str(mock_bin) + os.pathsep + os.environ['PATH'])
    token = Path(temp) / 'api-token'
    token.write_text('fixture-api-token')
    for event, ref, number, expected in cases:
        if event == 'push':
            env['GITHUB_API_TOKEN_FILE'] = str(token)
        else:
            env.pop('GITHUB_API_TOKEN_FILE', None)
        env_file = Path(temp) / 'github_env'
        env_file.write_text('')
        case_env = dict(env, GITHUB_EVENT_NAME=event, GITHUB_REF_NAME=ref,
                        PR_NUMBER=number, GITHUB_ENV=str(env_file))
        subprocess.run(['bash', '-e'], input=script, text=True, env=case_env,
                       capture_output=True, check=True)
        actual = env_file.read_text().strip().removeprefix('DEFAULT_TAG=')
        assert actual == expected, (event, ref, actual, expected)
        assert tag_pattern.fullmatch(actual), actual
        tags = subprocess.run(['just', 'generate-build-tags', 'controlthingsplatform', actual],
                              env=env, capture_output=True, text=True, check=True).stdout.split()
        assert actual in tags and all(tag_pattern.fullmatch(tag) for tag in tags), tags
        for recipe in ('build', 'rechunk', 'ostree-rechunk'):
            result = subprocess.run(['just', '--dry-run', recipe, 'controlthingsplatform', actual],
                                    env=env, capture_output=True, text=True, check=True)
            subprocess.run(['bash', '-n'], input=result.stdout + result.stderr,
                           text=True, check=True)
        build = subprocess.run(['just', 'build', 'controlthingsplatform', actual],
                       env=env, capture_output=True, text=True, check=True)
        args = json.loads(capture.read_text())
        assert token.read_text() not in build.stdout + build.stderr + ' '.join(args)
        assert (f'id=github_token,src={token}' in args) == (event == 'push')
        assert args[0] == 'build' and args[args.index('--tag') + 1] == f'controlthingsplatform:{actual}', args
        assert any(re.fullmatch(r'CYBERCHEF_BUILD_EPOCH=\d+', arg) for arg in args), args
        assert not any(arg.startswith('TOOLS_BUILD_EPOCH=') for arg in args), args
        print(f'PASS {event} {ref} -> {actual}; alias tags, mocked Podman build arguments, build/rechunk shell syntax')
    for ref in ('3/merge', '8/merge', '9/merge'):
        assert not tag_pattern.fullmatch(ref)
    print('PASS original PR tags rejected by image-tag grammar')
print('PASS workflow shell syntax; 8 event/ref cases')
