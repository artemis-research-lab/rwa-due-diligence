"""P3 fund-flow diagrams (D11, D12, D21): D2 source, escaping, lanes, d2 wrapper, sanitizer, version check."""

import copy
import os
import re
import subprocess
import sys
import warnings

import pytest

from test_support import GOLDEN, load_fixture
from lib import flow

D2 = flow.find_d2()
# The d2 tests run only when the binary is on PATH; Block B of every build must show them as passed.
# pytest.ini (out of scope for P3) does not register the d2 marker yet, hence the local warning filter.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", pytest.PytestUnknownMarkWarning)
    D2_MARK = pytest.mark.d2
needs_d2 = [D2_MARK, pytest.mark.skipif(D2 is None, reason="d2 %s not on PATH" % flow.D2_VERSION)]

HOSTILE = 'a"b\\c}d{e#f$g|h<i>j\nk \u00e9\u4e2d ${x} \'ok\' (1/2) & 50% @x_y=z-1;:,.'


def _golden(name):
    return (GOLDEN / name).read_bytes().decode("utf-8")


def _apply(*marks):
    def wrap(fn):
        for mark in reversed(marks):
            fn = mark(fn)
        return fn
    return wrap


def _quoted(source):
    return re.findall(r'"([^"]*)"', source)


# 1. D2 source golden ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("pid", ["P1", "P2"])
def test_d2_source_matches_golden(pid):
    assert flow.build_d2(load_fixture(), pid) == _golden("acme.flow-%s.d2" % pid)


def test_d2_source_shape():
    source = flow.build_d2(load_fixture(), "P1")
    assert source.startswith("direction: down\nvars: {\n  d2-config: {\n    layout-engine: elk\n"
                             "    theme-id: 0\n  }\n}\n")
    assert source.endswith("\n") and not source.endswith("\n\n") and "\r" not in source


# 2. escaping -----------------------------------------------------------------------------------------------

def _hostile_doc():
    doc = copy.deepcopy(load_fixture())
    for node in doc["flows"]["nodes"]:
        node["label"] = HOSTILE
    for edge in doc["flows"]["edges"]:
        edge["label"] = HOSTILE
    return doc


def test_hostile_labels_reduced_to_alphabet():
    source = flow.build_d2(_hostile_doc(), "P1")
    allowed = re.compile(r"^[A-Za-z0-9 .,:;()/&+%@'_=-]*$")
    labels = [q for q in _quoted(source) if not q.startswith("#")]
    assert labels
    for label in labels:
        text = re.sub(r" \[(V|S|I|N|N\?)\]$", "", label)
        assert allowed.match(text) and "  " not in text and text == text.strip(), label
    assert flow.clean_label(HOSTILE) == "a b c d e f g h i j k x 'ok' (1/2) & 50% @x_y=z-1;:,."[:40]
    for ch in '"\\{}#$|<>\n\u00e9':
        assert ch not in flow.clean_label(HOSTILE)
    assert source.isascii() and "$" not in source and "\\" not in source
    # Every line outside the lane bodies is structural: one opening and one closing brace per node/edge line.
    for line in source.split("\n"):
        if " -> " in line or re.match(r"^  n\d+: ", line):
            assert line.count("{") == 1 and line.count("}") == 1 and line.count('"') % 2 == 0


def test_label_clipped_to_40():
    assert len(flow.clean_label("x" * 100)) == 40
    assert flow.d2_label("  a \t b  ") == '"a b"'


def test_non_schema_node_id_rejected():
    doc = copy.deepcopy(load_fixture())
    doc["flows"]["nodes"][0]["id"] = 'n1"; x'
    for edge in doc["flows"]["edges"]:
        for end in ("from", "to"):
            if edge[end] == "n1":
                edge[end] = 'n1"; x'
    with pytest.raises(ValueError):
        flow.build_d2(doc, "P1")


@_apply(*needs_d2)
def test_hostile_source_compiles():
    svg = flow.sanitize_svg(flow.render_svg(flow.build_d2(_hostile_doc(), "P1"), D2))
    assert svg.startswith("<svg")


# 3. lanes --------------------------------------------------------------------------------------------------

def test_onchain_only_product_emits_only_onchain_lane():
    doc = copy.deepcopy(load_fixture())
    doc["flows"]["edges"] = [e for e in doc["flows"]["edges"] if e["from"] in ("n1", "n3") and e["to"] in ("n1", "n3")]
    source = flow.build_d2(doc, "P2")
    assert "onchain: \"On-chain\" {" in source
    assert "offchain:" not in source and "boundary:" not in source


def test_lane_order_fixed():
    source = flow.build_d2(load_fixture(), "P1")
    positions = [source.index('%s: "' % lane) for lane in ("offchain", "boundary", "onchain")]
    assert positions == sorted(positions)


def test_nodes_sorted_and_edge_styles():
    source = flow.build_d2(load_fixture(), "P2")
    ids = re.findall(r"^  (n\d+): ", source, re.M)
    assert ids == ["n6", "n9", "n5", "n1", "n3", "n4"]
    assert ('onchain.n3 -> onchain.n4: "reserve pledge [N]" {style.stroke: "#b91c1c"; style.font-size: 12; '
            'style.stroke-dash: 4; style.opacity: 0.5}') in source
    assert "style.double-border: true" in source


def test_not_found_without_evidence_marker():
    doc = copy.deepcopy(load_fixture())
    edge = [e for e in doc["flows"]["edges"] if e["label"] == "reserve pledge"][0]
    edge["claim"]["evidence"] = []
    assert '"reserve pledge [N?]"' in flow.build_d2(doc, "P2")


# 4. SVG golden and 5. environment independence -------------------------------------------------------------

@_apply(*needs_d2)
@pytest.mark.parametrize("pid", ["P1", "P2"])
def test_svg_matches_golden(pid):
    svg = flow.sanitize_svg(flow.render_svg(flow.build_d2(load_fixture(), pid), D2))
    assert svg == _golden("acme.flow-%s.svg" % pid)


@_apply(*needs_d2)
@pytest.mark.parametrize("pid", ["P1", "P2"])
def test_svg_independent_of_d2_environment(pid):
    env = dict(os.environ, D2_LAYOUT="dagre", D2_THEME="200", D2_PAD="5", D2_SKETCH="true", SCALE="2",
               OMIT_VERSION="true", D2_FONT_REGULAR="missing.ttf", D2_ANIMATE_INTERVAL="500", DEBUG="true")
    svg = flow.sanitize_svg(flow.render_svg(flow.build_d2(load_fixture(), pid), D2, env=env))
    assert svg == _golden("acme.flow-%s.svg" % pid)


@_apply(*needs_d2)
def test_render_all_in_product_order():
    figures = flow.render_all(load_fixture(), D2)
    assert list(figures) == ["P1", "P2"]
    assert figures["P1"] == _golden("acme.flow-P1.svg")


@_apply(*needs_d2)
def test_check_d2_accepts_pinned_binary():
    flow.check_d2(D2)


def test_render_error_carries_stderr():
    with pytest.raises(flow.RenderError) as exc:
        flow.render_svg("a -> b\n", sys.executable)
    assert "d2 exit" in str(exc.value)


# 6. sanitizer ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    '<svg><script>alert(1)</script></svg>',
    '<svg onload="alert(1)"></svg>',
    '<svg><foreignObject><div/></foreignObject></svg>',
    '<svg><a href="https://x"><text>x</text></a></svg>',
    '<svg><a xlink:href="javascript:alert(1)"></a></svg>',
    '<svg><use href="//evil.example/x.svg#a"/></svg>',
    '<svg><style>@import url(x.css);</style></svg>',
])
def test_sanitizer_rejects(bad):
    with pytest.raises(flow.RenderError):
        flow.sanitize_svg(bad)


def test_sanitizer_strips_declaration_and_keeps_text():
    svg = '<?xml version="1.0" encoding="utf-8"?><svg><text>pay onx=1</text><use href="#a"/></svg>\r\n'
    assert flow.sanitize_svg(svg) == '<svg><text>pay onx=1</text><use href="#a"/></svg>\n'


# 7. version check ------------------------------------------------------------------------------------------

def _fake_d2(tmp_path, monkeypatch, output):
    script = tmp_path / "fake_d2.py"
    script.write_bytes(("import sys\nsys.stdout.write(%r)\n" % output).encode("utf-8"))
    real_run = subprocess.run

    def run(argv, **kwargs):
        if argv[0] == str(script):
            argv = [sys.executable, str(script)] + list(argv[1:])
        return real_run(argv, **kwargs)

    monkeypatch.setattr(flow.subprocess, "run", run)
    return str(script)


def test_wrong_version_rejected(tmp_path, monkeypatch):
    fake = _fake_d2(tmp_path, monkeypatch, "v0.8.0\n")
    with pytest.raises(flow.DependencyError) as exc:
        flow.check_d2(fake)
    assert str(exc.value) == "d2 v0.9.0 required, found v0.8.0"


def test_pinned_version_accepted_from_fake(tmp_path, monkeypatch):
    flow.check_d2(_fake_d2(tmp_path, monkeypatch, "v0.9.0\n"))


def test_missing_binary_rejected(tmp_path):
    with pytest.raises(flow.DependencyError):
        flow.check_d2(str(tmp_path / "no-such-d2"))
