"""v0.5.0 migration rwa-dd/1.0 -> 2.0, v0.6.0 migration 2.0 -> 2.1 and v0.7.0 migration 2.1 -> 2.2
(lib/migrate.py)."""

import copy
import json

import pytest

from test_support import FIXTURES, GOLDEN, fixture_sources, load_fixture, load_v1, load_v21
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
    assert validate.validate_document(migrate.migrate_to_current(load_v1(), RUN), fixture_sources()[:8]) == []


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
    assert validate.validate_document(migrate.migrate_to_current(old, RUN), fixture_sources()[:8]) == []


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
    # convert_20 emits rwa-dd/2.1; it validates once carried on to the current schema.
    assert validate.validate_document(migrate.convert_21(migrate.convert_20(load_v2(), RUN_21), RUN_22),
                                      fixture_sources()[:8]) == []


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
            assert x[field] == {"value": None, "status": "not_found", "evidence": [], "subject": None, "note": ""}
    notes = {f["id"]: (f["material"], f["scope_note"]) for f in doc["findings"]}
    assert notes == {"G1": (False, ""), "G2": (False, ""), "G3": (False, ""),
                     "D1": (False, schema.MIGRATED_SCOPE_NOTE), "D2": (False, schema.MIGRATED_SCOPE_NOTE),
                     "C1": (False, "")}
    old = load_v2()
    assert [(f["id"], f["statement"]) for f in doc["findings"]] == [(f["id"], f["statement"]) for f in old["findings"]]
    assert [c["status"] for _, c in schema.iter_claims(doc) if c["status"] != "not_found"] == \
        [c["status"] for _, c in schema.iter_claims(dict(old, supports=[])) if c["status"] != "not_found"]


# --------------------------------------------------------------------------- v0.7.0 rwa-dd/2.1 -> 2.2

# Fixed run block of tests/golden/acme_v21.migrated.json.
RUN_22 = {"run_id": "acme-20261101T000000Z", "slug": "acme", "root_url": "https://acme-yield.example/", "round": 1,
          "status": "draft", "started_at": "2026-11-01T00:00:00Z", "finalized_at": None, "skill_version": "0.7.0",
          "seeded_from": "acme-20261001T080000Z"}


def v21_sources():
    """The ledger of the 2.1 fixture: the shared ledger without S9."""
    return fixture_sources()[:8]


def test_v21_fixture_is_still_2_1():
    assert load_v21()["schema_version"] == "rwa-dd/2.1"


def test_convert_21_matches_golden():
    expected = (GOLDEN / "acme_v21.migrated.json").read_bytes().decode("utf-8")
    assert dump_json(migrate.convert_21(load_v21(), RUN_22)) == expected


def test_convert_21_validates_and_does_not_mutate():
    old = load_v21()
    before = copy.deepcopy(old)
    doc = migrate.convert_21(old, RUN_22)
    assert old == before
    assert validate.validate_document(doc, v21_sources()) == []
    assert doc["schema_version"] == "rwa-dd/2.2" and doc["run"] == RUN_22 and doc["next_searches"] == []


def _x(doc, xid):
    return next(x for x in doc["interfaces"] if x["id"] == xid)


def test_convert_21_amounts():
    doc = migrate.convert_21(load_v21(), RUN_22)
    x2 = _x(doc, "X2")
    assert "amount" not in x2 and "amount_basis" not in x2
    assert x2["amounts"] == [{
        "basis": "OTHER", "value": {"value": 25000000, "status": "self_reported", "evidence": ["S8"], "subject": "E5",
                                    "note": "2.1 basis GROSS_FUNDED", "origin": None, "assurance": None},
        "unit": "n/d", "as_of": None, "block": None, "chain": None, "scope": schema.MIGRATED_AMOUNT_SCOPE,
        "valuation_basis": None}]
    bases = {x["id"]: [(a["basis"], a["unit"]) for a in x["amounts"]] for x in doc["interfaces"]}
    assert bases == {"X1": [], "X2": [("OTHER", "n/d")], "X3": [], "X4": [("FACILITY_COMMITMENT", "USD")], "X5": [],
                     "X6": [], "X7": [], "X8": [], "X9": [("OTHER", "USD")], "X10": [("RESERVE_LOOKTHROUGH", "USD")],
                     "X11": [("OTHER", "n/d")], "X12": [], "X13": [("SALE_PROCEEDS", "USD")]}
    assert _x(doc, "X10")["amounts"][0]["value"]["note"] == "2.1 basis LOOKTHROUGH"


def test_convert_21_basis_map_and_units():
    assert migrate.BASIS_MAP == {"GROSS_FUNDED": "OTHER", "COMMITMENT": "FACILITY_COMMITMENT",
                                 "LOOKTHROUGH": "RESERVE_LOOKTHROUGH", "RESERVE": "RESERVE_LOOKTHROUGH",
                                 "SALE_PROCEEDS": "SALE_PROCEEDS", None: "OTHER"}
    old = load_v21()
    x9 = _x(old, "X9")
    x9["amount_basis"] = "RESERVE"
    x9["amount"]["note"] = "Treasury sleeve balance."
    x9["currency"]["value"] = "PYUSD (USD-denominated stablecoin)"
    entry = _x(migrate.convert_21(old, RUN_22), "X9")["amounts"][0]
    assert (entry["basis"], entry["unit"], entry["value"]["note"]) == \
        ("RESERVE_LOOKTHROUGH", "n/d", "Treasury sleeve balance.")


def test_convert_21_supply_concentration_and_sale_fields():
    old = load_v21()
    _x(old, "X2")["supply_concentration"] = {"value": "E1 holds 60 percent of pool supply", "status": "verified",
                                             "evidence": ["S4"], "subject": None, "note": ""}
    doc = migrate.convert_21(old, RUN_22)
    assert _x(doc, "X2")["supply_concentration"] == {
        "ratio": {"value": None, "status": "not_found", "evidence": ["S4"], "subject": None,
                  "note": "migrated: E1 holds 60 percent of pool supply", "origin": None, "assurance": None},
        "numerator": "", "denominator": "", "as_of": None, "block": None, "chain": None}
    assert _x(doc, "X4")["supply_concentration"]["ratio"] == schema.empty_claim()
    for field in migrate.SALE_CLAIMS_22:
        assert all(x[field] == schema.empty_claim() for x in doc["interfaces"])
    assert validate.validate_document(doc, v21_sources()) == []


def test_convert_21_claims_and_strategies():
    doc = migrate.convert_21(load_v21(), RUN_22)
    assert all(list(c) == list(schema.CLAIM_KEYS) and c["origin"] is None and c["assurance"] is None
               for _, c in schema.iter_claims(doc))
    assert all(t["deployment"] == schema.empty_claim() for t in doc["strategies"])
    assert list(doc["strategies"][0])[:6] == ["id", "products", "name", "component", "business_type", "deployment"]


def test_convert_21_findings():
    old = load_v21()
    doc = migrate.convert_21(old, RUN_22)
    got = {f["id"]: (f["scope_match"], f["scope_note"], f["resolution"], f["carried_from"]) for f in doc["findings"]}
    note = schema.MIGRATED_NOTE_21
    assert got == {
        "G1": ("not_applicable", "", {"status": "open", "note": ""}, "G1"),
        "G2": ("not_applicable", "", {"status": "open", "note": ""}, "G2"),
        "G3": ("not_applicable", "", {"status": "open", "note": ""}, "G3"),
        "D1": ("unchecked", note + " -- " + old["findings"][3]["scope_note"], {"status": "open", "note": ""}, "D1"),
        "D2": ("unchecked", note + " -- " + old["findings"][4]["scope_note"], {"status": "open", "note": ""}, "D2"),
        "C1": ("not_applicable", "", {"status": "not_applicable", "note": ""}, "C1"),
        "U1": ("unchecked", note, {"status": "open", "note": ""}, "U1")}
    assert all((f["assertions"], f["k_checks"], f["impact"], f["priority"]) == ([], [], [], 2) for f in doc["findings"])
    old["findings"][3]["scope_note"] = "x" * 200
    assert len(migrate.convert_21(old, RUN_22)["findings"][3]["scope_note"]) == 200


def test_convert_21_renames_amount_subjects():
    old = load_v21()
    old["findings"][0]["subjects"] = ["X2.amount", "X1.amount", "X2.supply_concentration", "X4.security", "E1"]
    doc = migrate.convert_21(old, RUN_22)
    assert doc["findings"][0]["subjects"] == ["X2.amounts[0].value", "X1", "X2.supply_concentration.ratio",
                                              "X4.security", "E1"]
    assert validate.validate_document(doc, v21_sources()) == []


def test_convert_21_from_2_0_placeholder_note():
    doc = migrate.migrate_to_current(load_v2(), RUN_22)
    notes = {f["id"]: f["scope_note"] for f in doc["findings"] if f["type"] == "discrepancy"}
    assert notes == {"D1": schema.MIGRATED_NOTE_21, "D2": schema.MIGRATED_NOTE_21}


def test_migrate_to_current_dispatch():
    v1 = migrate.migrate_to_current(load_v1(), RUN_22)
    assert v1["schema_version"] == "rwa-dd/2.2" and v1["run"] == RUN_22
    assert v1 == migrate.convert_21(migrate.convert_20(migrate.convert(load_v1(), RUN_22), RUN_22), RUN_22)
    assert validate.validate_document(v1, fixture_sources()[:8]) == []
    v2 = migrate.migrate_to_current(load_v2(), RUN_22)
    assert v2 == migrate.convert_21(migrate.convert_20(load_v2(), RUN_22), RUN_22)
    assert validate.validate_document(v2, fixture_sources()[:8]) == []
    assert migrate.migrate_to_current(load_v21(), RUN_22) == migrate.convert_21(load_v21(), RUN_22)
    current = load_fixture()
    copied = migrate.migrate_to_current(current, RUN_22)
    assert copied["run"] == RUN_22 and copied["next_searches"] == [] and current["next_searches"]
    assert {k: v for k, v in copied.items() if k not in ("run", "next_searches")} == \
        {k: v for k, v in current.items() if k not in ("run", "next_searches")}
    assert migrate.SEEDABLE == ("rwa-dd/1.0", "rwa-dd/2.0", "rwa-dd/2.1", "rwa-dd/2.2")
    with pytest.raises(ValueError):
        migrate.migrate_to_current(dict(current, schema_version="rwa-dd/0.9"), RUN_22)
