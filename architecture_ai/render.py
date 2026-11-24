"""Render static findings as a cited Markdown report and Mermaid diagram."""

import json
import re
import html
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
    for repo in repositories:
        for index, fact in enumerate(repo["facts"]):
            if fact["kind"] == "calls_endpoint" and not fact["details"].get("target"):
                details = fact["details"]
                unknown = "{}_unknown_{}".format(_service_id(repo["service"]), index)
                lines.append('    {}["Destino não identificado"]'.format(unknown))
                lines.append('    {} -. "REST {} (destino não identificado)" .-> {}'.format(
                    _service_id(repo["service"]), details.get("method", "?"), unknown))
    if len(lines) == 1:
        lines.append("    no_relationships[\"No communication relationships detected\"]")
    return "\n".join(lines) + "\n"


def render_svg(architecture: Dict[str, object]) -> str:
    """Create an offline visual overview with all repositories and observed links."""
    repos = architecture["repositories"]
    width, row = 1100, 180
    height = max(260, 100 + len(repos) * row)
    positions = {repo["service"]: (40, 70 + i * row) for i, repo in enumerate(repos)}
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" viewBox="0 0 {} {}">'.format(width, height, width, height),
             '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#52769a"/></marker></defs>',
             '<rect width="100%" height="100%" fill="#f6f9fc"/>',
             '<text x="40" y="35" font-family="Arial" font-size="22" font-weight="bold" fill="#183659">Visão da arquitetura — análise estática</text>']
    edges = _communication_edges(repos)
    for repo in repos:
        name = repo["service"]
        x, y = positions[name]
        facts = repo["facts"]
        summary = []
        for fact in facts:
            d = fact["details"]
            if fact["kind"] == "exposes_endpoint": summary.append('REST {} {}'.format(d['method'], d['path']))
            elif fact["kind"] == "publishes_to": summary.append('Publica Kafka: ' + d['topic'])
            elif fact["kind"] == "consumes_from": summary.append('Consome Kafka: ' + d['topic'])
            elif fact["kind"] == "calls_endpoint": summary.append('Chama REST: ' + d.get('path', 'desconhecido'))
        parts.append('<rect x="{}" y="{}" width="400" height="140" rx="12" fill="white" stroke="#6b8baa"/>'.format(x,y))
        parts.append('<text x="{}" y="{}" font-family="Arial" font-size="17" font-weight="bold" fill="#183659">{}</text>'.format(x+15,y+27,html.escape(name)))
        for j, entry in enumerate((summary or ['Responsabilidade não identificada'])[:4]):
            parts.append('<text x="{}" y="{}" font-family="Arial" font-size="13" fill="#344b60">{}</text>'.format(x+15,y+52+j*21,html.escape(entry[:55])))
        outgoing = [e for e in edges if e[0] == name]
        unresolved = [f for f in facts if f["kind"] == "calls_endpoint" and not f["details"].get("target")]
        for j, edge in enumerate(outgoing):
            target, label = edge[1], edge[2]
            target_y = positions[target][1] + 110
            route_x = 470 + j * 24
            dash = ' stroke-dasharray="6 4"' if edge[3] == 'inferred' else ''
            parts.append('<path d="M 440 {} L {} {} L {} {} L 440 {}" fill="none" stroke="#52769a" stroke-width="2"{} marker-end="url(#arrow)"/>'.format(y+45+j*25,route_x,y+45+j*25,route_x,target_y,target_y,dash))
            parts.append('<text x="500" y="{}" font-family="Arial" font-size="14" fill="#183659">→ {}: {}</text>'.format(y+50+j*25,html.escape(target),html.escape(label)))
        for j, fact in enumerate(unresolved):
            parts.append('<text x="500" y="{}" font-family="Arial" font-size="14" fill="#8c5d20">→ REST {}: destino não identificado</text>'.format(y+50+(len(outgoing)+j)*25,html.escape(fact['details'].get('path','?'))))
        if not outgoing and not unresolved:
            parts.append('<text x="500" y="{}" font-family="Arial" font-size="14" fill="#64798c">Nenhuma ligação de saída identificada</text>'.format(y+50))
    parts.append('</svg>')
    return '\n'.join(parts)


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
    svg_path = output_directory / "architecture.svg"
    json_path.write_text(json.dumps(architecture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(architecture), encoding="utf-8")
    mermaid_path.write_text(render_mermaid(architecture), encoding="utf-8")
    svg_path.write_text(render_svg(architecture), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path, "mermaid": mermaid_path, "svg": svg_path}
