"""Render static findings as a cited Markdown report and Mermaid diagram."""

import json
import re
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from architecture_ai.extractor import analyze_repositories


def _citation(evidence: Dict[str, object], repository: str) -> str:
    return "`{}/{}:{}`".format(repository, evidence["file"], evidence["line"])


def _fact_citations(fact: Dict[str, object]) -> str:
    return ", ".join(
        _citation(item, fact["service"]) for item in fact.get("evidence", [])
    )


def _service_id(service: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", service)


def _communication_edges(repositories: Sequence[Dict[str, object]]) -> List[Tuple[str, str, str, str, str]]:
    facts = [fact for repo in repositories for fact in repo["facts"]]
    publishers = [fact for fact in facts if fact["kind"] == "publishes_to"]
    consumers = [fact for fact in facts if fact["kind"] == "consumes_from"]
    edges = []
    for publisher in publishers:
        topic = publisher["details"]["topic"]
        for consumer in consumers:
            if consumer["details"]["topic"] == topic:
                evidence = "{}; {}".format(
                    _fact_citations(publisher), _fact_citations(consumer)
                )
                edges.append((
                    publisher["service"], consumer["service"],
                    "Kafka: {} (confirmado)".format(topic), "confirmed", evidence,
                ))
    for fact in facts:
        if fact["kind"] != "calls_endpoint":
            continue
        target = fact["details"].get("target")
        if target:
            label = "REST {} {} (inferido)".format(
                fact["details"].get("method", "?"), fact["details"].get("path", "?")
            )
            edges.append((
                fact["service"], target, label, "inferred", _fact_citations(fact)
            ))
    return edges


def render_mermaid(architecture: Dict[str, object]) -> str:
    repositories = architecture["repositories"]
    lines = ["flowchart LR"]
    for repo in repositories:
        service = repo["service"]
        lines.append('    {}["{}"]'.format(_service_id(service), service))
    for source, target, label, certainty, _ in _communication_edges(repositories):
        if certainty == "inferred":
            # Mermaid's documented dotted-link label form is `A-. text .->B`.
            safe_label = label.replace("{productId}", "productId")
            lines.append('    {} -. {} .-> {}'.format(
                _service_id(source), safe_label, _service_id(target)
            ))
        else:
            lines.append('    {} -->|"{}"| {}'.format(
                _service_id(source), label, _service_id(target)
            ))
    if len(lines) == 1:
        lines.append("    no_relationships[\"No communication relationships detected\"]")
    return "\n".join(lines) + "\n"


def render_markdown(architecture: Dict[str, object]) -> str:
    repositories = architecture["repositories"]
    lines = [
        "# Architecture findings",
        "",
        "> Generated from static source analysis. `Confirmed` means the code directly "
        "contains the interface/configuration; `Inferred` means a relationship is "
        "matched across evidence. No LLM was used to create these findings.",
        "",
        "## Components and observed interfaces",
        "",
    ]
    for repo in repositories:
        facts = repo["facts"]
        lines.extend(["### {}".format(repo["service"]), ""])
        if not facts:
            lines.extend(["No supported interfaces were detected; responsibility is unknown.", ""])
            continue
        for fact in facts:
            details = fact["details"]
            if fact["kind"] == "exposes_endpoint":
                description = "exposes {} {} (confirmed)".format(details["method"], details["path"])
            elif fact["kind"] == "publishes_to":
                description = "publishes to Kafka topic `{}` (confirmed)".format(details["topic"])
            elif fact["kind"] == "consumes_from":
                description = "consumes Kafka topic `{}` (confirmed)".format(details["topic"])
            elif fact["kind"] == "calls_endpoint":
                destination = details.get("target", details.get("target_hint", "unknown service"))
                description = "calls {} {} on {} (inferred relationship)".format(
                    details.get("method", "?"), details.get("path", "?"), destination
                )
            else:
                description = "{} ({})".format(fact["kind"], fact["certainty"])
            lines.append("- {} — evidence: {}".format(description, _fact_citations(fact)))
        lines.append("")

    lines.extend(["## Communication relationships", ""])
    edges = _communication_edges(repositories)
    if edges:
        for source, target, label, certainty, evidence in edges:
            lines.append("- **{} → {}** — {}; evidence: {}".format(
                source, target, label, evidence
            ))
    else:
        lines.append("No communication relationship was detected.")
    lines.extend([
        "",
        "## Not established by this analysis",
        "",
        "Deployment topology, runtime behavior outside the inspected repositories, "
        "authentication/authorization, and persistence are not determined by the "
        "current extractor. Treat them as unknown until additional evidence is added.",
        "",
        "## Diagram",
        "",
        "See `architecture.mmd` for the Mermaid source.",
        "",
    ])
    return "\n".join(lines)


def generate_report(repositories: Sequence[Path], output_directory: Path) -> Dict[str, Path]:
    output_directory = output_directory.expanduser().resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    architecture = analyze_repositories(repositories)
    json_path = output_directory / "architecture.json"
    markdown_path = output_directory / "architecture.md"
    mermaid_path = output_directory / "architecture.mmd"
    json_path.write_text(json.dumps(architecture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(architecture), encoding="utf-8")
    mermaid_path.write_text(render_mermaid(architecture), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path, "mermaid": mermaid_path}
