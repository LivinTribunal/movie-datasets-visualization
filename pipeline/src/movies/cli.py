"""Command line entry point: `movies <stage> [options]`."""

import argparse

from movies.acquire import download
from movies.reference import countries


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="movies")
    sub = parser.add_subparsers(dest="stage", required=True)

    acquire = sub.add_parser(
        "acquire", help="download raw datasets and build the Wikidata crosswalk"
    )
    acquire.add_argument(
        "--source",
        action="append",
        default=[],
        metavar="NAME",
        help="only this source (repeatable); needed for optional sources such as rt_legacy",
    )
    acquire.add_argument("--force", action="store_true", help="ignore the lock and re-download")

    sub.add_parser("reference", help="build data/reference/countries.csv")

    args = parser.parse_args(argv)
    if args.stage == "acquire":
        download.run(args.source, force=args.force)
    elif args.stage == "reference":
        countries.run()
