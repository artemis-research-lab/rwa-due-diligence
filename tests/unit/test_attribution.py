"""v0.7.4: regulatory filing attribution (curator AC-05): rules A1-A6 and V1, verification basis, QA14, ledger
corrections (dd.py correct-source), change rows and amendment_changes."""

import copy
import json

import pytest

from test_support import FIXTURES, build_run, claim, clock_at, clock_from_ts, load_fixture, run_cli
from lib import changes, claims, flow, framework, ledger, qa, render_md, runstate, schema, validate
from lib.textutil import dump_json_line

NEEDS_D2 = pytest.mark.skipif(flow.find_d2() is None, reason="d2 %s not on PATH" % flow.D2_VERSION)
CASES = json.loads((FIXTURES / "ac05" / "cases.json").read_bytes().decode("utf-8"))
REASON = "Form 10-Q is the filer's own document; the regulator only hosts it."


def _set(doc, parts, value):
    node = doc
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value


def _case_doc(tmp_path, case):
    """(document, folded ledger) of one case: acme plus the case's ledger lines and claim replacements."""
    path = tmp_path / "sources.jsonl"
    tail = "".join(dump_json_line(line) for line in case["ledger_tail"]).encode("utf-8")
    path.write_bytes((FIXTURES / "acme.sources.jsonl").read_bytes() + tail)
    sources = ledger.read_ledger(path)
    doc = load_fixture()
    doc["sources"] = copy.deepcopy(sources)
    for change in case["set"]:
        _set(doc, change["path"], change["claim"])
    return doc, sources


def _qa14(doc):
    return {r["id"]: r for r in qa.run(doc)}["QA14"]


# --------------------------------------------------------------------------- fixture cases

def test_cases_cover_the_spec():
    kinds = [(c["kind"], c["rule"]) for c in CASES]
    assert {r for k, r in kinds if k == "negative"} == {"A1", "A2", "A3", "A4", "A6", "V1"}
    assert sum(1 for k, _ in kinds if k == "positive") >= 7
    assert len({c["id"] for c in CASES}) == len(CASES)


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case_gives_exactly_the_expected_errors(tmp_path, case):
    doc, sources = _case_doc(tmp_path, case)
    assert validate.validate_document(doc, sources) == case["errors"]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case_qa14(tmp_path, case):
    doc, _ = _case_doc(tmp_path, case)
    result = _qa14(doc)
    assert result["result"] == ("fail" if case["kind"] == "negative" else "pass")
    assert result["detail"] == case["qa14"]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case_verification_basis(tmp_path, case):
    doc, _ = _case_doc(tmp_path, case)
    bases = render_md.verification_bases(doc)
    for cid, expected in case["basis"].items():
        assert bases[cid] == expected


def test_fixture_passes_qa14_and_every_verified_claim_has_a_basis():
    doc = load_fixture()
    assert _qa14(doc) == {"id": "QA14", "rule": "attribution", "result": "pass", "detail": "ok", "target": None,
                          "legacy": None, "mapping": ""}
    bases = render_md.verification_bases(doc)
    verified = [framework.claim_id(p, doc) for p, c in schema.iter_claims(doc) if c["status"] == "verified"]
    assert sorted(bases) == sorted(verified) and all(bases.values())
    assert bases["T1.l3_business.performance"] == ["S9"] and bases["E2.license_status"] == ["S2"]


# --------------------------------------------------------------------------- verification basis

def _sources(doc, *extra):
    by_id = {s["id"]: s for s in doc["sources"]}
    by_id.update({s["id"]: s for s in extra})
    return by_id


FILER = {"id": "S10", "origin": "filer", "source_type": "regulator_filing", "publisher": None}


def test_basis_excludes_filer_first_party_analyst_and_subject_publisher():
    doc = load_fixture()
    by_id = _sources(doc, FILER)
    legal = ("entities", 2, "jurisdiction")
    other = ("redemption", 0, "settlement_time")
    c = claim("x", "verified", ["S1", "S6", "S8", "S10"], "E3")
    assert claims.verification_basis(legal, c, by_id) == []
    assert claims.verification_basis(legal, claim("x", "verified", ["S10", "S3", "S2"]), by_id) == ["S2", "S3"]
    assert claims.verification_basis(legal, claim("x", "verified", ["S5"]), by_id) == []  # third_party, legal path
    assert claims.verification_basis(other, claim("x", "verified", ["S5"]), by_id) == ["S5"]
    published = dict(by_id, S3=dict(by_id["S3"], publisher="E3"))
    assert claims.verification_basis(legal, claim("x", "verified", ["S3"], "E3"), published) == []
    assert claims.evidence_role(FILER, claim("x", subject="E3")) == "independent:filer"
    assert claims.evidence_role(dict(FILER, publisher="E3"), claim("x", subject="E3")) == "self"
    assert "filer" not in claims.LEGAL_VERIFIERS


def test_basis_counts_an_auditor_only_for_a_tested_procedure():
    doc = load_fixture()
    by_id = _sources(doc)
    parts = ("interfaces", 1, "amounts", 1, "value")
    tested = claim(1, "verified", ["S9"], origin="auditor_procedure", assurance="TESTED")
    assert claims.verification_basis(parts, tested, by_id) == ["S9"]
    for origin, assurance in (("auditor_procedure", "NOT_TESTED"), (None, None), ("onchain", "TESTED")):
        assert claims.verification_basis(parts, dict(tested, origin=origin, assurance=assurance), by_id) == []


def test_auditor_source_is_the_basis_of_the_audit_record_only(tmp_path):
    by_id = _sources(load_fixture())
    record = claim("Loan sample procedures", "verified", ["S9"])
    for field in ("auditor", "scope", "date"):
        assert claims.verification_basis(("audits", 0, field), record, by_id) == ["S9"]
    assert claims.verification_basis(("strategies", 0, "l3_business", "performance"), record, by_id) == []
    assert claims.verification_basis(("audits", 0, "scope"), dict(record, evidence=["S1"]), by_id) == []
    assert claims.AUDIT_RECORD_FIELDS == ("auditor", "scope", "date", "report_ref")
    doc = load_fixture()
    doc["strategies"][0]["l3_business"]["performance"].update({"origin": None, "assurance": None})
    assert "strategies[0].l3_business.performance: verified needs a verification basis" in \
        " ".join(validate.validate_document(doc))


def test_a6_is_not_caught_with_a_verifying_source():
    doc = load_fixture()
    doc["interfaces"][3]["enforcement"] = claim("Enforceable", "inferred", ["S8", "S2"], note="Register shows it.",
                                                origin="analyst")
    assert validate.validate_document(doc) == []
    doc["interfaces"][3]["enforcement"]["evidence"] = ["S8", "S5"]  # a legal opinion is not a disclosure
    assert validate.validate_document(doc) == []


def test_attribution_applies_under_audits():
    doc = load_fixture()
    doc["audits"][0]["scope"] = claim("Loan sample procedures", "third_party_reported", ["S9"],
                                      origin="regulator", assurance="NOT_APPLICABLE")
    assert "audits[0].scope: origin regulator requires a regulator source in evidence (curator AC-05)" in \
        validate.validate_document(doc)
    assert _qa14(doc)["detail"] == "audits[0].scope"


# --------------------------------------------------------------------------- report and derived output

def test_report_shows_basis_publication_and_corrections():
    doc = load_fixture()
    cell = render_md._Cells(doc)
    assert cell(doc["entities"][0]["jurisdiction"]) == "Examplestan [CONFIRMED] (S3; basis S3)"
    assert cell(doc["holder_rights"][0]["governing_law"]).endswith("[SELF_REPORTED] (S8)")
    fixed = ledger.make_correction(dict(doc["sources"][4]), {"source_type": "legal_doc"}, "A legal opinion, "
                                   "not research: re-typed after review.", clock_at())
    report = render_md.render(doc, corrections=[fixed])
    assert "| S5 | third_party_research | third_party | publication: research.example (third_party_research) |" \
        in report
    assert ("- S5: source\\_type third\\_party\\_research -> legal\\_doc (corrected 2026-10-01T08:00:00Z) -- A legal"
            " opinion, not research: re-typed after review.") in report
    assert "### Changes in amendment" not in report
    rows = [{"ref": "S5", "path": "source_type", "change": "changed", "before": "third_party_research",
             "after": "legal_doc", "evidence_added": []}]
    amended = render_md.render(doc, amendment=1, amendment_rows=rows)
    assert ("### Changes in amendment 1\n\n| ref | path | change | before | after | evidence added |\n"
            "|---|---|---|---|---|---|\n| S5 | source\\_type | changed | third\\_party\\_research | legal\\_doc | -- |"
            ) in amended


def test_derived_carries_verification_basis_and_amendment_changes():
    doc = load_fixture()
    out = render_md.derived(doc, "0" * 64, qa.run(doc), [])
    assert out["amendment_changes"] == [] and out["verification_basis"]["X2.amounts[0].value"] == ["S4"]
    assert list(out["verification_basis"]) == sorted(out["verification_basis"])


def test_publication_of_a_url_without_host():
    assert render_md.publication({"url": "analyst-call-notes-r1", "source_type": "analyst_input"}) == \
        "-- (analyst_input)"
    assert render_md.publication({"url": "https://www.sec.gov/x.htm", "source_type": "regulator_filing"}) == \
        "www.sec.gov (regulator_filing)"


# --------------------------------------------------------------------------- ledger fold

def _ledger_file(tmp_path, *lines):
    path = tmp_path / "sources.jsonl"
    path.write_bytes((FIXTURES / "acme.sources.jsonl").read_bytes()
                     + "".join(dump_json_line(line) for line in lines).encode("utf-8"))
    return path


def _correction(sid, fields, previous, reason=REASON, at="2026-10-21T09:00:00Z"):
    return {"correction": sid, "fields": fields, "previous": previous, "reason": reason, "corrected_at": at}


def test_read_ledger_folds_corrections_in_file_order(tmp_path):
    first = _correction("S5", {"origin": "filer", "source_type": "regulator_filing"},
                        {"origin": "third_party", "source_type": "third_party_research"})
    second = _correction("S5", {"publisher": "E7"}, {"publisher": None})
    third = _correction("S5", {"origin": "first_party"}, {"origin": "filer"})
    path = _ledger_file(tmp_path, first, second, third)
    sources = ledger.read_ledger(path)
    assert len(sources) == 9 and [s["id"] for s in sources] == ["S%d" % i for i in range(1, 10)]
    assert (sources[4]["origin"], sources[4]["source_type"], sources[4]["publisher"]) == (
        "first_party", "regulator_filing", "E7")
    assert ledger.read_corrections(path) == [first, second, third]
    swapped = _ledger_file(tmp_path, first, third, second)
    assert ledger.read_ledger(swapped)[4]["origin"] == "first_party"
    with pytest.raises(runstate.ContractError, match=r"^sources\.jsonl line 10: previous\.origin"):
        ledger.read_ledger(_ledger_file(tmp_path, third, first))


@pytest.mark.parametrize("line, message", [
    (_correction("S99", {"origin": "filer"}, {"origin": "regulator"}), "line 10: correction of unknown source"),
    (_correction("S5", {"origin": "third_party"}, {"origin": "third_party"}), "line 10: fields.origin"),
    (_correction("S5", {"title": "x"}, {"title": "Independent review of Acme Yield"}), "line 10: fields: one or"),
    (_correction("S5", {"origin": "filer"}, {"origin": "third_party"}, reason="short"), "line 10: reason"),
    (_correction("S5", {"origin": "nobody"}, {"origin": "third_party"}), "line 10: origin: not a valid origin"),
    ({"correction": "S5"}, "line 10: keys must be"),
])
def test_bad_correction_line_is_a_contract_error(tmp_path, line, message):
    with pytest.raises(runstate.ContractError, match=message):
        ledger.read_ledger(_ledger_file(tmp_path, line))


def test_malformed_ledger_line_names_the_line(tmp_path):
    path = _ledger_file(tmp_path)
    path.write_bytes(path.read_bytes() + b"{not json\n")
    with pytest.raises(runstate.ContractError, match="^sources.jsonl line 10: not valid JSON"):
        ledger.read_ledger(path)


# --------------------------------------------------------------------------- correct-source

def _filing_run(tmp_path, origin="regulator"):
    """The acme run plus S10, a 10-Q registered as regulator_registry (A1 forbids registering it as a filing with
    origin regulator, so the wrong attribution enters as a mistyped registry record)."""
    project = build_run(tmp_path)
    runstate.add_source(tmp_path, "acme", clock=clock_from_ts("2026-10-21T08:00:00Z"),
                        url="https://sec.example/x-10q.htm", title="Form 10-Q of Example Equipment Lessors Ltd",
                        source_type="regulator_registry", origin=origin, fetch="ok",
                        excerpt="The Company is party to a loan and security agreement.")
    return project


def test_add_source_refuses_attribution_violations(tmp_path):
    project = build_run(tmp_path)
    before = project.ledger_file.read_bytes()
    with pytest.raises(runstate.InvalidError) as exc:
        runstate.add_source(tmp_path, "acme", clock=clock_at(), url="https://sec.example/q.htm", title="10-Q",
                            source_type="regulator_filing", origin="regulator", fetch="ok", excerpt="Quarterly.")
    assert exc.value.errors == [
        "sources[9].origin: S10 is a filing made to a regulator; its origin is the filer (filer or first_party), "
        "not regulator (curator AC-05)",
        "sources[9].source_type: origin regulator is only for records a regulator issues or keeps "
        "(regulator_registry) (curator AC-05)"]
    for source_type, origin in (("news", "regulator"), ("project_docs", "filer")):
        with pytest.raises(runstate.InvalidError):
            runstate.add_source(tmp_path, "acme", clock=clock_at(), url="https://x.example/", title="x",
                                source_type=source_type, origin=origin, fetch="ok", excerpt="x")
    assert project.ledger_file.read_bytes() == before


def test_correct_source_appends_and_folds(tmp_path):
    project = _filing_run(tmp_path)
    before = project.ledger_file.read_bytes()
    fixed = runstate.correct_source(tmp_path, "acme", "S10",
                                    {"source_type": "regulator_filing", "origin": "filer", "publisher": "E7"},
                                    REASON, clock=clock_from_ts("2026-10-21T10:00:00Z"))
    assert fixed == {"correction": "S10",
                     "fields": {"source_type": "regulator_filing", "origin": "filer", "publisher": "E7"},
                     "previous": {"source_type": "regulator_registry", "origin": "regulator", "publisher": None},
                     "reason": REASON, "corrected_at": "2026-10-21T10:00:00Z"}
    after = project.ledger_file.read_bytes()
    assert after.startswith(before) and after[len(before):] == dump_json_line(fixed).encode("utf-8")
    source = runstate.load_work(project)["sources"][9]
    assert (source["source_type"], source["origin"], source["publisher"]) == ("regulator_filing", "filer", "E7")
    assert runstate.check(tmp_path, "acme") == [] and ledger.read_corrections(project.ledger_file) == [fixed]
    again = runstate.correct_source(tmp_path, "acme", "S10", {"publisher": None}, REASON, clock=clock_at())
    assert again["previous"] == {"publisher": "E7"} and runstate.check(tmp_path, "acme") == []
    assert project.ledger_file.read_bytes().startswith(after)


def test_correct_source_refusals(tmp_path):
    project = _filing_run(tmp_path)
    before = (project.ledger_file.read_bytes(), project.work_file.read_bytes())
    with pytest.raises(runstate.ContractError, match="unknown source S11"):
        runstate.correct_source(tmp_path, "acme", "S11", {"origin": "filer"}, REASON, clock=clock_at())
    with pytest.raises(runstate.InvalidError) as exc:
        runstate.correct_source(tmp_path, "acme", "S10", {"origin": "regulator"}, REASON, clock=clock_at())
    assert exc.value.errors == ["correct-source: fields.origin: 'regulator' equals the current value"]
    with pytest.raises(runstate.InvalidError) as exc:
        runstate.correct_source(tmp_path, "acme", "S10", {"origin": "filer"}, REASON, clock=clock_at())
    assert exc.value.errors == ["sources[9].source_type: origin filer is only for filings (regulator_filing)"]
    with pytest.raises(runstate.InvalidError) as exc:
        runstate.correct_source(tmp_path, "acme", "S10", {"source_type": "regulator_filing", "origin": "filer"},
                                "too short", clock=clock_at())
    assert exc.value.errors == ["correct-source: reason: must be 20..300 characters"]
    with pytest.raises(runstate.InvalidError) as exc:
        runstate.correct_source(tmp_path, "acme", "S10", {"publisher": "E99"}, REASON, clock=clock_at())
    assert exc.value.errors == ["sources[9].publisher: unknown entity E99"]
    assert (project.ledger_file.read_bytes(), project.work_file.read_bytes()) == before


def test_correct_source_refused_in_phase_final(tmp_path):
    project = _filing_run(tmp_path)
    state = runstate.load_state(project)
    runstate.save_state(project, dict(state, phase="final", status="final"))
    before = project.ledger_file.read_bytes()
    with pytest.raises(runstate.ContractError, match="requires an open run"):
        runstate.correct_source(tmp_path, "acme", "S10", {"origin": "registry"}, REASON, clock=clock_at())
    assert project.ledger_file.read_bytes() == before


def test_correct_source_cli(tmp_path):
    project = _filing_run(tmp_path)
    base = ["--slug", "acme", "--root", str(tmp_path)]
    code, out, err = run_cli(["correct-source"] + base + ["--id", "S10", "--source-type", "regulator_filing",
                                                          "--origin", "filer", "--reason", REASON])
    assert (code, err) == (0, "") and json.loads(out)["fields"] == {"source_type": "regulator_filing",
                                                                    "origin": "filer"}
    code, out, _ = run_cli(["correct-source"] + base + ["--id", "S10", "--publisher", "E7", "--reason", REASON])
    assert code == 0 and json.loads(out)["previous"] == {"publisher": None}
    code, out, _ = run_cli(["correct-source"] + base + ["--id", "S10", "--publisher", "none", "--reason", REASON])
    assert code == 0 and json.loads(out)["fields"] == {"publisher": None}
    code, out, _ = run_cli(["correct-source"] + base + ["--id", "S10", "--reason", REASON])
    assert (code, out) == (2, "correct-source: give at least one of --source-type, --origin, --publisher\n")
    code, _, err = run_cli(["correct-source"] + base + ["--id", "S12", "--origin", "filer", "--reason", REASON])
    assert code == 3 and "unknown source S12" in err
    assert runstate.check(tmp_path, "acme") == [] and len(ledger.read_corrections(project.ledger_file)) == 3


# --------------------------------------------------------------------------- change rows

def test_changes_rows_for_corrections():
    old = load_fixture()
    new = copy.deepcopy(old)
    new["sources"][4].update({"origin": "filer", "source_type": "regulator_filing", "publisher": "E7"})
    rows = [r for r in changes.diff(old, new) if r["ref"] == "S5"]
    assert rows == [
        {"ref": "S5", "path": "origin", "change": "changed", "before": "third_party", "after": "filer",
         "evidence_added": []},
        {"ref": "S5", "path": "publisher", "change": "changed", "before": "null", "after": "E7",
         "evidence_added": []},
        {"ref": "S5", "path": "source_type", "change": "changed", "before": "third_party_research",
         "after": "regulator_filing", "evidence_added": []}]


# --------------------------------------------------------------------------- amendment_changes

def test_amendment_log_is_empty_before_an_amendment(tmp_path):
    project = build_run(tmp_path)
    assert runstate.amendment_log(project, runstate.load_state(project), runstate.load_work(project)) == []


@pytest.mark.d2
@NEEDS_D2
def test_amendment_changes_against_the_archived_version(tmp_path):
    project = _filing_run(tmp_path, origin="regulator")
    runstate.make_review(tmp_path, "acme")
    path = project.scratch / "logs" / "reply.txt"
    path.write_bytes(b"finalize\n")
    runstate.apply_directives(tmp_path, "acme", path)
    runstate.finalize(tmp_path, "acme", clock=clock_at())
    run_id = runstate.load_state(project)["run_id"]
    amend = project.scratch / "logs" / "amend-1.txt"
    amend.write_bytes(b"note S10 is a 10-Q filed by E7, not a register record\n")
    runstate.amend(tmp_path, "acme", amend)
    assert (project.archive / ("%s.v0" % run_id) / "acme.dd.json").is_file()
    runstate.correct_source(tmp_path, "acme", "S10", {"source_type": "regulator_filing", "origin": "filer",
                                                      "publisher": "E7"}, REASON, clock=clock_at())
    doc = runstate.load_work(project)
    doc["interfaces"][3]["terms"] = claim("Secured equipment loan facility", "self_reported", ["S10"], "E7",
                                          origin="borrower")
    runstate.save_work(project, doc)
    expected = [
        {"ref": "S10", "path": "origin", "change": "changed", "before": "regulator", "after": "filer",
         "evidence_added": []},
        {"ref": "S10", "path": "publisher", "change": "changed", "before": "null", "after": "E7",
         "evidence_added": []},
        {"ref": "S10", "path": "source_type", "change": "changed", "before": "regulator_registry",
         "after": "regulator_filing", "evidence_added": []}]
    rows = runstate.amendment_log(project, runstate.load_state(project), doc)
    assert [r for r in rows if r["ref"] == "S10"] == expected
    terms = [r for r in rows if (r["ref"], r["path"]) == ("X4", "terms")]
    assert len(terms) == 1 and terms[0]["after"].startswith("Secured equipment loan facility [self_reported]")
    result = runstate.render_draft(tmp_path, "acme", clock=clock_at())
    derived = json.loads((project.scratch / "draft" / "acme.derived.json").read_bytes().decode("utf-8"))
    assert derived["amendment_changes"] == rows
    report = (project.scratch / "draft" / "acme.report.md").read_bytes().decode("utf-8")
    assert "### Changes in amendment 1" in report and "| S10 | origin | changed | regulator | filer | -- |" in report
    assert "- S10: origin regulator -> filer; publisher -- -> E7; source\\_type regulator\\_registry -> " \
           "regulator\\_filing (corrected 2026-10-01T08:00:00Z)" in report
    assert result["outputs"]
