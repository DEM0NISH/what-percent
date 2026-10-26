"""Command-line entry point for What%."""

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level parser so commands can be added incrementally."""
    parser = argparse.ArgumentParser(
        prog="whatpercent",
        description="A self-monitoring scraper with validated fallbacks.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("collect", "health", "spotcheck", "analyze", "build-db"),
        help="operation to run (available in later project steps)",
    )
    return parser


def main() -> None:
    """Print help by default; command implementations are added in later steps."""
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    parser.error(f"{args.command!r} is not implemented yet")


if __name__ == "__main__":
    main()
