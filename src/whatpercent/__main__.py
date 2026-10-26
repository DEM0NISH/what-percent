"""Command-line entry point for What%."""

import argparse
import logging
from pathlib import Path

from whatpercent.collect import collect_products
from whatpercent.config import ConfigurationError, load_settings
from whatpercent.storage import build_database


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser while keeping collection options explicit."""
    parser = argparse.ArgumentParser(
        prog="whatpercent",
        description="A self-monitoring scraper with validated fallbacks.",
    )
    commands = parser.add_subparsers(dest="command")
    collect = commands.add_parser("collect", help="collect configured public product pages")
    collect.add_argument("--config", default="products.yaml", help="product YAML config path")
    collect.add_argument("--limit", type=int, help="maximum products to collect")
    collect.add_argument("--site", help="collect only this approved site key")
    collect.add_argument("--offline-dir", type=Path, help="read hashed saved HTML fixtures only")
    collect.add_argument(
        "--force", action="store_true", help="append observations despite same-day keys"
    )
    commands.add_parser("build-db", help="rebuild the derived SQLite cache from CSV files")
    for name in ("health", "spotcheck", "analyze"):
        commands.add_parser(name, help=f"{name} (implemented in a later project step)")
    return parser


def main() -> None:
    """Dispatch collection and storage commands; all errors are concise for CLI users."""
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        if args.command == "collect":
            collect_products(
                config_path=args.config,
                limit=args.limit,
                site=args.site,
                offline_dir=args.offline_dir,
                force=args.force,
            )
        elif args.command == "build-db":
            settings = load_settings()
            path = build_database(settings.data_dir)
            print(f"SQLite cache rebuilt: {path}")
        else:
            parser.error(f"{args.command!r} is not implemented yet")
    except (ConfigurationError, OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
