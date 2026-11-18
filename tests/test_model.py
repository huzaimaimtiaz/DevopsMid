"""Checks run by Jenkins after train.py."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import app  # noqa: E402

CONFIG = json.loads((ROOT / 'config.json').read_text())
DATA = ROOT / 'dataset' / 'train.csv'
METRICS = ROOT / 'artifacts' / 'metrics.json'


class DatasetTests(unittest.TestCase):
    def test_columns_and_labels(self):
        df = pd.read_csv(DATA)
        for col in CONFIG['features'] + ['label']:
            self.assertIn(col, df.columns)
        self.assertGreaterEqual(len(df), 100)
        self.assertEqual(set(df['label'].unique()), {0, 1})


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metrics = json.loads(METRICS.read_text())

    def test_metrics_fields(self):
        for key in ['student_id', 'accuracy', 'training_rows', 'model_version', 'git_sha']:
            self.assertIn(key, self.metrics)
        self.assertEqual(self.metrics['student_id'], CONFIG['student_id'])

    def test_model_trained_on_latest_data(self):
        raw = DATA.read_bytes()
        self.assertEqual(self.metrics['training_rows'], len(pd.read_csv(DATA)))
        self.assertEqual(self.metrics['model_version'], hashlib.sha256(raw).hexdigest()[:12])

    def test_accuracy_is_reasonable(self):
        self.assertGreaterEqual(self.metrics['accuracy'], 0.6)
        self.assertLessEqual(self.metrics['accuracy'], 1.0)

    def test_metrics_endpoint(self):
        self.assertEqual(app.metrics()['model_version'], self.metrics['model_version'])

    def test_predict_endpoint(self):
        features = CONFIG['features']
        records = [{f: 0.5 for f in features}, {f: -1.0 for f in features}, {features[0]: None}]
        out = app.predict(app.PredictionRequest(records=records))
        self.assertEqual(len(out['predictions']), 3)
        self.assertTrue(all(p in (0, 1) for p in out['predictions']))
        self.assertTrue(all(0.0 <= p <= 1.0 for p in out['probabilities']))


if __name__ == '__main__':
    unittest.main()
