"""v0.5.0 migration rwa-dd/1.0 -> 2.0 and v0.6.0 migration 2.0 -> 2.1 (lib/migrate.py)."""

import copy
import json

import pytest

from test_support import FIXTURES, GOLDEN, fixture_sources, load_fixture, load_v1
from lib import migrate, schema, validate
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


def test_convert_still_emits_2_0():
    doc = migrate.convert(load_v1(), RUN)
    assert doc["schema_version"] == "rwa-dd/2.0" and "supports" not in doc
    assert all("component" not in t for t in doc["strategies"])


def test_converted_doc_validates_with_v1_ledger():
    assert validate.validate_document(migrate.migrate_to_current(load_v1(), RUN), fixture_sources()) == []


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
    assert validate.validate_document(migrate.migrate_to_current(old, RUN), fixture_sources()) == []


def test_unnamed_product_strategy_name():
    old = load_v1()
    old["project"]["products"][1]["name"] = {"value": None, "status": "not_found", "evidence": [], "subject": None,
                                             "note": ""}
    assert migrate.convert(old, RUN)["strategies"][1]["name"] == "Strategy for P2"


# --------------------------------------------------------------------------- v0.6.0 rwa-dd/2.0 -> 2.1

# Fixed run block of tests/golden/acme_v2.migrated.json.
RUN_21 = {"run_id": "acme-20261101T000000Z", "slug": "acme", "root_url": "https://acme-yield.example/", "round": 1,
          "status": "draft", "started_at": "2026-11-01T00:00:00Z", "finalized_at": None, "skill_version": "0.6.0",
          "seeded_from": "acme-20261001T080000Z"}


def load_v2():
    return json.loads((FIXTURES / "acme_v2.dd.json").read_bytes().decode("utf-8"))


def test_v2_fixture_is_still_2_0():
    assert load_v2()["schema_version"] == "rwa-dd/2.0"


def test_convert_20_matches_golden():
    expected = (GOLDEN / "acme_v2.migrated.json").read_bytes().decode("utf-8")
    assert dump_json(migrate.convert_20(load_v2(), RUN_21)) == expected


def test_convert_20_validates_with_same_ledger():
    assert validate.validate_document(migrate.convert_20(load_v2(), RUN_21), fixture_sources()) == []


def test_convert_20_does_not_mutate_input():
    old = load_v2()
    before = copy.deepcopy(old)
    migrate.convert_20(old, RUN_21)
    assert old == before


def test_convert_20_ultimate_obligor_and_within_l3():
    old = load_v2()
    doc = migrate.convert_20(old, RUN_21)
    functions = {e["id"]: e["functions"] for e in doc["entities"]}
    assert {"layer": "L3-O", "role": "cash_flow_source", "strategy": "T1", "evidence": ["S8"]} in functions["E10"]
    assert functions["E9"] == [{"layer": "L3-O", "role": "cash_flow_source", "strategy": "T2", "evidence": ["S7"]}]
    assert not any(fn["role"] == "ultimate_obligor" for fns in functions.values() for fn in fns)
    assert {e["entity_class"] for e in doc["entities"]} == {"unknown"}
    x8 = doc["interfaces"][7]
    assert (old["interfaces"][7]["kind"], x8["kind"]) == ("within_L3", "L3_L3O")
    assert [x["kind"] for x in doc["interfaces"]] == [x["kind"] for x in old["interfaces"][:7]] + ["L3_L3O"]


def test_convert_20_within_l3_without_obligor_kept():
    old = load_v2()
    old["entities"][9]["functions"][0]["role"] = "financing_recipient"
    assert migrate.convert_20(old, RUN_21)["interfaces"][7]["kind"] == "within_L3"
    old = load_v2()
    old["entities"][9]["functions"][0]["strategy"] = None  # an obligor for every strategy
    assert migrate.convert_20(old, RUN_21)["interfaces"][7]["kind"] == "L3_L3O"


def test_convert_20_placeholders():
    doc = migrate.convert_20(load_v2(), RUN_21)
    assert doc["schema_version"] == "rwa-dd/2.1" and doc["run"] == RUN_21
    assert doc["next_searches"] == [] and doc["supports"] == []
    assert {t["component"] for t in doc["strategies"]} == {"CORE_CREDIT"}
    for x in doc["interfaces"]:
        assert x["alternative"] == {"group": None, "option": None} and x["amount_basis"] is None
        for field in migrate.NEW_INTERFACE_CLAIMS:
            assert x[field] == schema.empty_claim()
    notes = {f["id"]: (f["material"], f["scope_note"]) for f in doc["findings"]}
    assert notes == {"G1": (False, ""), "G2": (False, ""), "G3": (False, ""),
                     "D1": (False, schema.MIGRATED_SCOPE_NOTE), "D2": (False, schema.MIGRATED_SCOPE_NOTE),
                     "C1": (False, "")}
    old = load_v2()
    assert [(f["id"], f["statement"]) for f in doc["findings"]] == [(f["id"], f["statement"]) for f in old["findings"]]
    assert [c["status"] for _, c in schema.iter_claims(doc) if c["status"] != "not_found"] == \
        [c["status"] for _, c in schema.iter_claims(dict(old, supports=[])) if c["status"] != "not_found"]


def test_migrate_to_current_dispatch():
    v1 = migrate.migrate_to_current(load_v1(), RUN_21)
    assert v1["schema_version"] == "rwa-dd/2.1" and v1["run"] == RUN_21
    assert v1 == migrate.convert_20(migrate.convert(load_v1(), RUN_21), RUN_21)
    assert validate.validate_document(v1, fixture_sources()) == []
    assert migrate.migrate_to_current(load_v2(), RUN_21) == migrate.convert_20(load_v2(), RUN_21)
    current = load_fixture()
    copied = migrate.migrate_to_current(current, RUN_21)
    assert copied["run"] == RUN_21 and copied["next_searches"] == [] and current["next_searches"]
    assert {k: v for k, v in copied.items() if k not in ("run", "next_searches")} == \
        {k: v for k, v in current.items() if k not in ("run", "next_searches")}
    with pytest.raises(ValueError):
        migrate.migrate_to_current(dict(current, schema_version="rwa-dd/0.9"), RUN_21)
