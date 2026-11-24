"""Command-line interface for architecture-ai."""

import argparse
import json
import os
from pathlib import Path

from architecture_ai.analyzer import analyze_with_local_model
from architecture_ai.extractor import analyze_repositories
from architecture_ai.retrieval import index_repositories, search_evidence
from architecture_ai.render import generate_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze architecture evidence in Go repositories")
    subparsers = parser.add_subparsers(dest="command", required=True)
    extract = subparsers.add_parser("extract", help="extract static facts with code evidence")
    extract.add_argument("repositories", nargs="+", type=Path)
    extract.add_argument("--output", type=Path, default=Path("architecture.json"))
    index = subparsers.add_parser("index", help="index source files in a local FTS5 database")
    index.add_argument("repositories", nargs="+", type=Path)
    index.add_argument("--database", type=Path, default=Path(".architecture/evidence.sqlite"))
    search = subparsers.add_parser("search", help="retrieve evidence chunks from the local index")
    search.add_argument("query", nargs="+")
    search.add_argument("--database", type=Path, default=Path(".architecture/evidence.sqlite"))
    search.add_argument("--limit", type=int, default=5)
    report = subparsers.add_parser("report", help="generate cited JSON, Markdown, and Mermaid files")
    report.add_argument("repositories", nargs="+", type=Path)
    report.add_argument("--output-dir", type=Path, default=Path("docs/generated"))
    analyze = subparsers.add_parser("analyze", help="generate a cited architecture answer with local Ollama")
    analyze.add_argument("query")
    analyze.add_argument("repositories", nargs="+", type=Path)
    analyze.add_argument("--database", type=Path, default=Path(".architecture/evidence.sqlite"))
    analyze.add_argument("--prompt", choices=["v1", "v2", "v3"], default="v3")
    analyze.add_argument("--limit", type=int, default=4)
    analyze.add_argument("--output", type=Path, default=Path("docs/generated/llm-analysis.json"))
    chat = subparsers.add_parser("chat", help="chat interativo com URLs HTTPS ou pastas locais")
    chat.add_argument("sources", nargs="*", help="URLs HTTPS ou caminhos locais")
    chat.add_argument("--output-dir", type=Path, default=Path("docs/generated"))
    chat.add_argument("--prompt", choices=["v1", "v2", "v3"], default="v3")
    args = parser.parse_args()

    if args.command == "chat":
        from architecture_ai.chat import run_chat
        try:
            run_chat(args.sources, args.output_dir.expanduser().resolve(), args.prompt)
        except (ValueError, KeyboardInterrupt) as error:
            print("\n{}".format(error or "Operação cancelada."))
    elif args.command == "extract":
        result = analyze_repositories(args.repositories)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        count = sum(len(repo["facts"]) for repo in result["repositories"])
        print("Wrote {} facts from {} repositories to {}".format(
            count, len(result["repositories"]), args.output
        ))
    elif args.command == "index":
        count = index_repositories(args.repositories, args.database)
        print("Indexed {} evidence chunks in {}".format(count, args.database))
    elif args.command == "search":
        query = " ".join(args.query)
        results = search_evidence(args.database, query, args.limit)
        for item in results:
            print("{}:{}:{}-{}".format(
                item["repository"], item["path"], item["start_line"], item["end_line"]
            ))
            print(item["content"])
            print()
        if not results:
            print("No matching evidence found.")
    elif args.command == "report":
        outputs = generate_report(args.repositories, args.output_dir)
        for kind, path in outputs.items():
            print("Wrote {}: {}".format(kind, path))
    elif args.command == "analyze":
        result, citation_warnings = analyze_with_local_model(
            args.query, args.repositories, args.database, args.prompt, args.limit
        )
        payload = {
            "model": os.environ.get("OLLAMA_MODEL", "qwen3:8b"),
            "prompt_version": args.prompt,
            "analysis": result,
            "citation_warnings": citation_warnings,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Wrote local-model analysis to {}".format(args.output))

