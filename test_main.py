import os
import unittest
from fastapi.testclient import TestClient
import main
from main import app

class TestApp(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        main.data_file = 'test_data.json'
        if os.path.exists(main.data_file):
            os.remove(main.data_file)

    def tearDown(self):
        if os.path.exists(main.data_file):
            os.remove(main.data_file)

    def test_linear_cut_endpoint(self):

        data = {"original_length": 6000, "cut_length": [1500, 1450, 1300, 1150, 1000], "cut_count": [10, 3, 6, 9, 10],
                "blade_thickness": 1,
                "cutting_angle": 45,
                "original_thickness": 25
                }
        response = self.client.post("/linear-cut/", json=data)
        self.assertEqual(response.status_code, 200)
        # Добавьте дополнительные проверки, чтобы убедиться, что результат соответствует ожидаемому

    def test_linear_cut_dynamic_endpoint(self):
        data = {"original_length": 6000, "cut_length": [1500, 1450, 1300, 1150, 1000], "cut_count": [10, 3, 6, 9, 10],
                "blade_thickness": 1,
                "cutting_angle": 45,
                "original_thickness": 25
                }
        response = self.client.post("/linear-cut-dynamic", json=data)
        self.assertEqual(response.status_code, 200)

    def test_linear_cut_multi_endpoint(self):
        data = {"originals_length": [6000, 5000], "cut_length": [1500, 1450, 1300, 1150, 1000], "cut_count": [10, 3, 6, 9, 10],
                "blade_thickness": 1,
                "cutting_angle": 45,
                "original_thickness": 25
                }
        response = self.client.post("/linear-multi-cut", json=data)
        self.assertEqual(response.status_code, 200)

    def test_bivariate_cut_endpoint(self):
        pieces = [(2, 3, 15), (4, 5, 10), (3, 3, 20)]
        material_width = 10
        material_height = 10
        data = {"pieces": pieces, "material_width": material_width, "material_height": material_height}
        response = self.client.post("/bivariate-cut", json=data)
        self.assertEqual(response.status_code, 200)

    def test_history_cut_empty(self):
        response = self.client.get("/history-cut")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_history_cut_returns_newest_first(self):
        data = {"original_length": 6000, "cut_length": [1500], "cut_count": [2],
                "blade_thickness": 1, "cutting_angle": 45, "original_thickness": 25}
        self.client.post("/linear-cut/", json=data)
        self.client.post("/linear-cut/", json=data)
        response = self.client.get("/history-cut")
        self.assertEqual(response.status_code, 200)
        history = response.json()
        self.assertEqual(len(history), 2)
        self.assertGreaterEqual(history[0]['id'], history[1]['id'])
        self.assertEqual(history[0]['data_input']['original_length'], 6000)

if __name__ == '__main__':
    unittest.main()