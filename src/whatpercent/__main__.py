"""Command-line entry point for What%."""

import argparse
import logging
from pathlib import Path

from whatpercent.analysis import run_analysis
from whatpercent.collect import collect_products
from whatpercent.config import ConfigurationError, load_settings
from whatpercent.spotcheck import record_result, sample_rows, summarize
from whatpercent.storage import build_database, load_run_rows


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
    health = commands.add_parser("health", help="show per-site collection health")
    health.add_argument("--run", default="latest", help="run id or latest")
    spotcheck = commands.add_parser("spotcheck", help="sample and record manual checks")
    spot_commands = spotcheck.add_subparsers(dest="spotcheck_command", required=True)
    spot_commands.add_parser("sample", help="sample recent usable rows")
    record = spot_commands.add_parser("record", help="record a manual comparison")
    record.add_argument("row_key")
    record.add_argument("result", choices=("match", "mismatch"))
    record.add_argument("note", nargs="?", default="")
    spot_commands.add_parser("summary", help="show completed spot-check accuracy")
    commands.add_parser(
        "analyze", help="analyse collected observations for a configured sale window"
    )
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
            summary = collect_products(
                config_path=args.config,
                limit=args.limit,
                site=args.site,
                offline_dir=args.offline_dir,
                force=args.force,
            )
            if summary.suspect:
                print("Collection health is suspect:")
                print(summary.report)
                raise SystemExit(3)
        elif args.command == "build-db":
            settings = load_settings()
            path = build_database(settings.data_dir)
            print(f"SQLite cache rebuilt: {path}")
        elif args.command == "health":
            settings = load_settings()
            rows = load_run_rows(settings.data_dir)
            if args.run != "latest":
                rows = [row for row in rows if row.get("run_id") == args.run]
            elif rows:
                latest = rows[-1].get("run_id")
                rows = [row for row in rows if row.get("run_id") == latest]
            if not rows:
                print("No collection health rows are available.")
                return
            for row in rows:
                state = "suspect" if row.get("suspect") == "true" else "healthy"
                reasons = row.get("reasons") or "none"
                print(
                    f"{row['site']}: {state}; rows={row['rows']}; "
                    f"price_fill={row['price_fill']}; title_fill={row['title_fill']}; "
                    f"validity={row['validity_rate']}; reasons={reasons}"
                )
        elif args.command == "spotcheck":
            settings = load_settings()
            if args.spotcheck_command == "sample":
                rows = sample_rows(settings.data_dir)
                for row in rows:
                    print(
                        f"{row['row_key']} | {row['product']} | ₹{row['price']} / "
                        f"MRP ₹{row['mrp']} | {row['url']}"
                    )
                if not rows:
                    print("No recent ok/fallback_ok rows are available to sample.")
            elif args.spotcheck_command == "record":
                record_result(settings.data_dir, args.row_key, args.result, args.note)
                print("Spot-check saved privately.")
            else:
                matches, total, accuracy = summarize(settings.data_dir)
                if accuracy is None:
                    print("No completed manual spot-checks yet.")
                else:
                    print(f"Accuracy: {accuracy:.1f}% ({matches}/{total} matched)")
        elif args.command == "analyze":
            target = run_analysis(load_settings().data_dir)
            if target is None:
                print("Analysis pending: no collected observations or sale window configured.")
            else:
                print(f"Analysis summary written: {target}")
        else:
            parser.error(f"{args.command!r} is not implemented yet")
    except SystemExit:
        raise
    except (ConfigurationError, OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
