"""P4 PDF text helper (D25): page separators, UTF-8 LF output, missing pypdf, bad input."""

import shutil
import sys

import pytest

from test_support import FIXTURES, clock_at
from lib import pdftext, runstate

EXPECTED = "=== page 1 ===\nSample page one\n=== page 2 ===\nSample page two\n"


@pytest.fixture
def project(tmp_path):
    runstate.init(tmp_path, "acme", "https://a.example/", clock=clock_at())
    project = runstate.open_project(tmp_path, "acme")
    shutil.copyfile(FIXTURES / "sample.pdf", project.scratch / "raw" / "sample.pdf")
    return project


def test_extracts_pages_with_separators(project):
    result = pdftext.pdf_text(project.root, "acme", "sample.pdf")
    path = project.scratch / "text" / "sample.pdf.txt"
    assert result == {"path": str(path.resolve()), "pages": 2, "chars": len(EXPECTED)}
    assert path.read_bytes() == EXPECTED.encode("utf-8")


def test_join_pages_normalises_line_endings():
    assert pdftext.join_pages(["a\r\nb\rc", "", "d\n"]) == \
        "=== page 1 ===\na\nb\nc\n=== page 2 ===\n=== page 3 ===\nd\n"


def test_missing_pypdf_names_the_install_command(project, monkeypatch):
    monkeypatch.setitem(sys.modules, "pypdf", None)
    with pytest.raises(pdftext.DependencyError) as info:
        pdftext.pdf_text(project.root, "acme", "sample.pdf")
    version = pdftext.PYPDF_VERSION
    assert str(info.value) == "pypdf %s required: python -m pip install --user pypdf==%s" % (version, version)
    assert not (project.scratch / "text" / "sample.pdf.txt").exists()


def test_missing_raw_file_is_invalid(project):
    with pytest.raises(runstate.InvalidError, match="not found"):
        pdftext.pdf_text(project.root, "acme", "absent.pdf")


def test_bad_name_is_invalid(project):
    with pytest.raises(runstate.InvalidError):
        pdftext.pdf_text(project.root, "acme", "../sample.pdf")


def test_not_a_pdf_is_invalid(project):
    (project.scratch / "raw" / "junk.pdf").write_bytes(b"<html>not a pdf</html>")
    with pytest.raises(runstate.InvalidError, match="not a readable PDF"):
        pdftext.pdf_text(project.root, "acme", "junk.pdf")
