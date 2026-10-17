"""HTML report (D6, D18, D19): golden, safety, class allowlist, links and parity with the Markdown report."""

import copy
import hashlib
import html
import re

from test_support import GOLDEN, ROOT, load_fixture
from lib import render_html, render_md

ASSETS = ROOT / "assets"
LISM = ASSETS / render_html.LISM_CSS


def _body(page):
    return page[page.index("<body>"):]


def _hostile():
    doc = copy.deepcopy(load_fixture())
    bad = '<script>alert(1)</script> " onmouseover="x & a\nb \u00e9'
    doc["narrative"]["executive_summary"] = bad
    doc["entities"][0]["legal_name"]["value"] = bad
    doc["project"]["products"][1]["name"]["note"] = bad
    return doc


# 1. golden ------------------------------------------------------------------------------------------------

def _figures():
    return {pid: (GOLDEN / ("acme.flow-%s.svg" % pid)).read_bytes().decode("utf-8") for pid in ("P1", "P2")}


def test_report_matches_golden():
    expected = (GOLDEN / "acme.report.html").read_bytes().decode("utf-8")
    assert render_html.render(load_fixture(), (), _figures()) == expected


def test_render_twice_identical():
    assert render_html.render(load_fixture()) == render_html.render(load_fixture())


# 2. self-contained, no JavaScript -------------------------------------------------------------------------

def test_self_contained_no_js():
    for page in (render_html.render(load_fixture()), render_html.render(_hostile())):
        low = page.lower()
        for needle in ("<script", "<link", "<iframe", "<object", "<embed", "javascript:", "@import", "src="):
            assert needle not in low, needle
        assert not any(re.search(r"\son[a-z]+=", tag) for tag in re.findall(r"<[^>]*>", low))
        lism = LISM.read_bytes().decode("utf-8")
        assert "url(" not in low.replace(lism.lower(), "")
    css = (ASSETS / "report.css").read_bytes().decode("utf-8")
    assert "url(" not in css and "@import" not in css


def test_template_markers_once():
    tmpl = (ASSETS / render_html.TEMPLATE).read_bytes().decode("utf-8")
    for marker in ("<!--DD:TITLE-->", "<!--DD:LISM_CSS-->", "<!--DD:REPORT_CSS-->", "<!--DD:BODY-->"):
        assert tmpl.count(marker) == 1
    assert "<!--DD:" not in render_html.render(load_fixture())


# 3. escaping ----------------------------------------------------------------------------------------------

def test_hostile_text_is_escaped():
    body = _body(render_html.render(_hostile()))
    assert "<script>" not in body
    assert '" onmouseover="x' not in body
    assert " & " not in body
    assert "a\nb" not in body
    escaped = "&lt;script&gt;alert(1)&lt;/script&gt; &quot; onmouseover=&quot;x &amp; a b &#233;"
    assert body.count(escaped) == 3
    body.encode("ascii")
    print("\nESCAPED " + escaped)


# 4. class allowlist ---------------------------------------------------------------------------------------

def _css_classes(css):
    return set(re.findall(r"\.(-?[A-Za-z_][A-Za-z0-9_-]*)", css))


def test_class_allowlist():
    report_css = _css_classes((ASSETS / "report.css").read_bytes().decode("utf-8"))
    lism_css = _css_classes(LISM.read_bytes().decode("utf-8"))
    page = render_html.render(load_fixture(), [(1, "accept N1\n")])
    used = {tok for attr in re.findall(r'class="([^"]*)"', _body(page)) for tok in attr.split()}
    assert used
    for tok in used:
        assert (tok.startswith("dd-") and tok in report_css) or tok in lism_css, tok
    assert {"is--wrapper", "has--gutter", "l--flow"} <= used


# 5. links -------------------------------------------------------------------------------------------------

def test_links_and_anchors():
    doc = copy.deepcopy(load_fixture())
    doc["sources"][0]["url"] = "javascript:alert(1)"
    body = _body(render_html.render(doc))
    assert not re.search(r'<a [^>]*href="javascript', body, re.I)
    row = re.search(r'<tr id="src-S1">.*?</tr>', body).group(0)
    assert "<a " not in row and "javascript:alert(1)" in row
    row2 = re.search(r'<tr id="src-S2">.*?</tr>', body).group(0)
    assert '<a href="https://regulator.example/register/AAM-0042" rel="noopener noreferrer nofollow" ' \
           'target="_blank">' in row2
    ids = set(re.findall(r'id="([^"]+)"', body))
    targets = re.findall(r'href="#([^"]+)"', body)
    assert targets and all(t in ids for t in targets)
    assert {"s%d" % i for i in range(1, 15)} <= set(targets)


def test_html_url_helper():
    from lib.textutil import html_url
    assert html_url("HTTPS://a.example/x?a=1&b=2") == "HTTPS://a.example/x?a=1&amp;b=2"
    for bad in ("javascript:alert(1)", "https://a.example/ x", "ftp://a.example/", "https://a\u0007", "data:x"):
        assert html_url(bad) is None


# 6. structure parity with Markdown ------------------------------------------------------------------------

def _md_plain(line):
    return re.sub(r"\\(.)", r"\1", line)


def _html_plain(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment))


def test_heading_parity():
    rounds = [(1, "accept N1\n"), (2, "finalize\n")]
    for doc in (load_fixture(), _hostile()):
        md = render_md.render(doc, rounds).split("\n")
        page = render_html.render(doc, rounds)
        for level in (2, 3):
            md_heads = [_md_plain(line[level + 1:]) for line in md if line.startswith("#" * level + " ")]
            html_heads = [_html_plain(h) for h in re.findall(r"<h%d>(.*?)</h%d>" % (level, level), page)]
            assert html_heads == md_heads and md_heads


def test_toc_lists_every_section():
    page = render_html.render(load_fixture())
    sections = re.findall(r'<section id="([^"]+)"', page)
    toc = re.search(r'<nav class="dd-toc">(.*?)</nav>', page, re.S).group(1)
    assert re.findall(r'href="#([^"]+)"', toc) == sections and len(sections) == 17


def test_flow_placeholders_and_blocking_panel():
    page = render_html.render(load_fixture())
    assert '<figure class="dd-flow" id="flow-P1"></figure>' in page
    assert '<figure class="dd-flow" id="flow-P2"></figure>' in page
    assert '<section id="s2" class="dd-section l--flow dd-panel dd-panel--blocking">' in page
    assert re.search(r'<span class="dd-kind dd-kind--[a-z_]+">', page)


def test_none_handling_matches_markdown():
    doc = copy.deepcopy(load_fixture())
    doc["audits"] = []
    doc["open_questions"] = []
    page = render_html.render(doc)
    s9 = re.search(r'<section id="s9".*?</section>', page, re.S).group(0)
    s13 = re.search(r'<section id="s13".*?</section>', page, re.S).group(0)
    assert '<p class="dd-none">none</p>' in s9 and '<p class="dd-none">none</p>' in s13
    a = re.search(r'<section id="appendix-a".*?</section>', page, re.S).group(0)
    assert '<p class="dd-none">none</p>' in a


def test_appendix_a_pre_escaped():
    page = render_html.render(load_fixture(), [(1, "accept N1\r\n# <b>&\n\n")])
    assert '<h3>Round 1</h3>\n<pre class="dd-pre">accept N1\n# &lt;b&gt;&amp;</pre>' in page


def test_solana_ref_renders():
    doc = copy.deepcopy(load_fixture())
    doc["flows"]["nodes"][0]["ref"] = "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV1"
    assert "<td>7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV1</td>" in render_html.render(doc)


# 7. draft banner ------------------------------------------------------------------------------------------

def test_draft_banner_only_for_draft():
    doc = load_fixture()
    assert '<p class="dd-banner dd-banner--draft">DRAFT -- not finalized</p>' in render_html.render(doc)
    doc["run"].update({"status": "final", "finalized_at": "2026-10-02T00:00:00Z"})
    assert "DRAFT" not in render_html.render(doc)


# 9. asset integrity ---------------------------------------------------------------------------------------

def test_lism_sha256_recorded():
    digest = hashlib.sha256(LISM.read_bytes()).hexdigest()
    notes = (ROOT / "references" / "third-party.md").read_bytes().decode("utf-8")
    assert "sha256: `%s`" % digest in notes
    assert render_html.LISM_CSS in notes


# P3: inline flow figures ----------------------------------------------------------------------------------

def test_figures_embedded_with_caption():
    page = render_html.render(load_fixture(), (), _figures())
    for pid in ("P1", "P2"):
        fig = re.search(r'<figure class="dd-flow" id="flow-%s">\n(<svg .*?)\n<figcaption>(.*?)</figcaption></figure>'
                        % pid, page, re.S)
        assert fig and fig.group(1) == _figures()[pid].rstrip("\n")
        assert fig.group(2) == ("Fund flow %s: lanes off-chain / boundary / on-chain; marker after each label"
                                " = claim status" % pid)
    assert "<?xml" not in page


def test_partial_figures_keep_empty_placeholder():
    page = render_html.render(load_fixture(), (), {"P1": _figures()["P1"]})
    assert '<figure class="dd-flow" id="flow-P2"></figure>' in page
    assert '<figure class="dd-flow" id="flow-P1"></figure>' not in page


def test_page_with_figures_has_no_active_content():
    low = render_html.render(load_fixture(), (), _figures()).lower()
    for needle in ("<script", "<foreignobject", "<link", "<iframe", "javascript:", "@import", "src="):
        assert needle not in low, needle
    assert not any(re.search(r"\son[a-z]+=", tag) for tag in re.findall(r"<[^>]*>", low))
    assert not re.search(r"""href\s*=\s*["']?\s*(https?:|//)""", low.split("<section id=\"s14\"")[0])
    rest = low.replace(LISM.read_bytes().decode("utf-8").lower(), "")
    assert rest.count("url(") == len(re.findall(r"""url\(\s*["']?(?:data:application/font-woff;|#)""", rest)) > 0
    assert low.isascii()


def test_heading_parity_with_figures():
    md = render_md.render(load_fixture(), (), _figures()).split("\n")
    page = render_html.render(load_fixture(), (), _figures())
    md_heads = [_md_plain(line[4:]) for line in md if line.startswith("### ")]
    assert [_html_plain(h) for h in re.findall(r"<h3>(.*?)</h3>", page)] == md_heads


def test_css_c6_and_flow_rules():
    css = (ASSETS / "report.css").read_bytes().decode("utf-8")
    assert ".dd-table td:first-child, .dd-table th:first-child { white-space: nowrap; }" in css
    assert ".dd-meta__row dd { margin: 0; overflow-wrap: break-word; }" in css
    assert ".dd-flow svg { width: 100%; height: auto; max-height: 80vh; }" in css
    assert ".dd-flow { break-inside: avoid; }" in css
