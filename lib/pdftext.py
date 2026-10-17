"""PDF text extraction with pypdf (D25): optional dependency, imported only when a PDF is read.

Reads <project>/.scratch/raw/NAME and writes <project>/.scratch/text/NAME.txt (UTF-8, LF), one
"=== page <n> ===" line before the text of each page.
"""

from lib import fetch, runstate

PYPDF_VERSION = "6.21.1"


class DependencyError(Exception):
    """pypdf is not installed (CLI exit 4)."""


def load_pypdf():
    try:
        import pypdf
    except ImportError:
        raise DependencyError("pypdf %s required: python -m pip install --user pypdf==%s"
                              % (PYPDF_VERSION, PYPDF_VERSION))
    return pypdf


def page_texts(path):
    pypdf = load_pypdf()
    try:
        reader = pypdf.PdfReader(str(path))
        return [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # pypdf raises many error types on malformed input
        raise runstate.InvalidError(["%s: not a readable PDF (%s: %s)" % (path.name, type(exc).__name__, exc)])


def join_pages(pages):
    parts = []
    for number, text in enumerate(pages, 1):
        body = text.replace("\r\n", "\n").replace("\r", "\n")
        if body and not body.endswith("\n"):
            body += "\n"
        parts.append("=== page %d ===\n%s" % (number, body))
    return "".join(parts)


def pdf_text(root, slug, name):
    project = runstate.open_project(root, slug)
    fetch.check_name(name)
    source = project.safe(project.scratch / "raw" / name)
    if not source.is_file():
        raise runstate.InvalidError(["name: %s not found in .scratch/raw" % name])
    pages = page_texts(source)
    text = join_pages(pages).encode("utf-8", errors="replace").decode("utf-8")
    path = project.write_text(project.scratch / "text" / (name + ".txt"), text)
    return {"path": str(path), "pages": len(pages), "chars": len(text)}
