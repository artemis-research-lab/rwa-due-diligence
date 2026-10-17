"""Read-only HTTPS download of one public file into <project>/.scratch/raw/ (D24).

The only module allowed to import urllib. GET only, an honest User-Agent, no cookies, no auth, no body;
host and redirect checks, a size cap and an atomic write. It does not register a source.
"""

import hashlib
import http.client
import ipaddress
import re
import urllib.error
import urllib.parse
import urllib.request

from lib import runstate

USER_AGENT = "rwa-due-diligence/0.4 (+read-only research)"
HEADERS = (("User-Agent", USER_AGENT), ("Accept", "*/*"))
NAME_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$"
MAX_REDIRECTS = 5
TIMEOUT = 30
MAX_BYTES = 25_000_000
CHUNK = 65536
REDIRECT_CODES = (301, 302, 303, 307, 308)
BLOCKED_SUFFIXES = (".local", ".internal", ".localhost")


class FetchError(Exception):
    """Network or HTTP failure (CLI exit 4)."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Hand every 3xx response back to the caller, which checks the target before following it."""

    def _keep(self, req, fp, code, msg, headers):
        return fp

    http_error_301 = http_error_302 = http_error_303 = http_error_307 = http_error_308 = _keep


def _open(request):
    opener = urllib.request.build_opener(_NoRedirect)
    opener.addheaders = []
    return opener.open(request, timeout=TIMEOUT)


def check_name(name):
    if not isinstance(name, str) or not re.fullmatch(NAME_PATTERN, name):
        raise runstate.InvalidError(["name: %r must match %s" % (name, NAME_PATTERN)])
    return name


def url_problem(url):
    """None when url is an https URL to a public host name, else the reason it is refused."""
    try:
        parts = urllib.parse.urlsplit(url)
        parts.port
    except ValueError as exc:
        return "malformed URL (%s)" % exc
    if parts.scheme != "https":
        return "scheme must be https"
    if parts.username is not None or parts.password is not None:
        return "credentials in the URL are not allowed"
    host = (parts.hostname or "").rstrip(".")
    if not host:
        return "missing host"
    try:
        ipaddress.ip_address(host)
        return "host must not be an IP literal"
    except ValueError:
        pass
    if re.fullmatch(r"0x[0-9a-f]+|[0-9.]+", host):
        return "host must not be an IP literal"
    if host == "localhost" or host.endswith(BLOCKED_SUFFIXES):
        return "host %s is not public" % host
    return None


def check_url(url):
    problem = url_problem(url)
    if problem:
        raise runstate.InvalidError(["url: %s" % problem])
    return url


def _request(url):
    request = urllib.request.Request(url, method="GET")
    for key, value in HEADERS:
        request.add_header(key, value)
    return request


def _get(url):
    try:
        return _open(_request(url))
    except urllib.error.HTTPError as exc:
        raise FetchError("HTTP %d %s for %s" % (exc.code, exc.reason, url))
    except urllib.error.URLError as exc:
        raise FetchError("network error for %s: %s" % (url, exc.reason))
    except (OSError, http.client.HTTPException) as exc:
        raise FetchError("network error for %s: %s" % (url, exc))


def _save(project, response, part, target):
    """Stream the body into part, then rename it to target; nothing is kept on failure."""
    length = response.headers.get("Content-Length")
    if length and length.strip().isdigit() and int(length) > MAX_BYTES:
        raise FetchError("size cap exceeded: Content-Length %s > %d bytes" % (length.strip(), MAX_BYTES))
    digest = hashlib.sha256()
    size = 0
    try:
        with open(project.safe(part), "wb") as handle:
            while True:
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise FetchError("size cap exceeded: more than %d bytes" % MAX_BYTES)
                digest.update(chunk)
                handle.write(chunk)
        project.safe(part).replace(project.safe(target))
    except (OSError, http.client.HTTPException) as exc:
        part.unlink(missing_ok=True)
        raise FetchError("download failed: %s" % exc)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    return size, digest.hexdigest()


def fetch_file(root, slug, url, name, overwrite=False):
    project = runstate.open_project(root, slug)
    check_name(name)
    check_url(url)
    raw = project.scratch / "raw"
    target = project.safe(raw / name)
    part = project.safe(raw / (name + ".part"))
    if target.exists() and not overwrite:
        raise runstate.InvalidError(["name: %s already exists in .scratch/raw (use --overwrite)" % name])
    project.mkdir(raw)

    current = url
    for _ in range(MAX_REDIRECTS + 1):
        response = _get(current)
        with response:
            status = response.status
            if status in REDIRECT_CODES:
                location = response.headers.get("Location")
                if not location:
                    raise FetchError("HTTP %d without Location for %s" % (status, current))
                following = urllib.parse.urljoin(current, location.strip())
                problem = url_problem(following)
                if problem:
                    raise FetchError("redirect from %s refused: %s" % (current, problem))
                current = following
                continue
            if not 200 <= status < 300:
                raise FetchError("HTTP %d %s for %s" % (status, response.reason, current))
            size, sha256 = _save(project, response, part, target)
            return {"path": str(target), "bytes": size, "sha256": sha256,
                    "content_type": response.headers.get("Content-Type"),
                    "final_url": current, "http_status": status}
    raise FetchError("more than %d redirects starting at %s" % (MAX_REDIRECTS, url))
