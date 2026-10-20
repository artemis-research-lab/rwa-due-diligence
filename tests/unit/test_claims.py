"""Test group 2: one negative test per claim rule."""

import copy

from test_support import claim, load_fixture
from lib import claims, validate


def errors_for(mutate):
    doc = copy.deepcopy(load_fixture())
    mutate(doc)
    return validate.validate_document(doc)


def test_fixture_claims_are_valid():
    assert claims.check_all(load_fixture()) == []


def test_verified_without_independent():
    def m(doc):
        doc["project"]["products"][0]["symbol"] = claim("aSN", "verified", ["S1"], "P1")
    assert errors_for(m) == ["project.products[0].symbol: verified requires an independent source"]


def test_legal_verified_by_third_party():
    def m(doc):
        doc["entities"][2]["jurisdiction"] = claim("Examplestan", "verified", ["S5"], "E3")
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
        doc["entities"][2]["jurisdiction"] = claim("Examplestan", "third_party_reported", evidence, "E3")
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


# --------------------------------------------------------------------------- v0.7.0 provenance (curator Q8)

def _x2_funded(doc):
    """X2.amounts[2].value: an issuer statement quoted in the S9 auditor report (self_reported, NOT_TESTED)."""
    return doc["interfaces"][1]["amounts"][2]["value"]


def _performance(doc):
    """T1.l3_business.performance: verified by an auditor procedure (TESTED)."""
    return doc["strategies"][0]["l3_business"]["performance"]


def test_fixture_q8_claims():
    doc = load_fixture()
    assert doc["sources"][8]["origin"] == "auditor"
    funded = _x2_funded(doc)
    assert (funded["status"], funded["evidence"], funded["origin"], funded["assurance"]) == \
        ("self_reported", ["S9"], "issuer_management", "NOT_TESTED")
    perf = _performance(doc)
    assert (perf["status"], perf["evidence"], perf["origin"], perf["assurance"]) == \
        ("verified", ["S9"], "auditor_procedure", "TESTED")


def test_issuer_origin_quoted_by_auditor_is_self_reported():
    path = "interfaces[1].amounts[2].value"

    def third_party(doc):
        _x2_funded(doc)["status"] = "third_party_reported"
    assert errors_for(third_party) == [
        path + ": auditor source: state origin (issuer statement -> self_reported; tested -> auditor_procedure)",
        path + ": origin issuer_management is an issuer assertion; status must be self_reported (curator Q8)"]

    def verified(doc):
        _x2_funded(doc)["status"] = "verified"
    assert errors_for(verified) == [
        path + ": origin issuer_management is an issuer assertion; status must be self_reported (curator Q8)",
        path + ": verified citing an auditor source requires origin auditor_procedure, regulator, registry or "
               "onchain (curator Q8)",
        path + ": verified requires a regulator/registry/auditor/onchain source for legal fields"]

    def no_origin(doc):
        _x2_funded(doc)["origin"] = None
    assert errors_for(no_origin) == [
        path + ": self_reported requires a first-party or subject-published source"]


def test_auditor_procedure_rules():
    path = "strategies[0].l3_business.performance"

    def no_assurance(doc):
        _performance(doc)["assurance"] = None
    assert errors_for(no_assurance) == [path + ": origin auditor_procedure requires assurance TESTED or NOT_TESTED"]

    def not_tested(doc):
        _performance(doc)["assurance"] = "NOT_TESTED"
    assert errors_for(not_tested) == [
        path + ": origin auditor_procedure with assurance NOT_TESTED requires status third_party_reported"]

    def without_auditor(doc):
        _performance(doc)["evidence"] = ["S4"]
    assert errors_for(without_auditor) == [path + ": assurance requires an auditor source (curator Q8)",
                                           path + ": origin auditor_procedure requires an auditor source"]

    def other_origin(doc):
        _performance(doc)["origin"] = "independent_party"
    assert errors_for(other_origin) == [
        path + ": verified citing an auditor source requires origin auditor_procedure, regulator, registry or "
               "onchain (curator Q8)"]


def test_legal_verified_through_auditor_needs_tested():
    def tested(doc):
        doc["entities"][2]["jurisdiction"] = claim("Examplestan", "verified", ["S9"], "E3",
                                                   origin="auditor_procedure", assurance="TESTED")
    assert errors_for(tested) == []

    def untested(doc):
        tested(doc)
        doc["entities"][2]["jurisdiction"]["assurance"] = "NOT_TESTED"
    assert errors_for(untested) == [
        "entities[2].jurisdiction: origin auditor_procedure with assurance NOT_TESTED requires status "
        "third_party_reported",
        "entities[2].jurisdiction: verified requires a regulator/registry/auditor/onchain source for legal fields"]


def test_third_party_reported_through_auditor_needs_origin():
    def m(origin):
        def mutate(doc):
            doc["entities"][2]["jurisdiction"] = claim("Examplestan", "third_party_reported", ["S9"], "E3",
                                                       origin=origin)
        return mutate
    assert errors_for(m("independent_party")) == []
    assert errors_for(m("auditor_procedure")) == [
        "entities[2].jurisdiction: origin auditor_procedure requires assurance TESTED or NOT_TESTED"]
    assert errors_for(m(None)) == []  # origin unstated: lint warning and QA7 failure, not an error
    assert errors_for(m("borrower")) == [
        "entities[2].jurisdiction: auditor source: state origin (issuer statement -> self_reported; tested -> "
        "auditor_procedure)",
        "entities[2].jurisdiction: origin borrower is an issuer assertion; status must be self_reported (curator Q8)"]
    assert errors_for(_third_party(["S5", "S9"])) == []  # not auditor-only


def test_analyst_origin_and_assurance_source():
    def analyst(doc):
        doc["project"]["products"][0]["symbol"]["origin"] = "analyst"
    assert errors_for(analyst) == ["project.products[0].symbol: origin analyst allows only inferred or not_found"]

    def analyst_inferred(doc):
        doc["entities"][1]["jurisdiction"]["origin"] = "analyst"
    assert errors_for(analyst_inferred) == []

    def assurance_self(doc):
        doc["holder_rights"][0]["governing_law"]["assurance"] = "TESTED"
    assert errors_for(assurance_self) == [
        "holder_rights[0].governing_law: assurance requires an auditor source (curator Q8)"]

    def assurance_independent(doc):
        doc["holder_rights"][0]["governing_law"].update({"evidence": ["S8", "S5"], "assurance": "NOT_APPLICABLE"})
    assert errors_for(assurance_independent) == [
        "holder_rights[0].governing_law: assurance requires an auditor source (curator Q8)"]


def test_not_found_requires_null_origin_and_assurance():
    def origin(doc):
        doc["entities"][3]["jurisdiction"]["origin"] = "issuer_documents"
    assert errors_for(origin) == ["entities[3].jurisdiction: not_found requires null origin and assurance"]

    def assurance(doc):
        doc["entities"][3]["jurisdiction"]["assurance"] = "NOT_TESTED"
    assert "entities[3].jurisdiction: not_found requires null origin and assurance" in errors_for(assurance)


def test_issuer_origin_on_first_party_claim():
    def borrower(doc):
        doc["holder_rights"][0]["governing_law"]["origin"] = "borrower"
    assert errors_for(borrower) == []

    def inferred(doc):
        doc["entities"][1]["jurisdiction"]["origin"] = "issuer_documents"
    assert errors_for(inferred) == [
        "entities[1].jurisdiction: inferred is the analyst's conclusion; origin must be analyst or null",
        "entities[1].jurisdiction: origin issuer_documents is an issuer assertion; status must be self_reported "
        "(curator Q8)"]


def test_origin_and_assurance_enums():
    def m(doc):
        doc["holder_rights"][0]["governing_law"].update({"origin": "issuer", "assurance": "tested"})
    assert errors_for(m) == ["holder_rights[0].governing_law.assurance: not a valid assurance_scope",
                             "holder_rights[0].governing_law.origin: not a valid assertion_origin"]


# --------------------------------------------------------------------------- D77 Q8 gating

def test_verified_auditor_source_with_null_origin_is_unstated():
    from lib import lint, qa

    def m(doc):
        doc["entities"][2]["jurisdiction"] = claim("Examplestan", "verified", ["S9"], "E3")
    assert errors_for(m) == []  # valid: the auditor source counts for the legal rule
    doc = load_fixture()
    m(doc)
    assert lint.provenance_warnings(doc) == [{
        "path": "entities[2].jurisdiction",
        "message": "E3.jurisdiction: cites an auditor source; set origin and assurance (curator Q8)"}]
    assert {r["id"]: r for r in qa.run(doc)}["QA7"]["detail"] == "E3.jurisdiction"


def test_verified_auditor_source_with_issuer_origin_fails():
    def m(doc):
        doc["entities"][2]["jurisdiction"] = claim("Examplestan", "verified", ["S9"], "E3",
                                                   origin="issuer_management")
    assert errors_for(m) == [
        "entities[2].jurisdiction: origin issuer_management is an issuer assertion; status must be self_reported "
        "(curator Q8)",
        "entities[2].jurisdiction: verified citing an auditor source requires origin auditor_procedure, regulator, "
        "registry or onchain (curator Q8)",
        "entities[2].jurisdiction: verified requires a regulator/registry/auditor/onchain source for legal fields"]


def test_audit_claims_are_exempt_from_q8():
    from lib import lint, qa
    doc = load_fixture()
    doc["audits"][0]["scope"] = claim("Loan sample procedures", "verified", ["S9"])
    assert validate.validate_document(doc) == []
    assert lint.provenance_warnings(doc) == []
    assert {r["id"]: r for r in qa.run(doc)}["QA7"]["result"] == "pass"
    doc["audits"][0]["scope"]["origin"] = "issuer_management"
    assert validate.validate_document(doc) == [
        "audits[0].scope: origin issuer_management is an issuer assertion; status must be self_reported (curator Q8)"]


# --------------------------------------------------------------------------- v0.7.1 provenance combinations P1-P5

JURISDICTION = "entities[2].jurisdiction"


def _jurisdiction(status, evidence, origin=None, assurance=None):
    def mutate(doc):
        doc["entities"][2]["jurisdiction"] = claim("Examplestan", status, evidence, "E3", origin=origin,
                                                   assurance=assurance)
    return mutate


def _inferred(origin, assurance=None):
    """entities[1].jurisdiction (inferred) citing the S9 auditor source."""
    def mutate(doc):
        doc["entities"][1]["jurisdiction"].update({"origin": origin, "evidence": ["S1", "S9"], "assurance": assurance})
    return mutate


def test_p1_assurance_needs_an_auditor_source():
    assert errors_for(_jurisdiction("third_party_reported", ["S5", "S9"], "independent_party", "NOT_TESTED")) == []
    assert errors_for(_jurisdiction("third_party_reported", ["S5"], "independent_party", "NOT_TESTED")) == [
        JURISDICTION + ": assurance requires an auditor source (curator Q8)"]


def test_p2_analyst_origin_carries_no_assurance():
    assert errors_for(_inferred("analyst")) == []
    assert errors_for(_inferred("analyst", "NOT_TESTED")) == [
        "entities[1].jurisdiction: origin analyst cannot carry assurance"]


def test_p3_inferred_origin_is_analyst_or_null():
    assert errors_for(_inferred(None)) == []
    assert errors_for(_inferred("auditor_procedure", "TESTED")) == [
        "entities[1].jurisdiction: inferred is the analyst's conclusion; origin must be analyst or null",
        "entities[1].jurisdiction: origin auditor_procedure with assurance TESTED requires status verified"]


def test_p4_auditor_procedure_assurance_sets_status():
    assert errors_for(_jurisdiction("third_party_reported", ["S9"], "auditor_procedure", "NOT_TESTED")) == []
    assert errors_for(_jurisdiction("verified", ["S9"], "auditor_procedure", "TESTED")) == []
    assert errors_for(_jurisdiction("third_party_reported", ["S9"], "auditor_procedure", "TESTED")) == [
        JURISDICTION + ": origin auditor_procedure with assurance TESTED requires status verified"]


def test_p5_verified_citing_an_auditor_source():
    assert errors_for(_jurisdiction("verified", ["S2", "S9"], "regulator", "NOT_TESTED")) == []
    assert errors_for(_jurisdiction("verified", ["S3", "S9"], "registry", "TESTED")) == []
    assert errors_for(_jurisdiction("verified", ["S3", "S9"], "regulator", "TESTED")) == [
        JURISDICTION + ": verified with origin regulator needs a regulator source in evidence"]
    assert errors_for(_jurisdiction("verified", ["S2", "S9"], "regulator", "NOT_APPLICABLE")) == [
        JURISDICTION + ": verified citing an auditor source needs assurance TESTED or NOT_TESTED"]
    assert errors_for(_jurisdiction("verified", ["S2", "S9"], "independent_party", "TESTED")) == [
        JURISDICTION + ": verified citing an auditor source requires origin auditor_procedure, regulator, registry "
                       "or onchain (curator Q8)"]


def test_onchain_verified_claim_citing_an_auditor_source():
    def amount(assurance):
        def mutate(doc):
            doc["interfaces"][1]["amounts"][0]["value"].update({"evidence": ["S4", "S9"], "origin": "onchain",
                                                                "assurance": assurance})
        return mutate
    assert load_fixture()["interfaces"][1]["amounts"][0]["value"]["status"] == "verified"
    assert errors_for(amount("NOT_TESTED")) == []
    assert errors_for(amount(None)) == [
        "interfaces[1].amounts[0].value: verified citing an auditor source needs assurance TESTED or NOT_TESTED"]


def test_audit_claim_with_independent_source_is_exempt_from_p1():
    def m(doc):
        doc["audits"][0]["scope"] = claim("Loan sample procedures", "third_party_reported", ["S5"],
                                          assurance="NOT_APPLICABLE")
    assert errors_for(m) == []
