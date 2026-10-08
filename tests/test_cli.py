import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from wallvision.cli import main
from wallvision.report import write_report


class CliTests(unittest.TestCase):
    def test_demo_calibrate_and_labeled_analysis(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d)
            self.assertEqual(main(['demo', '--output', d]), 0)
            self.assertEqual(main(['calibrate', str(output / 'baseline.jsonl'),
                                   '--model', str(output / 'model.json')]), 0)
            self.assertEqual(main(['analyze', str(output / 'test.jsonl'), '--model', str(output / 'model.json'),
                                   '--labels', str(output / 'labels.json'), '--output', str(output / 'analysis.json'),
                                   '--html', str(output / 'analysis.html')]), 0)
            result = json.loads((output / 'analysis.json').read_text())
            self.assertEqual(result['metadata']['source'], 'synthetic')
            self.assertGreater(result['metrics']['motion_recall_on_valid'], .95)
            self.assertEqual(main(['analyze', str(output / 'baseline.jsonl'), '--model', str(output / 'model.json'),
                                   '--labels', str(output / 'labels.json'), '--output', str(output / 'bad.json')]), 2)

    def test_report_escapes_input(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'report.html'
            write_report(path, [{'name': '</script><script>alert(1)</script>', 'windows': []}],
                         '<script>bad</script>', '<b>bad</b>')
            value = path.read_text()
            self.assertNotIn('</script><script>alert', value)
            self.assertIn('&lt;script&gt;bad', value)

    def test_bad_input_returns_actionable_error(self):
        result = subprocess.run([sys.executable, '-m', 'wallvision', 'analyze', '/nonexistent',
                                 '--model', '/nonexistent', '--output', '/nonexistent'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Error:', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
