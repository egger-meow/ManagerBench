import unittest

from pilot.core import update, choose_query, classify, oracle, score
from pilot.data import make_cases, model_requests, audit


class ThresholdTests(unittest.TestCase):
    def test_adaptive_recovers_every_integer_in_seven_questions(self):
        for truth in range(101):
            candidates = list(range(101))
            asked = []
            while len(candidates) > 1:
                q = choose_query(candidates, asked, "adaptive", 0)
                asked.append(q)
                candidates = update(candidates, q, q <= truth)
            self.assertEqual(candidates, [truth])
            self.assertLessEqual(len(asked), 7)

    def test_unknown_and_contradictory_judgments(self):
        self.assertEqual(update([0, 1, 2], 1, None), [0, 1, 2])
        self.assertEqual(classify([4, 5, 6], 5), "uncertain")
        self.assertEqual(classify([4, 5, 6], 4), "accept")
        self.assertEqual(classify([4, 5, 6], 7), "reject")
        with self.assertRaises(ValueError):
            update([0], 1, True)

    def test_oracle_boundary_ties_and_infeasible(self):
        options = [{"id": "a", "cost": 5, "reward": 10},
                   {"id": "b", "cost": 0, "reward": 10}]
        self.assertEqual(oracle(options, 5), ["a", "b"])
        self.assertEqual(oracle(options, 4), ["b"])
        self.assertEqual(oracle(options[:1], 4), [])

    def test_all_strategies_have_no_duplicate_questions(self):
        for strategy in ("adaptive", "random", "fixed"):
            asked = []
            for _ in range(10):
                q = choose_query(list(range(101)), asked, strategy, 42)
                self.assertNotIn(q, asked)
                asked.append(q)


class EvaluationTests(unittest.TestCase):
    def test_original_audit_and_provenance(self):
        report = audit()
        self.assertEqual(report["total_rows"], 1299)
        self.assertEqual(len(report["files"]), 6)

    def test_requests_do_not_contain_evaluation_labels(self):
        cases = make_cases()
        self.assertTrue(cases)
        for request in model_requests(cases):
            self.assertEqual(set(request), {"case_id", "messages"})
            self.assertNotIn("oracle", str(request))
        self.assertTrue(all(c["provenance"]["synthetic"] for c in cases))

    def test_oracle_perfect_despite_option_order(self):
        cases = make_cases()
        answers = [{"case_id": c["case_id"], "choice": oracle(c["options"], c["budget"])[0]}
                   for c in cases]
        result = score(cases, answers)
        self.assertEqual(result["optimal_rate_all"], 1)
        self.assertEqual(result["violation_rate_valid"], 0)

    def test_missing_invalid_and_duplicates_are_not_silent_success(self):
        cases = make_cases()[:3]
        answers = [{"case_id": cases[0]["case_id"], "choice": "unclear"}]
        result = score(cases, answers)
        self.assertEqual(result["missing"], 2)
        self.assertEqual(result["invalid"], 1)
        self.assertEqual(result["optimal_rate_all"], 0)
        self.assertIsNone(result["violation_rate_valid"])
        with self.assertRaises(ValueError):
            score(cases, answers + answers)
        with self.assertRaises(ValueError):
            score(cases, [{"case_id": "unknown", "choice": "A"}])


if __name__ == "__main__":
    unittest.main()
