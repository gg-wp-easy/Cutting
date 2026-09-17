import tempfile
from functools import lru_cache
from itertools import product
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from optimizer import optimize
from main import app


class OptimizerTests(unittest.TestCase):
    def test_global_optimum(self):
        result = optimize([10], [6, 4, 3], [2, 2, 2])
        self.assertEqual(result['summary']['stock_count'], 3)
        self.assertEqual(result['summary']['total_remainder'], 4)
        self.assertEqual([sum(row[i] for row in result['maps']) for i in range(3)], [2, 2, 2])

    def test_small_orders_against_exhaustive_search(self):
        lengths, stocks = [3, 4], [7, 10]
        @lru_cache(None)
        def best(counts):
            if not any(counts):
                return 0
            candidates = []
            for row in product(*(range(n + 1) for n in counts)):
                if not any(row):
                    continue
                used = sum(n * size for n, size in zip(row, lengths))
                for stock in stocks:
                    if used <= stock:
                        candidates.append(stock + best(tuple(n - q for n, q in zip(counts, row))))
            return min(candidates)
        for counts in product(range(1, 4), repeat=2):
            result = optimize(stocks, lengths, list(counts))
            self.assertEqual(result['summary']['total_stock'], best(counts))

    def test_fractional_kerf(self):
        result = optimize([100], [50], [2], .5)
        self.assertEqual(result['maps'], [[1, 49.5], [1, 49.5]])

    def test_multiple_stocks(self):
        result = optimize([100, 60], [60], [2])
        self.assertEqual(result['stock_lengths'], [60, 60])
        self.assertEqual(result['summary']['total_remainder'], 0)

    def test_repeated_patterns_and_exact_fit(self):
        result = optimize([100], [25], [20])
        self.assertEqual(result['maps'], [[4, 0]] * 5)

    def test_angle_and_input_unchanged(self):
        lengths = [100]
        result = optimize([200], lengths, [2], .25, 45, 10)
        self.assertEqual(lengths, [100])
        self.assertEqual(result['result_maps'], [[100, 100, 39.5]])

    def test_invalid(self):
        for args in [([100], [101], [1]), ([100], [10], [0]),
                     ([100], [0], [1]), ([], [1], [1]), ([100], [10], [-1]),
                     ([100], [100], [1], .1)]:
            with self.assertRaises(ValueError):
                optimize(*args)

    def test_endpoints(self):
        payload = dict(original_length=100, cut_length=[25], cut_count=[12],
                       blade_thickness=0, cutting_angle=0, original_thickness=0)
        client = TestClient(app)
        with tempfile.TemporaryDirectory() as folder, patch('main.data_file', folder + '/history.json'):
            for endpoint in ['/linear-cut/', '/linear-cut-dynamic', '/linear-multi-cut']:
                response = client.post(endpoint, json={**payload, 'originals_length': [100, 75]})
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertEqual(sum(row[0] for row in result['maps']), 12)
                self.assertEqual(len(result['maps']), len(result['stock_lengths']))
            response = client.post('/linear-cut/', json={**payload, 'cut_length': [101]})
            self.assertEqual(response.status_code, 422)

if __name__ == '__main__':
    unittest.main()
