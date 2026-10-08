import unittest

from wallvision.evaluation import evaluate


class EvaluationTests(unittest.TestCase):
    def test_boundaries_and_unknown_are_explicit(self):
        rows = [{'start': 0, 'end': 2, 'state': 'still'},
                {'start': 1, 'end': 3, 'state': 'motion'},
                {'start': 2, 'end': 4, 'state': 'motion'},
                {'start': 3, 'end': 5, 'state': 'unknown'}]
        result = evaluate(rows, [{'start': 0, 'end': 2, 'label': 'still'},
                                 {'start': 2, 'end': 5, 'label': 'motion'}])
        self.assertEqual(result['excluded'], 1)
        self.assertEqual(result['tn'], 1)
        self.assertEqual(result['tp'], 1)
        self.assertEqual(result['unknown_motion'], 1)
        self.assertEqual(result['motion_recall_on_valid'], 1)
        self.assertEqual(result['motion_recall_including_unknown'], .5)
        self.assertAlmostEqual(result['valid_coverage'], 2 / 3)

    def test_overlapping_labels_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([], [{'start': 0, 'end': 3, 'label': 'still'},
                          {'start': 2, 'end': 4, 'label': 'motion'}])

    def test_empty_denominators_are_not_perfect_scores(self):
        result = evaluate([], [])
        self.assertIsNone(result['motion_recall_on_valid'])
        self.assertIsNone(result['false_positive_rate_on_valid'])
        self.assertIsNone(result['valid_coverage'])
