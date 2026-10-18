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
        doc["governing_law"]["evidence"] = ["S5"]
    assert errors_for(m) == ["governing_law: self_reported requires a first-party or subject-published source"]


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
        doc["governing_law"].update({"subject": "E9", "evidence": ["S8", "S99"]})
    assert errors_for(m) == ["governing_law.evidence: unknown source S99", "governing_law.subject: unknown id E9"]


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
        doc["relationships"][0]["claim"]["value"] = None
    assert errors_for(m) == ["relationships[0].claim: inferred requires a non-null value"]

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
