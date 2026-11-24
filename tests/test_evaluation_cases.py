import json
import unittest
from pathlib import Path


class EvaluationCaseTests(unittest.TestCase):
    def test_required_case_count_and_security_categories(self):
        fixture_path = Path(__file__).parents[1] / "evaluation" / "cases.json"
        cases = json.loads(fixture_path.read_text(encoding="utf-8"))["cases"]
        categories = {category for case in cases for category in case["category"]}

        self.assertGreaterEqual(len(cases), 15)
        self.assertTrue({"direct-injection", "indirect-injection", "leakage", "lgpd", "bias"}.issubset(categories))


if __name__ == "__main__":
    unittest.main()
