"""Exercise asset download recovery without network access or real credentials."""
from io import BytesIO
from pathlib import Path
import importlib.util
import sys
import tempfile
from unittest.mock import Mock, patch
from urllib.error import URLError

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path('build_files').resolve()))
import http_download
spec = importlib.util.spec_from_file_location('chef', 'build_files/install-cyberchef.py')
chef = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chef)


def response(body, length=None):
    """Create a file-like response, optionally declaring a longer body."""
    stream = BytesIO(body)
    stream.headers = {} if length is None else {'Content-Length': str(length)}
    return stream


with tempfile.TemporaryDirectory() as tmp:
    destination = Path(tmp) / 'download'
    # Exercise the actual asset wrapper, preserving anonymous requests. Inject
    # the stream opener beneath the shared retry implementation.
    original = http_download.download
    for failure in (URLError('temporary DNS failure'), TimeoutError(),
                    ConnectionResetError(), response(b'partial', 100)):
        opener = Mock(side_effect=[failure, response(b'complete', 8)])
        with patch.object(chef.http_download, 'download',
                          side_effect=lambda req, dest: original(req, dest, opener)), \
             patch.object(http_download.time, 'sleep') as sleep:
            chef.download('https://github.com/gchq/CyberChef/releases/download/v1/app.zip', destination)
        assert destination.read_bytes() == b'complete'
        assert opener.call_count == 2
        assert sleep.call_args.args == (1,)
        assert all(call.args[0].get_header('Authorization') is None for call in opener.call_args_list)
    opener = Mock(side_effect=TimeoutError())
    with patch.object(http_download.time, 'sleep') as sleep:
        try:
            original(chef.Request('https://example.invalid/file'), destination, opener)
        except TimeoutError:
            pass
        else:
            raise AssertionError('Expected exhausted retries')
    assert opener.call_count == 3 and sleep.call_count == 2
    opener = Mock(return_value=response(b'data'))
    with patch.object(http_download.time, 'sleep') as sleep:
        try:
            original(chef.Request('https://example.invalid/file'), Path(tmp), opener)
        except IsADirectoryError:
            pass
        else:
            raise AssertionError('Expected local filesystem failure')
    assert opener.call_count == 1 and sleep.call_count == 0
print('PASS anonymous asset downloads, network/timeout/truncation recovery, partial-file replacement, retry exhaustion and filesystem failure')
