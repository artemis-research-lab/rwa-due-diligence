from test_support import ROOT, run_cli
from lib import schema, validate


def test_schema_doc_matches_committed_reference():
    # test 11
    committed = (ROOT / "references" / "schema.md").read_bytes().decode("utf-8")
    assert schema.schema_doc() == committed
    code, out, _ = run_cli(["schema-doc"])
    assert code == 0 and out == committed


def test_schema_doc_is_deterministic_and_ascii():
    text = schema.schema_doc()
    assert text == schema.schema_doc()
    assert text.isascii() and text.endswith("\n") and not text.endswith("\n\n")


def test_skeleton_is_structurally_valid_once_run_is_filled():
    doc = schema.skeleton(schema.DOCUMENT)
    doc["run"].update({"run_id": "x", "slug": "acme", "root_url": "https://a.example/",
                       "status": "draft", "started_at": "2026-01-01T00:00:00Z",
                       "skill_version": "0.1.0"})
    product = schema.skeleton(schema.PRODUCT)
    product["id"] = "P1"
    doc["project"]["products"] = [product]
    assert validate.structural_errors(doc) == []


def test_order_like_schema_keeps_schema_order():
    doc = {"x_unmapped": [], "schema_version": "rwa-dd/1.0", "zzz": 1}
    assert list(schema.order_like_schema(doc)) == ["schema_version", "x_unmapped", "zzz"]
