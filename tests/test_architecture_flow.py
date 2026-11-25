import tempfile
import unittest
from pathlib import Path
from architecture_ai.extractor import analyze_repositories
from architecture_ai.retrieval import index_repositories, search_evidence
from architecture_ai.visual import build_visual
from architecture_ai.scope import classify_question


class ArchitectureFlowTests(unittest.TestCase):
    def test_short_ambiguous_question_without_history_requests_clarification(self):
        self.assertEqual(classify_question('Como isso funciona?'), 'unclear')

    def test_multilanguage_facts_and_structure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'mixed'; root.mkdir()
            (root / 'Api.java').write_text('@GetMapping("/orders")\n', encoding='utf-8')
            (root / 'server.js').write_text('app.post("/books", handler)\n', encoding='utf-8')
            (root / 'main.tf').write_text('resource "aws_sqs_queue" "orders" {\n}\n', encoding='utf-8')
            (root / 'app.py').write_text('@app.get("/stock")\ndef stock():\n    return "ok"\n', encoding='utf-8')
            facts = analyze_repositories([root])['repositories'][0]['facts']
            routes = {fact['details']['path'] for fact in facts if fact['kind'] == 'exposes_endpoint'}
            self.assertEqual(routes, {'/orders', '/books', '/stock'})
            self.assertTrue(any(f['kind'] == 'declares_resource' and f['details']['type'] == 'aws_sqs_queue' for f in facts))
            db = root.parent/'evidence.sqlite'; index_repositories([root], db)
            chunks = search_evidence(db, 'stock', 10)
            self.assertTrue(any('@app.get' in c['content'] and 'return "ok"' in c['content'] for c in chunks))

    def test_diagram_keeps_isolated_and_excludes_uncited_edges(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); first=root/'a'; second=root/'b'; first.mkdir(); second.mkdir()
            result={'components':[], 'relationships':[{'source':'a','target':'b','evidence':[], 'protocol':'REST','certainty':'confirmed'}], 'unknowns':[]}
            output = root/'result.html'; build_visual(result, [first,second], [], output)
            text = output.read_text(encoding='utf-8')
            self.assertIn('"name": "a"', text); self.assertIn('"name": "b"', text)
            self.assertIn('"relations": []', text)

    def test_untrusted_repository_name_is_not_executable_html(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); repo=root/'<img src=x onerror=alert(1)>'; repo.mkdir(parents=True)
            output=root/'view.html'; build_visual({'components': [], 'relationships': [], 'unknowns': []}, [repo], [], output)
            self.assertNotIn('<img src=x onerror=alert(1)>', output.read_text(encoding='utf-8'))

if __name__ == '__main__': unittest.main()
