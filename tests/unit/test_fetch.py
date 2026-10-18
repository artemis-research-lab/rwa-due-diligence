"""P4 fetch helper (D24): host, scheme, redirect, size and name rules, atomic write; offline except one
acceptance test that runs only with --run-acceptance."""

import email.message
import hashlib
import json
import urllib.error

import pytest

from test_support import clock_at, walk
from lib import fetch, runstate

PDF = b"%PDF-1.4\n% tiny\n" + b"x" * 100


class FakeResponse:
    def __init__(self, status=200, body=b"", headers=None, reason="OK"):
        self.status = status
        self.reason = reason
        self.headers = email.message.Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value
        self._body = body
        self._pos = 0

    def read(self, n=-1):
        if n < 0:
            n = len(self._body) - self._pos
        chunk = self._body[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def serve(monkeypatch, responses):
    """Replace the opener: each request takes the next canned response (or exception) by URL."""
    seen = []

    def fake_open(request):
        seen.append(request)
        item = responses[request.full_url]
        if isinstance(item, Exception):
            raise item
        return item() if callable(item) else item

    monkeypatch.setattr(fetch, "_open", fake_open)
    return seen


@pytest.fixture
def project(tmp_path):
    runstate.init(tmp_path, "acme", "https://a.example/", clock=clock_at())
    return runstate.open_project(tmp_path, "acme")


def _fetch(project, url, name="doc.pdf", **kw):
    return fetch.fetch_file(project.root, project.slug, url, name, **kw)


def test_success_writes_atomically_and_reports(project, monkeypatch):
    url = "https://docs.example.com/a/doc.pdf"
    serve(monkeypatch, {url: FakeResponse(body=PDF, headers={"Content-Type": "application/pdf"})})
    result = _fetch(project, url)
    assert list(result) == ["path", "bytes", "sha256", "content_type", "final_url", "http_status"]
    target = project.scratch / "raw" / "doc.pdf"
    assert result["path"] == str(target.resolve())
    assert target.read_bytes() == PDF
    assert result["bytes"] == len(PDF) and result["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert (result["content_type"], result["final_url"], result["http_status"]) == ("application/pdf", url, 200)
    assert not (project.scratch / "raw" / "doc.pdf.part").exists()
    json.dumps(result)


def test_headers_are_exactly_the_two_allowed(project, monkeypatch):
    url = "https://docs.example.com/doc.pdf"
    seen = serve(monkeypatch, {url: FakeResponse(body=PDF)})
    _fetch(project, url)
    (request,) = seen
    assert request.get_method() == "GET" and request.data is None
    assert sorted(request.header_items()) == [("Accept", "*/*"),
                                              ("User-agent", "rwa-due-diligence/0.4 (+read-only research)")]


def test_real_opener_has_no_default_headers_or_cookies(monkeypatch):
    opener_headers = []

    class Probe(fetch.urllib.request.BaseHandler):
        def default_open(self, req):
            opener_headers.extend(self.parent.addheaders)
            handlers.extend(type(h).__name__ for h in self.parent.handlers)
            raise fetch.urllib.error.URLError("probe")

    handlers = []
    real_build = fetch.urllib.request.build_opener

    def build(*extra):
        return real_build(*(extra + (Probe,)))

    monkeypatch.setattr(fetch.urllib.request, "build_opener", build)
    with pytest.raises(fetch.FetchError):
        fetch._get("https://docs.example.com/x")
    assert opener_headers == []
    assert "HTTPCookieProcessor" not in handlers and "_NoRedirect" in handlers
    assert "HTTPRedirectHandler" not in handlers


@pytest.mark.parametrize("url", [
    "http://docs.example.com/doc.pdf",
    "ftp://docs.example.com/doc.pdf",
    "file:///etc/passwd",
    "https://127.0.0.1/doc.pdf",
    "https://[::1]/doc.pdf",
    "https://10.0.0.8:8443/doc.pdf",
    "https://2130706433/doc.pdf",
    "https://0x7f000001/doc.pdf",
    "https://localhost/doc.pdf",
    "https://LOCALHOST./doc.pdf",
    "https://printer.local/doc.pdf",
    "https://wiki.corp.internal/doc.pdf",
    "https://user:pw@docs.example.com/doc.pdf",
    "https:///doc.pdf",
    "https://docs.example.com:99999/doc.pdf",
])
def test_refused_urls_are_invalid_input(project, monkeypatch, url):
    seen = serve(monkeypatch, {})
    with pytest.raises(runstate.InvalidError):
        _fetch(project, url)
    assert seen == []


def test_redirect_followed_when_https_public(project, monkeypatch):
    first, second = "https://a.example.com/doc", "https://cdn.example.net/files/doc.pdf"
    serve(monkeypatch, {first: FakeResponse(302, headers={"Location": "https://cdn.example.net/files/doc.pdf"}),
                        second: FakeResponse(body=PDF)})
    result = _fetch(project, first)
    assert result["final_url"] == second and result["bytes"] == len(PDF)


def test_relative_redirect_is_resolved(project, monkeypatch):
    first, second = "https://a.example.com/x/doc", "https://a.example.com/y/doc.pdf"
    serve(monkeypatch, {first: FakeResponse(301, headers={"Location": "/y/doc.pdf"}), second: FakeResponse(body=PDF)})
    assert _fetch(project, first)["final_url"] == second


@pytest.mark.parametrize("location", ["http://a.example.com/doc.pdf", "https://127.0.0.1/doc.pdf",
                                      "https://localhost/doc.pdf", "https://nas.local/doc.pdf"])
def test_redirect_to_refused_target_is_an_error(project, monkeypatch, location):
    first = "https://a.example.com/doc"
    seen = serve(monkeypatch, {first: FakeResponse(302, headers={"Location": location})})
    with pytest.raises(fetch.FetchError, match="redirect from .* refused"):
        _fetch(project, first)
    assert len(seen) == 1
    assert not (project.scratch / "raw" / "doc.pdf").exists()


def test_five_redirects_allowed_six_refused(project, monkeypatch):
    def chain(n):
        responses = {}
        for i in range(n):
            responses["https://a.example.com/%d" % i] = FakeResponse(
                307, headers={"Location": "https://a.example.com/%d" % (i + 1)})
        responses["https://a.example.com/%d" % n] = FakeResponse(body=PDF)
        return responses

    serve(monkeypatch, chain(5))
    assert _fetch(project, "https://a.example.com/0")["final_url"] == "https://a.example.com/5"
    seen = serve(monkeypatch, chain(6))
    with pytest.raises(fetch.FetchError, match="more than 5 redirects"):
        _fetch(project, "https://a.example.com/0", name="other.pdf")
    assert len(seen) == 6
    assert not (project.scratch / "raw" / "other.pdf").exists()


def test_size_cap_exceeded_while_streaming_leaves_no_file(project, monkeypatch):
    monkeypatch.setattr(fetch, "MAX_BYTES", 1000)
    monkeypatch.setattr(fetch, "CHUNK", 64)
    url = "https://a.example.com/big.pdf"
    serve(monkeypatch, {url: FakeResponse(body=b"x" * 1001)})
    before = walk(project.dir)
    with pytest.raises(fetch.FetchError, match="size cap exceeded"):
        _fetch(project, url)
    assert walk(project.dir) == before


def test_size_cap_from_content_length(project, monkeypatch):
    url = "https://a.example.com/big.pdf"
    seen_reads = []
    response = FakeResponse(body=b"x", headers={"Content-Length": str(fetch.MAX_BYTES + 1)})
    response.read = lambda n=-1: seen_reads.append(n) or b""
    serve(monkeypatch, {url: response})
    with pytest.raises(fetch.FetchError, match="Content-Length"):
        _fetch(project, url)
    assert seen_reads == []
    assert not (project.scratch / "raw" / "doc.pdf").exists()


def test_exact_cap_is_allowed(project, monkeypatch):
    monkeypatch.setattr(fetch, "MAX_BYTES", 1000)
    url = "https://a.example.com/ok.pdf"
    serve(monkeypatch, {url: FakeResponse(body=b"x" * 1000)})
    assert _fetch(project, url)["bytes"] == 1000


@pytest.mark.parametrize("name", ["", ".hidden", "-x.pdf", "a/b.pdf", "a\\b.pdf", "..", "a b.pdf",
                                  "x" * 81, "doc\u00e9.pdf", "doc.pdf\n"])
def test_bad_name_is_invalid_input(project, monkeypatch, name):
    seen = serve(monkeypatch, {})
    with pytest.raises(runstate.InvalidError):
        _fetch(project, "https://a.example.com/doc.pdf", name=name)
    assert seen == []


def test_longest_name_is_allowed(project, monkeypatch):
    url = "https://a.example.com/doc.pdf"
    serve(monkeypatch, {url: FakeResponse(body=PDF)})
    assert _fetch(project, url, name="a" * 80)["bytes"] == len(PDF)


def test_existing_file_needs_overwrite(project, monkeypatch):
    url = "https://a.example.com/doc.pdf"
    target = project.scratch / "raw" / "doc.pdf"
    target.write_bytes(b"old")
    seen = serve(monkeypatch, {url: lambda: FakeResponse(body=PDF)})
    with pytest.raises(runstate.InvalidError, match="already exists"):
        _fetch(project, url)
    assert seen == [] and target.read_bytes() == b"old"
    assert _fetch(project, url, overwrite=True)["bytes"] == len(PDF)
    assert target.read_bytes() == PDF


def test_http_error_is_network_error(project, monkeypatch):
    url = "https://a.example.com/doc.pdf"
    serve(monkeypatch, {url: urllib.error.HTTPError(url, 403, "Forbidden", email.message.Message(), None)})
    with pytest.raises(fetch.FetchError, match="HTTP 403 Forbidden"):
        _fetch(project, url)
    assert not (project.scratch / "raw" / "doc.pdf").exists()


def test_connection_error_is_network_error(project, monkeypatch):
    url = "https://a.example.com/doc.pdf"
    serve(monkeypatch, {url: urllib.error.URLError("timed out")})
    with pytest.raises(fetch.FetchError, match="timed out"):
        _fetch(project, url)


def test_read_failure_leaves_no_file(project, monkeypatch):
    url = "https://a.example.com/doc.pdf"
    response = FakeResponse(body=PDF)

    def broken(n=-1):
        raise TimeoutError("read timed out")

    response.read = broken
    serve(monkeypatch, {url: response})
    with pytest.raises(fetch.FetchError, match="read timed out"):
        _fetch(project, url)
    assert sorted((project.scratch / "raw").iterdir()) == []


def test_needs_a_run(tmp_path):
    with pytest.raises(runstate.ContractError):
        fetch.fetch_file(tmp_path, "acme", "https://a.example.com/doc.pdf", "doc.pdf")


LIVE_URL = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"


@pytest.mark.acceptance
def test_live_fetch_dummy_pdf(project, capsys):
    result = _fetch(project, LIVE_URL)
    with capsys.disabled():
        print("\nFETCH_JSON " + json.dumps(result))
    data = (project.scratch / "raw" / "doc.pdf").read_bytes()
    assert result["http_status"] == 200 and result["final_url"].startswith("https://")
    assert data.startswith(b"%PDF") and result["bytes"] == len(data)
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
