"""Check API credential scope and bounded retries without network or real secrets."""
from email.message import Message
from io import BytesIO
from pathlib import Path
import os
import subprocess
import textwrap
import sys
import tempfile
from unittest.mock import Mock, patch
from urllib.error import HTTPError

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path('build_files').resolve()))
import github_api
import http_download


def response(body):
    """Make a streamed response with HTTP headers."""
    result = BytesIO(body)
    result.headers = {}
    return result


def failure(code, **headers):
    """Construct an HTTP response failure for retry fixtures."""
    message = Message()
    for key, value in headers.items():
        message[key] = value
    return HTTPError('https://api.github.com/meta', code, 'fixture', message, BytesIO())


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    token = root / 'token'
    output = root / 'response.json'
    for authenticated in (False, True):
        if authenticated:
            token.write_text('fixture-token\n')
        opener = Mock()
        opener.open.return_value = response(b'{"ssh_keys":[]}')
        with patch.object(github_api, 'build_opener', return_value=opener):
            github_api.download('https://api.github.com/meta', output, token)
        request = opener.open.call_args.args[0]
        assert request.get_header('Authorization') == ('Bearer fixture-token' if authenticated else None)
        assert output.read_bytes() == b'{"ssh_keys":[]}'
    for url in ('http://api.github.com/meta', 'https://github.com/asset',
                'https://api.github.com.evil.invalid/meta', 'https://api.github.com@evil.invalid/meta'):
        try:
            github_api.download(url, output, token)
        except ValueError:
            pass
        else:
            raise AssertionError(url)
    assert github_api.NoRedirect().redirect_request(None, None, 302, '', {},
                                                    'https://other.invalid') is None
    for code, headers, delays in (
        (503, {}, [1, 2]),
        (429, {'Retry-After': '3'}, [3, 3]),
        (403, {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '105'}, [6, 6]),
        (403, {}, []),
        (401, {}, []),
        (403, {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '500'}, []),
    ):
        opener = Mock()
        opener.open.side_effect = [failure(code, **headers) for _ in range(3)]
        with patch.object(github_api, 'build_opener', return_value=opener), \
             patch.object(http_download.time, 'sleep') as sleep, \
             patch.object(http_download.time, 'time', return_value=100):
            try:
                github_api.download('https://api.github.com/meta', output, token)
            except HTTPError:
                pass
            else:
                raise AssertionError('Expected HTTP failure')
        assert [call.args[0] for call in sleep.call_args_list] == delays
        assert opener.open.call_count == len(delays) + 1
    opener = Mock()
    opener.open.side_effect = [failure(503), response(b'{}')]
    with patch.object(github_api, 'build_opener', return_value=opener), \
         patch.object(http_download.time, 'sleep'):
        github_api.download('https://api.github.com/meta', output, token)
    assert output.read_bytes() == b'{}'
print('PASS optional API authentication, origin restriction, redirect rejection, bounded HTTP retries and recovery')

# Execute the real workflow shell block with a fake builder. Inspect the secret
# while it exists, then verify cleanup after success, failure and missing token.
workflow = Path('.github/workflows/build.yml').read_text()
block = workflow.split('        id: build-image\n', 1)[1]
block = textwrap.dedent(block.split('        run: |\n', 1)[1].split('\n      - name:', 1)[0])
with tempfile.TemporaryDirectory(prefix='api-workflow-test-') as tmp:
    root = Path(tmp)
    mock = root / 'bin'
    mock.mkdir()
    sudo = mock / 'sudo'
    sudo.write_text('''#!/usr/bin/env python3
import os
from pathlib import Path
path = Path(os.environ['GITHUB_API_TOKEN_FILE'])
assert path.stat().st_mode & 0o777 == 0o600
assert path.read_text() == 'fixture-api-token\\n'
assert 'GITHUB_TOKEN' not in os.environ
raise SystemExit(int(os.environ['BUILD_EXIT']))
''')
    sudo.chmod(0o755)
    just = mock / 'just'
    just.write_text('#!/bin/sh\nexit 99\n')
    just.chmod(0o755)
    for token_value, status in (('fixture-api-token', 0), ('fixture-api-token', 7), ('', 1)):
        result = subprocess.run(['bash', '-c', block], capture_output=True, text=True,
            env=dict(os.environ, PATH=f'{mock}:{os.environ["PATH"]}', RUNNER_TEMP=tmp,
                     GITHUB_TOKEN=token_value, BUILD_EXIT=str(status),
                     IMAGE_NAME='fixture', DEFAULT_TAG='latest'))
        assert result.returncode == status, result.stderr
        assert not list(root.glob('github-token.*'))
        assert 'fixture-api-token' not in result.stdout + result.stderr
print('PASS workflow token permissions, environment removal, no logging, cleanup on success/failure/missing token')
