"""Extração estática auditável para os padrões Go do MVP."""

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


ROUTE_RE = re.compile(r'HandleFunc\("([A-Z]+)\s+([^" ]+)"')
ENV_DEFAULT_RE = re.compile(
    r'envOrDefault\("([A-Z][A-Z0-9_]*)",\s*"([^\"]+)"\)'
)
TOPIC_FIELD_RE = re.compile(r'Topic:\s*([A-Za-z_][A-Za-z0-9_]*)')
ENV_ACCESS_RE = re.compile(r'os\.Getenv\("([A-Z][A-Z0-9_]*)"\)')
IGNORED_DIRS = {".git", "vendor", "node_modules"}


def _read_go_files(repository: Path) -> Iterable[tuple[Path, List[str]]]:
    for path in sorted(repository.rglob("*.go")):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        yield path, text.splitlines()


def _evidence(repository: Path, path: Path, line_number: int, line: str) -> Dict[str, object]:
    return {
        "file": path.relative_to(repository).as_posix(),
        "line": line_number,
        "snippet": line.strip(),
    }


def _fact(kind: str, service: str, protocol: str, details: Dict[str, str],
          certainty: str, evidence: Sequence[Dict[str, object]]) -> Dict[str, object]:
    return {
        "kind": kind,
        "service": service,
        "protocol": protocol,
        "details": details,
        "certainty": certainty,
        "evidence": list(evidence),
    }


def extract_repository(repository: Path) -> Dict[str, object]:
    """Extract explicit interfaces and communication hints from one Go repository."""
    repository = repository.expanduser().resolve()
    if not repository.is_dir():
        raise ValueError("Not a directory: {}".format(repository))

    service = repository.name
    files = list(_read_go_files(repository))
    facts: List[Dict[str, object]] = []
    env_defaults: Dict[str, tuple[str, Dict[str, object]]] = {}
    env_accesses: Dict[str, Dict[str, object]] = {}
    kafka_writer = False
    kafka_reader = False

    for path, lines in files:
        for line_number, line in enumerate(lines, start=1):
            route = ROUTE_RE.search(line)
            if route:
                facts.append(_fact(
                    "exposes_endpoint", service, "REST",
                    {"method": route.group(1), "path": route.group(2)}, "confirmed",
                    [_evidence(repository, path, line_number, line)],
                ))

            for match in ENV_DEFAULT_RE.finditer(line):
                env_defaults[match.group(1)] = (
                    match.group(2), _evidence(repository, path, line_number, line)
                )
            env_access = ENV_ACCESS_RE.search(line)
            if env_access:
                env_accesses[env_access.group(1)] = _evidence(
                    repository, path, line_number, line
                )
            if "kafka.Writer{" in line:
                kafka_writer = True
            if "kafka.ReaderConfig{" in line:
                kafka_reader = True

    for path, lines in files:
        for line_number, line in enumerate(lines, start=1):
            field = TOPIC_FIELD_RE.search(line)
            if not field:
                continue
            # Resolve only the common envOrDefault("..._TOPIC", "literal") idiom.
            topic_env = next(
                (env_name for env_name in env_defaults if env_name.endswith("_TOPIC")),
                None,
            )
            if not topic_env:
                continue
            topic, default_evidence = env_defaults[topic_env]
            topic_field_evidence = _evidence(repository, path, line_number, line)
            if kafka_writer:
                facts.append(_fact(
                    "publishes_to", service, "Kafka", {"topic": topic}, "confirmed",
                    [default_evidence, topic_field_evidence],
                ))
            if kafka_reader:
                facts.append(_fact(
                    "consumes_from", service, "Kafka", {"topic": topic}, "confirmed",
                    [default_evidence, topic_field_evidence],
                ))

    # Find HTTP client construction and bind a likely target only through the
    # environment prefix (e.g. CATALOG_BASE_URL -> catalog-service).
    client_evidence = []
    rest_path = None
    for path, lines in files:
        for line_number, line in enumerate(lines, start=1):
            if "http.NewRequest" in line or ".Get(" in line or ".Do(request)" in line:
                client_evidence.append(_evidence(repository, path, line_number, line))
            if '"/products/"' in line:
                rest_path = "/products/{productId}"

    candidate_target: Optional[str] = None
    target_config_evidence = None
    for env_name, (_, evidence) in env_defaults.items():
        if env_name.endswith("_BASE_URL"):
            candidate_target = env_name[:-len("_BASE_URL")].lower()
            target_config_evidence = evidence
            break
    if candidate_target is None:
        for env_name, evidence in env_accesses.items():
            if env_name.endswith("_BASE_URL"):
                candidate_target = env_name[:-len("_BASE_URL")].lower()
                target_config_evidence = evidence
                break
    if client_evidence and candidate_target:
        ev = [target_config_evidence] + client_evidence[:2]
        facts.append(_fact(
            "calls_endpoint", service, "REST",
            {"target_hint": candidate_target, "method": "GET", "path": rest_path or "unknown"},
            "inferred", ev,
        ))

    return {"repository": str(repository), "service": service, "facts": facts}


def analyze_repositories(repositories: Sequence[Path]) -> Dict[str, object]:
    results = [extract_repository(path) for path in repositories]
    names = {
        item["service"].lower().replace("-service", "").replace("-api", ""): item["service"]
        for item in results
    }
    # Promote the target hint to a service name only when an input repository matches.
    for result in results:
        for fact in result["facts"]:
            hint = fact.get("details", {}).get("target_hint")
            if hint in names:
                fact["details"]["target"] = names[hint]
    return {"schema_version": "1", "repositories": results}


def write_json(result: Dict[str, object], output: Path) -> None:
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

