"""Test group 2: one negative test per claim rule."""

import copy

from test_support import load_fixture
from lib import claims, validate


def errors_for(mutate):
    doc = copy.deepcopy(load_fixture())
    mutate(doc)
    return validate.validate_document(doc)


def test_fixture_claims_are_valid():
    assert claims.check_all(load_fixture()) == []


def test_verified_without_independent():
    def m(doc):
        doc["project"]["products"][0]["symbol"] = {"value": "aSN", "status": "verified", "evidence": ["S1"],
                                                   "subject": "P1", "note": ""}
    assert errors_for(m) == ["project.products[0].symbol: verified requires an independent source"]


def test_legal_verified_by_third_party():
    def m(doc):
        doc["entities"][2]["jurisdiction"] = {"value": "Examplestan", "status": "verified", "evidence": ["S5"],
                                              "subject": "E3", "note": ""}
    assert errors_for(m) == ["entities[2].jurisdiction: verified requires a regulator/registry/auditor/onchain "
                             "source for legal fields"]


def test_self_reported_without_self():
    def m(doc):
        doc["holder_rights"][0]["governing_law"]["evidence"] = ["S5"]
    assert errors_for(m) == ["holder_rights[0].governing_law: self_reported requires a first-party or "
                             "subject-published source"]


def test_interface_and_holder_rights_are_legal_paths():
    def m(doc):
        doc["interfaces"][3]["collateral"].update({"status": "verified", "evidence": ["S5"]})
        doc["holder_rights"][0]["recourse"].update({"status": "verified", "evidence": ["S4"]})
    assert errors_for(m) == ["interfaces[3].collateral: verified requires a regulator/registry/auditor/onchain "
                             "source for legal fields"]


def test_publisher_equal_to_subject_makes_it_self():
    # S3 is a registry source; with publisher == subject it is self, not independent.
    doc = load_fixture()
    s3 = dict(doc["sources"][2], publisher="E1")
    claim = doc["entities"][0]["jurisdiction"]
    assert claims.evidence_role(s3, claim) == "self"
    assert claims.evidence_role(doc["sources"][2], claim) == "independent:registry"

    def m(d):
        d["sources"][2]["publisher"] = "E1"
    errs = errors_for(m)
    assert "entities[0].jurisdiction: verified requires a regulator/registry/auditor/onchain source for legal fields" \
        in errs


def test_inferred_without_note():
    def m(doc):
        doc["entities"][1]["jurisdiction"]["note"] = ""
    assert errors_for(m) == ["entities[1].jurisdiction: inferred requires a note"]


def test_inferred_without_evidence():
    def m(doc):
        doc["entities"][1]["jurisdiction"]["evidence"] = []
    assert errors_for(m) == ["entities[1].jurisdiction: inferred requires at least one evidence"]


def test_not_found_with_value():
    def m(doc):
        doc["entities"][3]["jurisdiction"]["value"] = "Examplestan"
    assert errors_for(m) == ["entities[3].jurisdiction: not_found requires a null value"]


def test_not_found_with_evidence_without_note():
    def m(doc):
        doc["entities"][2]["jurisdiction"]["note"] = ""
    assert errors_for(m) == ["entities[2].jurisdiction: not_found with evidence requires a note"]


def test_analyst_cannot_verify():
    def m(doc):
        doc["redemption"][0]["settlement_time"].update({"status": "verified", "note": ""})
    assert errors_for(m) == ["redemption[0].settlement_time: verified must not cite an analyst source",
                             "redemption[0].settlement_time: verified requires an independent source"]
    assert claims.evidence_role(load_fixture()["sources"][5], {"subject": None}) == "analyst"


def test_unknown_subject_and_evidence():
    def m(doc):
        doc["holder_rights"][0]["governing_law"].update({"subject": "E19", "evidence": ["S8", "S99"]})
    assert errors_for(m) == ["holder_rights[0].governing_law.evidence: unknown source S99",
                             "holder_rights[0].governing_law.subject: unknown id E19"]


# --------------------------------------------------------------------------- C2: non-not_found claims need a value

def test_verified_requires_value():
    def m(doc):
        doc["project"]["products"][0]["symbol"]["value"] = None
    assert errors_for(m) == ["project.products[0].symbol: verified requires a non-null value"]


def test_self_reported_requires_value():
    def m(doc):
        doc["project"]["name"]["value"] = None
    assert errors_for(m) == ["project.name: self_reported requires a non-null value"]


def test_inferred_requires_value():
    def m(doc):
        doc["strategies"][0]["l3_business"]["collections_control"]["value"] = None
    assert errors_for(m) == ["strategies[0].l3_business.collections_control: inferred requires a non-null value"]

def test_verified_must_not_cite_analyst():
    def both(doc):
        doc["redemption"][0]["settlement_time"].update({"status": "verified", "evidence": ["S4", "S6"], "note": ""})
    assert errors_for(both) == ["redemption[0].settlement_time: verified must not cite an analyst source"]

    def onchain_only(doc):
        doc["redemption"][0]["settlement_time"].update({"status": "verified", "evidence": ["S4"], "note": ""})
    assert errors_for(onchain_only) == []

    def inferred(doc):
        doc["redemption"][0]["settlement_time"].update({"status": "inferred", "evidence": ["S4", "S6"]})
    assert errors_for(inferred) == []


# --------------------------------------------------------------------------- v0.6.0 third_party_reported

def _third_party(evidence):
    def m(doc):
        doc["entities"][2]["jurisdiction"] = {"value": "Examplestan", "status": "third_party_reported",
                                              "evidence": evidence, "subject": "E3", "note": ""}
    return m


def test_third_party_reported_passes_with_s5_on_a_legal_path():
    assert errors_for(_third_party(["S5"])) == []
    assert load_fixture()["strategies"][0]["l3_business"]["concentration"]["status"] == "third_party_reported"


def test_third_party_reported_fails_with_first_party_or_analyst_only():
    message = "entities[2].jurisdiction: third_party_reported requires an independent source"
    assert errors_for(_third_party(["S8"])) == [message]
    assert errors_for(_third_party(["S6"])) == [message]
    assert errors_for(_third_party(["S1", "S6"])) == [message]


def test_third_party_reported_requires_value():
    def m(doc):
        _third_party(["S5"])(doc)
        doc["entities"][2]["jurisdiction"]["value"] = None
    assert errors_for(m) == ["entities[2].jurisdiction: third_party_reported requires a non-null value"]
