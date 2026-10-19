"""Fund-flow diagrams (D11, D12, D21, D45): D2 source per strategy and view, and the d2 v0.9.0 renderer wrapper.

build_d2 is pure. This is the only module that starts a subprocess: the pinned d2 binary, with explicit flags.
"""

import re
import shutil
import subprocess

from lib import framework, schema
from lib.textutil import id_key

D2_VERSION = "v0.9.0"
LABEL_MAX = 40

HEADER = """direction: down
vars: {
  d2-config: {
    layout-engine: elk
    theme-id: 0
  }
}"""

LANES = (("offchain", "Off-chain"), ("boundary", "Boundary"), ("onchain", "On-chain"))

SHAPES = {
    "investor": "shape: person",
    "entity": "shape: rectangle",
    "contract": "shape: rectangle; style.border-radius: 8",
    "pool": "shape: rectangle; style.border-radius: 8",
    "wallet": "shape: rectangle; style.border-radius: 8",
    "multisig": "shape: rectangle; style.border-radius: 8; style.double-border: true",
    "bank_account": "shape: cylinder",
    "asset": "shape: hexagon",
}

# kind -> (stroke colour, stroke-dash or None)
EDGE_STYLES = {
    "subscription": ("#2563eb", None),
    "redemption": ("#2563eb", 5),
    "yield": ("#16a34a", None),
    "fee": ("#6b7280", 2),
    "custody": ("#9333ea", None),
    "conversion": ("#0891b2", 3),
    "collateral": ("#b91c1c", 4),
}

FLAG_SUFFIX = {"CONFIRMED": " [C]", "SELF_REPORTED": " [S]", "THIRD_PARTY_REPORTED": " [T]", "INFERRED": " [I]",
               "UNRESOLVED": " [U]", "CONFLICTING": " [X]"}
FLAG_OPACITY = {"SELF_REPORTED": 0.7, "THIRD_PARTY_REPORTED": 0.7, "INFERRED": 0.7, "UNRESOLVED": 0.5}
VIEWS = schema.ENUMS["flow_view"]

LABEL_ALLOWED = re.compile(r"[^A-Za-z0-9 .,:;()/&+%@'_=-]")
NODE_ID = re.compile(r"^n[1-9][0-9]*$")

# Every flag that has an environment variable twin is pinned, so D2_*, SCALE, OMIT_VERSION and DEBUG
# cannot change the output (the second group was found by probing v0.9.0; it leaves default output unchanged).
D2_FLAGS = ["--layout=elk", "--theme=0", "--dark-theme=-1", "--pad=24", "--scale=-1", "--center=false",
            "--sketch=false", "--bundle=true", "--timeout=60",
            "--omit-version=false", "--animate-interval=0", "--no-xml-tag=false", "--debug=false",
            "--force-appendix=false", "--font-regular=", "--font-italic=", "--font-bold=", "--font-semibold=",
            "--font-mono=", "--font-mono-bold=", "--font-mono-italic=", "--font-mono-semibold=",
            "--stdout-format=svg", "-", "-"]


class DependencyError(Exception):
    """d2 is missing or not the pinned version (CLI exit 4)."""


class RenderError(Exception):
    """d2 failed or produced an SVG that the sanitizer rejects."""


# --------------------------------------------------------------------------- D2 source

def clean_label(text):
    """Reduce to the allowed alphabet, collapse runs of spaces, trim, clip (3.1 rule 6)."""
    return " ".join(LABEL_ALLOWED.sub(" ", text).split())[:LABEL_MAX]


def d2_label(text):
    return '"%s"' % clean_label(text)


def _node_id(ident):
    if not isinstance(ident, str) or not NODE_ID.match(ident):
        raise ValueError("flow node id %r is not a schema id n<k>" % (ident,))
    return ident


def view_edges(doc, strategy_id, view):
    """[(index, edge), ...] of the strategy's edges in one view, in document order."""
    return [(i, e) for i, e in enumerate(doc["flows"]["edges"])
            if strategy_id in e["strategies"] and e["view"] == view]


def figure_keys(doc):
    """`T<n>-<view>` for every (strategy, view) with at least one edge: strategy id order, then view order."""
    return ["%s-%s" % (t["id"], view) for t in sorted(doc["strategies"], key=id_key) for view in VIEWS
            if view_edges(doc, t["id"], view)]


def build_d2(doc, strategy_id, view):
    """D2 source of one strategy's fund flow in one view; same document -> same bytes on every OS."""
    selected = view_edges(doc, strategy_id, view)
    edges = [e for _, e in selected]
    edge_flags = framework.flags(doc)
    by_id = {n["id"]: n for n in doc["flows"]["nodes"]}
    used = sorted({e["from"] for e in edges} | {e["to"] for e in edges}, key=id_key)
    nodes = [by_id[nid] for nid in used]

    blocks = [HEADER]
    for lane, title in LANES:
        members = [n for n in nodes if n["lane"] == lane]
        if not members:
            continue
        lines = ["%s: %s {" % (lane, d2_label(title)), "  direction: right", '  style.fill: "#f8fafc"',
                 '  style.stroke: "#cbd5e1"', "  style.font-size: 14"]
        for n in members:
            lines.append('  %s: %s {%s; style.font-size: 13; style.fill: "#ffffff"}'
                         % (_node_id(n["id"]), d2_label(n["label"]), SHAPES[n["kind"]]))
        lines.append("}")
        blocks.append("\n".join(lines))

    lines = []
    for index, e in selected:
        src, dst = by_id[e["from"]], by_id[e["to"]]
        claim = e["claim"]
        fl = edge_flags[("flows", "edges", index, "claim")]
        suffix = FLAG_SUFFIX[fl]
        if fl == "UNRESOLVED" and not claim["evidence"]:
            suffix = " [U?]"
        colour, dash = EDGE_STYLES[e["kind"]]
        style = 'style.stroke: "%s"; style.font-size: 12' % colour
        if dash is not None:
            style += "; style.stroke-dash: %d" % dash
        if fl in FLAG_OPACITY:
            style += "; style.opacity: %s" % FLAG_OPACITY[fl]
        lines.append('%s.%s -> %s.%s: "%s%s" {%s}' % (
            src["lane"], _node_id(src["id"]), dst["lane"], _node_id(dst["id"]),
            clean_label(e["label"]), suffix, style))
    if lines:
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


# --------------------------------------------------------------------------- renderer

def find_d2():
    return shutil.which("d2")


def check_d2(path):
    try:
        proc = subprocess.run([path, "--version"], capture_output=True, timeout=30, check=False, shell=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DependencyError("d2 %s required, found none (%s)" % (D2_VERSION, exc))
    found = proc.stdout.decode("utf-8", errors="replace").strip()
    if found != D2_VERSION:
        raise DependencyError("d2 %s required, found %s" % (D2_VERSION, found or "no version"))


def render_svg(d2_source, d2_path, env=None):
    """Run d2 on the source; env is for tests only (None inherits the caller's environment)."""
    try:
        proc = subprocess.run([d2_path] + D2_FLAGS, input=d2_source.encode("utf-8"), capture_output=True,
                              timeout=90, check=False, shell=False, env=env)
    except subprocess.TimeoutExpired:
        raise RenderError("d2 timed out after 90 s")
    except OSError as exc:
        raise RenderError("d2 could not run: %s" % exc)
    if proc.returncode != 0:
        raise RenderError("d2 exit %d: %s" % (proc.returncode,
                                              proc.stderr.decode("utf-8", errors="replace")[:500]))
    return proc.stdout.decode("utf-8")


XML_DECL = re.compile(r"\A\s*<\?xml[^>]*\?>\s*")
TAG = re.compile(r"<[^>]*>")
EVENT_ATTR = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)
BAD_HREF = re.compile(r"""(?:xlink:)?href\s*=\s*["']?\s*(?:https?:|//|javascript:)""", re.IGNORECASE)


def sanitize_svg(svg):
    """Strip the XML declaration and reject active or external content."""
    svg = XML_DECL.sub("", svg, count=1).replace("\r\n", "\n").replace("\r", "\n")
    low = svg.lower()
    for needle in ("<script", "<foreignobject", "@import"):
        if needle in low:
            raise RenderError("SVG rejected: contains %s" % needle)
    for tag in TAG.findall(svg):
        if EVENT_ATTR.search(tag):
            raise RenderError("SVG rejected: event attribute in %s" % tag[:80])
        if BAD_HREF.search(tag):
            raise RenderError("SVG rejected: external or script link in %s" % tag[:80])
    return svg


def render_all(doc, d2_path, env=None):
    """Sanitized SVG per `T<n>-<view>` key (figure_keys order), only for pairs with at least one edge."""
    out = {}
    for key in figure_keys(doc):
        strategy_id, view = key.split("-", 1)
        out[key] = sanitize_svg(render_svg(build_d2(doc, strategy_id, view), d2_path, env=env))
    return out
