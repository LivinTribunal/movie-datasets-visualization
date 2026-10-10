"""Command line entry point: `movies <stage> [options]`."""

import argparse

from movies import clean, scrape
from movies.acquire import download
from movies.join import films
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

    clean_p = sub.add_parser(
        "clean", help="raw files -> one tidy Parquet per source in data/interim"
    )
    clean_p.add_argument(
        "--source",
        action="append",
        default=[],
        metavar="NAME",
        help="only this source (repeatable)",
    )

    sub.add_parser(
        "join", help="tmdb + Wikidata + RT + The Numbers -> films.parquet, Netflix title matches"
    )

    scrape_parser = sub.add_parser("scrape", help="scrape web and API sources -> data/scraped")
    scrape_parser.add_argument("--source", required=True, choices=scrape.SOURCES, metavar="NAME")

    args = parser.parse_args(argv)
    if args.stage == "acquire":
        download.run(args.source, force=args.force)
    elif args.stage == "reference":
        countries.run()
    elif args.stage == "clean":
        clean.run(args.source)
    elif args.stage == "join":
        films.run()
    elif args.stage == "scrape":
        scrape.run(args.source)
