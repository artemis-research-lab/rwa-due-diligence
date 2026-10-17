import test_support  # noqa: F401
from lib import textutil


def test_md_escape_specials_and_newlines():
    assert textutil.md_escape("a|b*c_d[e]f<g>h#i`j\\k") == "a\\|b\\*c\\_d\\[e\\]f\\<g\\>h\\#i\\`j\\\\k"
    assert textutil.md_escape("x\ny\r\nz\tw") == "x y z w"


def test_clip_is_hard_cut():
    assert textutil.clip("abcdef", 3) == "abc"
    assert textutil.clip("ab", 3) == "ab"
    assert textutil.md_text("<<<<", 2) == "\\<\\<"


def test_load_json_rejects_nan():
    import pytest
    with pytest.raises(ValueError):
        textutil.load_json_text('{"a": NaN}')
