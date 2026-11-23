"""Command-line interface for architecture-ai."""

import argparse
import json
from pathlib import Path

from architecture_ai.extractor import analyze_repositories


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze architecture evidence in Go repositories")
    subparsers = parser.add_subparsers(dest="command", required=True)
    extract = subparsers.add_parser("extract", help="extract static facts with code evidence")
    extract.add_argument("repositories", nargs="+", type=Path)
    extract.add_argument("--output", type=Path, default=Path("architecture.json"))
    args = parser.parse_args()

    if args.command == "extract":
        result = analyze_repositories(args.repositories)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        count = sum(len(repo["facts"]) for repo in result["repositories"])
        print("Wrote {} facts from {} repositories to {}".format(
            count, len(result["repositories"]), args.output
        ))

