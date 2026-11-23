"""Local, line-cited retrieval over source and configuration files."""

import re
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


SUPPORTED_SUFFIXES = {
    ".go", ".py", ".java", ".js", ".ts", ".tsx", ".jsx", ".md", ".txt",
    ".yaml", ".yml", ".json", ".toml", ".properties", ".xml", ".sql",
    ".sh", ".tf", ".proto",
}
IGNORED_DIRS = {
    ".git", ".architecture", ".venv", "__pycache__", "vendor", "node_modules",
    "target", "dist",
}
MAX_FILE_BYTES = 1_000_000
CHUNK_LINES = 40
CHUNK_OVERLAP = 5


def _iter_source_files(repository: Path) -> Iterable[Path]:
    for path in sorted(repository.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        relative_parts = path.relative_to(repository).parts
        if any(part in IGNORED_DIRS for part in relative_parts):
            continue
        # Real .env files can contain credentials; even dotenv examples are
        # omitted from the first version to keep the rule simple and safe.
        if path.name == ".env" or path.name.startswith(".env."):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield path


def _chunks(lines: Sequence[str]) -> Iterable[tuple[int, int, str]]:
    if not lines:
        return
    step = CHUNK_LINES - CHUNK_OVERLAP
    for start_index in range(0, len(lines), step):
        chunk = lines[start_index:start_index + CHUNK_LINES]
        content = "\n".join(chunk).strip()
        if content:
            yield start_index + 1, start_index + len(chunk), content


def index_repositories(repositories: Sequence[Path], database: Path) -> int:
    """Rebuild an FTS5 index. Returns the number of indexed chunks."""
    database = database.expanduser().resolve()
    database.parent.mkdir(parents=True, exist_ok=True)
    try:
        connection = sqlite3.connect(str(database))
        connection.execute("DROP TABLE IF EXISTS evidence")
        connection.execute(
            "CREATE VIRTUAL TABLE evidence USING fts5("
            "repository UNINDEXED, path UNINDEXED, start_line UNINDEXED, "
            "end_line UNINDEXED, content, tokenize='unicode61')"
        )
    except sqlite3.OperationalError as error:
        raise RuntimeError("SQLite FTS5 is unavailable in this Python build") from error

    count = 0
    try:
        for repository_path in repositories:
            repository = repository_path.expanduser().resolve()
            if not repository.is_dir():
                raise ValueError("Not a directory: {}".format(repository))
            for path in _iter_source_files(repository):
                try:
                    lines = path.read_text(encoding="utf-8").splitlines()
                except (OSError, UnicodeDecodeError):
                    continue
                relative_path = path.relative_to(repository).as_posix()
                for start_line, end_line, content in _chunks(lines):
                    connection.execute(
                        "INSERT INTO evidence(repository,path,start_line,end_line,content) "
                        "VALUES(?,?,?,?,?)",
                        (repository.name, relative_path, start_line, end_line, content),
                    )
                    count += 1
        connection.commit()
    finally:
        connection.close()
    return count


def search_evidence(database: Path, query: str, limit: int = 5) -> List[Dict[str, object]]:
    """Return matching chunks with repository and line-range citations."""
    tokens = re.findall(r"[A-Za-z0-9_]+", query)
    if not tokens:
        return []
    fts_query = " OR ".join('"{}"'.format(token.replace('"', '')) for token in tokens)
    connection = sqlite3.connect(str(database.expanduser().resolve()))
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT repository,path,start_line,end_line,content,bm25(evidence) AS rank "
            "FROM evidence WHERE content MATCH ? ORDER BY rank LIMIT ?",
            (fts_query, max(1, limit)),
        ).fetchall()
    finally:
        connection.close()
    return [
        {
            "repository": row["repository"],
            "path": row["path"],
            "start_line": int(row["start_line"]),
            "end_line": int(row["end_line"]),
            "content": row["content"],
        }
        for row in rows
    ]
