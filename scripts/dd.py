"""rwa-due-diligence CLI: run directory, source ledger, validation, review loop and reports.

Exit codes: 0 ok, 2 invalid document, directives or input, 3 contract violation (paths or state),
4 diagram renderer d2 missing, wrong version or failed; pypdf missing; download failed.
"""

import argparse
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from lib import fetch, flow, pdftext, runstate, schema  # noqa: E402

EXIT_OK = 0
EXIT_INVALID = 2
EXIT_CONTRACT = 3
EXIT_DEPENDENCY = 4


def _out(text):
    sys.stdout.write(text if text.endswith("\n") else text + "\n")


def _json(value):
    _out(json.dumps(value, indent=2, ensure_ascii=True))


def build_parser():
    parser = argparse.ArgumentParser(
        prog="dd.py",
        description="Read-only RWA due diligence: run directory, source ledger, validation, review loop, reports.",
        epilog="Exit codes: 0 ok, 2 invalid document, directives or input, 3 contract violation (paths or state), "
               "4 diagram renderer d2 missing, wrong version or failed; pypdf missing; download failed.")
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    def with_slug(name, help_text):
        p = sub.add_parser(name, help=help_text, description=help_text)
        p.add_argument("--slug", required=True, help="project slug, ^[a-z0-9][a-z0-9-]{1,40}$")
        p.add_argument("--root", default=".", help="reports root (default: current directory)")
        return p

    p = with_slug("init", "create <root>/<slug>/ with a skeleton working document")
    p.add_argument("--url", required=True, help="project root URL")
    p.add_argument("--new-run", action="store_true", help="archive the previous run and start a new one")

    p = with_slug("add-source", "append a source to the ledger and the working document")
    p.add_argument("--url", required=True, help="source URL or local path (<=500)")
    p.add_argument("--title", required=True, help="source title (<=200)")
    p.add_argument("--source-type", required=True, choices=schema.ENUMS["source_type"], metavar="TYPE",
                   help="one of: " + ", ".join(schema.ENUMS["source_type"]))
    p.add_argument("--origin", required=True, choices=schema.ENUMS["origin"], metavar="ORIGIN",
                   help="one of: " + ", ".join(schema.ENUMS["origin"]))
    p.add_argument("--fetch", required=True, choices=schema.ENUMS["fetch"], metavar="FETCH",
                   help="one of: " + ", ".join(schema.ENUMS["fetch"]))
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--excerpt", help="quoted excerpt (<=300; whitespace is collapsed)")
    group.add_argument("--excerpt-file", help="UTF-8 file holding the excerpt (<=300; whitespace is collapsed)")
    p.add_argument("--publisher", default=None, help="entity id E<n> that published the source")
    p.add_argument("--archived", action="store_true", help="the source is an archived copy")
    p.add_argument("--version-date", default=None, help="YYYY-MM-DD version of an archived copy")
    p.add_argument("--note", default="", help="note (<=200)")
    p.add_argument("--offline", action="store_true", help="no retrieval time: retrieved_at null, fetch offline")

    with_slug("validate", "validate audit/dd.work.json against the schema and the ledger")
    with_slug("review", "write the review packet of the current round")
    p = with_slug("directives", "record and parse the analyst directives of the current round")
    p.add_argument("--file", required=True, help="file holding the analyst reply verbatim")
    with_slug("render", "draft render into .scratch/draft/ (any phase)")
    with_slug("status", "print run state and counts as JSON")
    with_slug("finalize", "write the final outputs (after a finalize directive)")
    p = with_slug("amend", "reopen a final run for one more research round (moves outputs to archive/)")
    p.add_argument("--file", required=True, help="file holding the amendment verbatim (note, add-source, answer, drop)")
    p = with_slug("fetch-file", "download one public HTTPS file into .scratch/raw/NAME (does not add a source)")
    p.add_argument("--url", required=True, help="https URL of a public file")
    p.add_argument("--name", required=True, help="file name, ^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
    p.add_argument("--overwrite", action="store_true", help="replace an existing .scratch/raw/NAME")
    p = with_slug("pdf-text", "extract the text of .scratch/raw/NAME into .scratch/text/NAME.txt (needs pypdf)")
    p.add_argument("--name", required=True, help="file name under .scratch/raw/")
    sub.add_parser("schema-doc", help="print references/schema.md to stdout",
                   description="print references/schema.md to stdout")
    return parser


def _excerpt(args):
    if args.excerpt_file is not None:
        try:
            text = Path(args.excerpt_file).read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            raise runstate.InvalidError(["excerpt: file is not UTF-8"])
    else:
        text = args.excerpt
    return " ".join(text.split())


def run(args):
    cmd = args.command
    if cmd == "schema-doc":
        sys.stdout.write(schema.schema_doc())
    elif cmd == "init":
        _json(runstate.init(args.root, args.slug, args.url, new_run=args.new_run))
    elif cmd == "add-source":
        source = runstate.add_source(
            args.root, args.slug, url=args.url, title=args.title, source_type=args.source_type,
            origin=args.origin, fetch=args.fetch, excerpt=_excerpt(args), publisher=args.publisher,
            archived=args.archived, version_date=args.version_date, note=args.note, offline=args.offline)
        _json(source)
    elif cmd == "validate":
        errors = runstate.check(args.root, args.slug)
        if errors:
            raise runstate.InvalidError(errors)
        _out("valid")
    elif cmd == "review":
        _json(runstate.make_review(args.root, args.slug))
    elif cmd == "directives":
        _json(runstate.apply_directives(args.root, args.slug, args.file))
    elif cmd == "render":
        _json(runstate.render_draft(args.root, args.slug))
    elif cmd == "status":
        _json(runstate.status(args.root, args.slug))
    elif cmd == "finalize":
        _json(runstate.finalize(args.root, args.slug))
    elif cmd == "amend":
        _json(runstate.amend(args.root, args.slug, args.file))
    elif cmd == "fetch-file":
        _json(fetch.fetch_file(args.root, args.slug, args.url, args.name, overwrite=args.overwrite))
    elif cmd == "pdf-text":
        _json(pdftext.pdf_text(args.root, args.slug, args.name))
    return EXIT_OK


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except runstate.InvalidError as exc:
        for line in sorted(exc.errors):
            _out(line)
        return EXIT_INVALID
    except (flow.DependencyError, flow.RenderError, pdftext.DependencyError) as exc:
        sys.stderr.write("dependency error: %s\n" % exc)
        return EXIT_DEPENDENCY
    except fetch.FetchError as exc:
        sys.stderr.write("network error: %s\n" % exc)
        return EXIT_DEPENDENCY
    except runstate.ContractError as exc:
        sys.stderr.write("contract violation: %s\n" % exc)
        return EXIT_CONTRACT
    except OSError as exc:
        sys.stderr.write("contract violation: %s\n" % exc)
        return EXIT_CONTRACT


if __name__ == "__main__":
    sys.exit(main())
