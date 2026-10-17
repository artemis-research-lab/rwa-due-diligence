"""C4 / D20: text data files are LF-only in the repository."""

import pytest

from test_support import ROOT

DIRS = ("tests/fixtures", "tests/golden", "assets", "references")


@pytest.mark.parametrize("rel", DIRS)
def test_no_carriage_return(rel):
    files = [p for p in (ROOT / rel).rglob("*") if p.is_file()]
    assert files
    offenders = [str(p.relative_to(ROOT)) for p in files if b"\r" in p.read_bytes()]
    assert offenders == []
