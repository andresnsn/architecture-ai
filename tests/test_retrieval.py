import tempfile
import unittest
from pathlib import Path

from architecture_ai.retrieval import index_repositories, search_evidence


class RetrievalTests(unittest.TestCase):
    def test_blank_first_line_does_not_shift_citations(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository = root / "repo"
            repository.mkdir()
            (repository / "main.go").write_text('\nconst topic = "orders.created.v1"\n', encoding="utf-8")
            database = root / "index.sqlite"
            index_repositories([repository], database)
            chunk = search_evidence(database, "orders.created.v1")[0]
            self.assertEqual(chunk["start_line"] + chunk["content"].splitlines().index('const topic = "orders.created.v1"'), 2)

    def test_indexes_source_with_line_citations_and_skips_env_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository = root / "orders-api"
            repository.mkdir()
            source = repository / "main.go"
            source.write_text(
                'package main\nconst topic = "orders.created.v1"\n', encoding="utf-8"
            )
            (repository / ".env").write_text("secretneedle=not-for-index\n", encoding="utf-8")
            database = root / "index.sqlite"

            chunk_count = index_repositories([repository], database)
            results = search_evidence(database, "orders.created.v1")
            secret_results = search_evidence(database, "secretneedle")

            self.assertEqual(chunk_count, 1)
            self.assertTrue(results)
            self.assertEqual(results[0]["repository"], "orders-api")
            self.assertEqual(results[0]["path"], "main.go")
            self.assertEqual(results[0]["start_line"], 1)
            self.assertFalse(secret_results)


if __name__ == "__main__":
    unittest.main()
