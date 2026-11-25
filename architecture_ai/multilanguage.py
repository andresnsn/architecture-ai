"""Conservative, line-cited observations for common frameworks and IaC."""
import re
from pathlib import Path

from architecture_ai.retrieval import _iter_source_files

ROUTES = [
    (re.compile(r'@(Get|Post|Put|Delete|Patch)Mapping\s*\(\s*["\']([^"\']+)["\']', re.I), 'spring'),
    (re.compile(r'\b(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', re.I), 'node'),
    (re.compile(r'@(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', re.I), 'python'),
]
TERRAFORM = re.compile(r'^\s*(resource|data)\s+"([^"]+)"\s+"([^"]+)"')


def extract_additional(repository: Path, service: str):
    facts = []
    for path in _iter_source_files(repository):
        if path.suffix.lower() not in {'.java', '.kt', '.js', '.ts', '.py', '.tf'}:
            continue
        try:
            lines = path.read_text(encoding='utf-8').splitlines()
        except (OSError, UnicodeError):
            continue
        for number, line in enumerate(lines, 1):
            evidence = [{'file': path.relative_to(repository).as_posix(), 'line': number, 'snippet': line.strip()}]
            # A Spring class-level prefix can change the full path: label it as an observed fragment.
            for regex, framework in ROUTES:
                allowed = {'spring': {'.java', '.kt'}, 'node': {'.js', '.ts'}, 'python': {'.py'}}
                match = regex.search(line) if path.suffix.lower() in allowed[framework] else None
                if match:
                    facts.append({'kind': 'exposes_endpoint', 'service': service, 'protocol': 'HTTP',
                                  'details': {'method': match.group(1).upper(), 'path': match.group(2), 'framework': framework, 'path_scope': 'fragment'},
                                  'certainty': 'inferred', 'evidence': evidence})
                    break
            if path.suffix.lower() == '.tf':
                match = TERRAFORM.search(line)
                if match:
                    facts.append({'kind': 'declares_resource', 'service': service, 'protocol': 'Terraform',
                                  'details': {'declaration': match.group(1), 'type': match.group(2), 'name': match.group(3)},
                                  'certainty': 'confirmed', 'evidence': evidence})
    return facts
