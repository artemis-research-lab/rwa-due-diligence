"""v0.5.0 migration rwa-dd/1.0 -> 2.0 (lib/migrate.py)."""

import copy

from test_support import GOLDEN, fixture_sources, load_v1
from lib import migrate, validate
from lib.textutil import dump_json

# Fixed run block of tests/golden/acme_v1.migrated.json.
RUN = {"run_id": "acme-20261101T000000Z", "slug": "acme", "root_url": "https://acme-yield.example/", "round": 1,
       "status": "draft", "started_at": "2026-11-01T00:00:00Z", "finalized_at": None, "skill_version": "0.5.0",
       "seeded_from": "acme-20261001T080000Z"}


def test_v1_fixture_is_still_1_0():
    assert load_v1()["schema_version"] == "rwa-dd/1.0"


def test_convert_matches_golden():
    expected = (GOLDEN / "acme_v1.migrated.json").read_bytes().decode("utf-8")
    assert dump_json(migrate.convert(load_v1(), RUN)) == expected


def test_converted_doc_validates_with_v1_ledger():
    assert validate.validate_document(migrate.convert(load_v1(), RUN), fixture_sources()) == []


def test_convert_does_not_mutate_input():
    old = load_v1()
    before = copy.deepcopy(old)
    migrate.convert(old, RUN)
    assert old == before


def test_every_role_and_relationship_is_unmapped():
    old = load_v1()
    facts = [x["fact"] for x in migrate.convert(old, RUN)["x_unmapped"]]
    assert facts[0] == old["x_unmapped"][0]["fact"]
    for e in old["entities"]:
        assert "%s roles in rwa-dd/1.0: %s" % (e["id"], ", ".join(e["roles"])) in facts
    for r in old["relationships"]:
        assert any(f.startswith("%s %s %s: " % (r["from"], r["type"], r["to"])) for f in facts)
    unmapped = migrate.convert(old, RUN)["x_unmapped"]
    assert unmapped[-1] == {"fact": "E3 custodies P1: true", "evidence": ["S8"],
                            "why_unmapped": "rwa-dd/1.0 relationship; re-map into interfaces"}


def test_strategies_holder_rights_and_flows():
    doc = migrate.convert(load_v1(), RUN)
    assert [(t["id"], t["products"], t["name"]) for t in doc["strategies"]] == [
        ("T1", ["P1"], "Acme Senior Note"), ("T2", ["P2"], "Acme Treasury Vault")]
    assert all(e["functions"] == [] for e in doc["entities"])
    assert [h["governing_law"]["value"] for h in doc["holder_rights"]] == ["Examplestan", "Examplestan"]
    assert doc["holder_rights"][0]["look_through"]["status"] == "not_found"
    assert {n["layer"] for n in doc["flows"]["nodes"]} == {None}
    conversion = [e for e in doc["flows"]["edges"] if e["label"] == "stablecoin to fiat"][0]
    assert (conversion["view"], conversion["strategies"], conversion["interface"]) == \
        ("settlement", ["T1", "T2"], None)
    assert doc["interfaces"] == [] and doc["issuer_requests"] == [] and doc["next_searches"] == []
    assert all(f["subjects"] == [] for f in doc["findings"])
    assert "loss_absorption" not in doc["yield"][0]


def test_loss_absorption_string_wrapped_as_list():
    old = load_v1()
    old["yield"][0]["loss_absorption"] = {"value": "First-loss tranche held by the manager",
                                          "status": "self_reported", "evidence": ["S8"], "subject": "P1",
                                          "note": "From the memorandum."}
    waterfall = migrate.convert(old, RUN)["strategies"][0]["default_path"]["loss_waterfall"]
    assert waterfall == {"value": ["First-loss tranche held by the manager"], "status": "self_reported",
                         "evidence": ["S8"], "subject": "P1", "note": "From the memorandum."}
    assert validate.validate_document(migrate.convert(old, RUN), fixture_sources()) == []


def test_unnamed_product_strategy_name():
    old = load_v1()
    old["project"]["products"][1]["name"] = {"value": None, "status": "not_found", "evidence": [], "subject": None,
                                             "note": ""}
    assert migrate.convert(old, RUN)["strategies"][1]["name"] == "Strategy for P2"
