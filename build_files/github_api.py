"""Download public GitHub API JSON using an optional temporary build secret.

CLI: python3 /ctx/github_api.py URL DESTINATION. Only https://api.github.com
URLs are accepted. Read /run/secrets/github_token if present; local builds can
omit it. Never persist credentials or send them on redirects. Retry transient
HTTP failures up to twice, waiting at most 60 seconds per retry; longer server
backoffs fail for a later build retry. HTTP, network and filesystem errors
propagate to the caller without logging credentials or response bodies.
"""
from pathlib import Path
import sys
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import http_download


class NoRedirect(HTTPRedirectHandler):
    """Reject redirects so authorization cannot escape the API origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def download(url: str, destination: Path,
             token_file: Path = Path('/run/secrets/github_token')) -> None:
    """Download API JSON, optionally authenticated, with bounded HTTP retries."""
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'api.github.com':
        raise ValueError('Expected an https://api.github.com URL')
    headers = {'User-Agent': 'ControlThingsPlatform-build',
               'Accept': 'application/vnd.github+json'}
    if token_file.exists():
        token = token_file.read_text().strip()
        if not token or '\n' in token or '\r' in token:
            raise ValueError('Invalid GitHub API token file')
        headers['Authorization'] = f'Bearer {token}'
    request = Request(url, headers=headers)
    opener = build_opener(NoRedirect())
    http_download.download(request, destination, opener.open)


if __name__ == '__main__':
    download(sys.argv[1], Path(sys.argv[2]))
