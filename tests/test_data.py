import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from wallvision.data import import_esp_csv, load_recording, save_recording
from wallvision.synthetic import generate


class DataTests(unittest.TestCase):
    def test_jsonl_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'data.jsonl'
            original = generate(duration=1)
            save_recording(original, path)
            loaded = load_recording(path)
            np.testing.assert_array_equal(loaded.csi, original.csi)
            np.testing.assert_array_equal(loaded.timestamps, original.timestamps)
            self.assertEqual(loaded.metadata, original.metadata)

    def csv(self, path, stamps=(1000000, 1020000), channel_change=False):
        values = [item for _ in range(64) for item in (3, 4)]
        lines = ['type,id,mac,channel,local_timestamp,len,first_word,data']
        for i, stamp in enumerate(stamps):
            channel = 6 if channel_change and i else 1
            lines.append(f'CSI_DATA,{i},aa:bb:cc:dd:ee:ff,{channel},{stamp},128,1,"{json.dumps(values)}"')
        path.write_text('\n'.join(lines))

    def test_esp_imaginary_real_and_mask(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'esp.csv'
            self.csv(path)
            recording = import_esp_csv(path)
            self.assertEqual(recording.csi[0, 2], 4 + 3j)
            self.assertTrue((recording.csi[:, :2] == 0).all())
            self.assertNotIn('aa:bb', json.dumps(recording.metadata))
            np.testing.assert_allclose(recording.timestamps, [1, 1.02])

    def test_clock_wrap_is_unwrapped(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'esp.csv'
            self.csv(path, (2**32 - 10000, 10000))
            recording = import_esp_csv(path)
            self.assertAlmostEqual(np.diff(recording.timestamps)[0], .02)

    def test_clock_reboot_and_channel_change_fail(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'esp.csv'
            self.csv(path, (1000000, 1000))
            with self.assertRaises(ValueError):
                import_esp_csv(path)
            self.csv(path, channel_change=True)
            with self.assertRaises(ValueError):
                import_esp_csv(path)

    def test_requires_header(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'esp.csv'
            path.write_text('CSI_DATA,1,2,3\n')
            with self.assertRaises(ValueError):
                import_esp_csv(path)
