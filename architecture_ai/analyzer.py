"""RAG-backed architecture analysis using the local Ollama model."""

import json
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from architecture_ai.extractor import analyze_repositories
from architecture_ai.ollama_provider import call_local_model
from architecture_ai.retrieval import search_evidence


PROMPTS_DIRECTORY = Path(__file__).resolve().parent.parent / "prompts"


def _retrieve_context(database, query, limit):
    """Mix user keywords with architecture terms and favor repository diversity."""
    results = search_evidence(database, query, limit=max(limit, 4))
    results += search_evidence(database, 'http kafka route endpoint topic resource service', limit=max(limit * 2, 8))
    unique = []
    seen = set()
    for chunk in results:
        key = (chunk['repository'], chunk['path'], chunk['start_line'], chunk['end_line'])
        if key not in seen:
            seen.add(key)
            unique.append(chunk)
    first = []
    repositories = set()
    for chunk in unique:
        if chunk['repository'] not in repositories:
            first.append(chunk)
            repositories.add(chunk['repository'])
    remainder = [chunk for chunk in unique if chunk not in first]
    return (first + remainder)[:max(limit, 4)]


def _evidence_records(architecture: Dict[str, object]) -> List[Dict[str, object]]:
    records = []
    for repository in architecture["repositories"]:
        for fact in repository["facts"]:
            for item in fact["evidence"]:
                for repository_name in (repository["service"], repository["repository"]):
                    records.append({
                        "repository": repository_name,
                        "file": item["file"],
                        "line": item["line"],
                        "snippet": item["snippet"],
                    })
    return records


def _all_claim_evidence(result: Dict[str, object]) -> List[Dict[str, object]]:
    evidence = []
    for component in result.get("components", []):
        evidence.extend(component.get("evidence", []))
        for interface in component.get("interfaces", []):
            evidence.extend(interface.get("evidence", []))
    for relationship in result.get("relationships", []):
        evidence.extend(relationship.get("evidence", []))
    return evidence


def _audit_citations(result: Dict[str, object], source_records: Sequence[Dict[str, object]]) -> List[str]:
    exact = {
        (record["repository"], record["file"], record["line"], record["snippet"])
        for record in source_records
    }
    locations = {(repo, path, line) for repo, path, line, _ in exact}
    warnings = []
    for citation in _all_claim_evidence(result):
        key = (
            citation.get("repository"), citation.get("file"), citation.get("line"),
            citation.get("snippet"),
        )
        location = key[:3]
        if location not in locations:
            warnings.append("Citation points outside the supplied evidence: {}".format(key))
        elif key not in exact:
            warnings.append("Citation location exists, but its snippet differs from source: {}".format(key))
    return warnings


def source_records_for_query(query, repositories, database, limit=4):
    architecture = analyze_repositories(repositories)
    records = _evidence_records(architecture)
    for chunk in _retrieve_context(database, query, limit):
        for offset, snippet in enumerate(chunk['content'].splitlines()):
            if snippet.strip():
                records.append({'repository': chunk['repository'], 'file': chunk['path'],
                                'line': chunk['start_line'] + offset, 'snippet': snippet.strip()})
    return records


def analyze_with_local_model(
    query: str,
    repositories: Sequence[Path],
    database: Path,
    prompt_version: str = "v3",
    limit: int = 4,
    history: Sequence[Dict[str, object]] = (),
) -> Tuple[Dict[str, object], List[str]]:
    prompt_path = PROMPTS_DIRECTORY / (prompt_version + ".md")
    if prompt_version not in {"v1", "v2", "v3"} or not prompt_path.is_file():
        raise ValueError("Prompt version must be one of v1, v2, or v3")

    architecture = analyze_repositories(repositories)
    source_records = _evidence_records(architecture)
    retrieved = _retrieve_context(database, query, limit)
    for chunk in retrieved:
        for offset, snippet in enumerate(chunk["content"].splitlines()):
            if snippet.strip():
                source_records.append({
                    "repository": chunk["repository"],
                    "file": chunk["path"],
                    "line": chunk["start_line"] + offset,
                    "snippet": snippet.strip(),
                })
    context = {
        "static_findings": architecture["repositories"],
        "retrieved_source_chunks": retrieved,
        "previous_turns_unverified": list(history)[-2:],
    }
    prompt = prompt_path.read_text(encoding="utf-8")
    prompt = prompt.replace("{{request}}", query)
    prompt = prompt.replace("{{evidence}}", json.dumps(context, ensure_ascii=False, indent=2))

    result = call_local_model(prompt)
    warnings = _audit_citations(result, source_records)
    return result, warnings
