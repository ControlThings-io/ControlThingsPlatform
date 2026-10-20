"""Stream build downloads with bounded retries, without adding authentication."""
from http.client import IncompleteRead
from pathlib import Path
import shutil
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def download(request: Request, destination: Path, open_url: Callable = urlopen) -> None:
    """Stream a request to a disposable build file; retry transient failures twice.

The supplied opener controls redirects and authentication. Each attempt truncates
its destination before writing; callers must discard it on failure. Retry HTTP
429/selected 5xx, rate-limited 403, network errors and incomplete transfers.
Respect numeric Retry-After and rate-limit reset headers, allowing at most 60
seconds per wait. Permanent HTTP failures, longer backoffs and filesystem errors
propagate immediately. No request headers or response bodies are logged.
    """
    for attempt in range(3):
        try:
            with open_url(request, timeout=120) as response:
                with destination.open('wb') as output:
                    shutil.copyfileobj(response, output)
                    expected = response.headers.get('Content-Length')
                    if expected is not None and output.tell() < int(expected):
                        raise IncompleteRead(b'', int(expected) - output.tell())
            return
        except HTTPError as error:
            limited = error.headers.get('X-RateLimit-Remaining') == '0'
            retry_after = error.headers.get('Retry-After')
            retryable = error.code in (429, 500, 502, 503, 504) or (
                error.code == 403 and (limited or retry_after is not None))
            delay = 2 ** attempt
            try:
                if retry_after is not None:
                    delay = max(delay, float(retry_after))
                if limited and error.headers.get('X-RateLimit-Reset'):
                    delay = max(delay, float(error.headers['X-RateLimit-Reset']) - time.time() + 1)
            except ValueError:
                raise error
            if not retryable or attempt == 2 or not 0 <= delay <= 60:
                raise
            error.close()
        except (URLError, TimeoutError, ConnectionError, IncompleteRead):
            if attempt == 2:
                raise
            delay = 2 ** attempt
        time.sleep(delay)
