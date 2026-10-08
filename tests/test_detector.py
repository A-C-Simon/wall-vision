import unittest

import numpy as np

from wallvision.data import Recording
from wallvision.detector import Config, analyze, calibrate
from wallvision.synthetic import generate


class DetectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = calibrate(generate(seed=10, duration=30))

    def test_independent_still_and_motion(self):
        rows = analyze(generate(seed=20, intervals=[(10, 20), (30, 40)]), self.model)
        motion = [r for r in rows if (10 <= r['start'] and r['end'] < 20)
                  or (30 <= r['start'] and r['end'] < 40)]
        still = [r for r in rows if r['end'] < 10 or (r['start'] >= 20 and r['end'] < 30)]
        self.assertGreater(sum(r['state'] == 'motion' for r in motion) / len(motion), .95)
        self.assertLess(sum(r['state'] == 'motion' for r in still) / len(still), .05)

    def test_common_gain_and_random_packet_phase(self):
        rows = analyze(generate(seed=21, gain=True), self.model)
        self.assertTrue(all(r['state'] == 'still' for r in rows))

    def test_gap_does_not_become_still(self):
        recording = generate(seed=22)
        keep = ~((recording.timestamps > 15) & (recording.timestamps < 16))
        recording = Recording(recording.timestamps[keep], recording.csi[keep], recording.metadata)
        rows = analyze(recording, self.model)
        gap = [r for r in rows if r['start'] <= 15 and r['end'] >= 16]
        self.assertTrue(gap)
        self.assertTrue(all(r['state'] == 'unknown' and r['quality'] == 'packet_gap' for r in gap))

    def test_low_input_rate_abstains(self):
        rows = analyze(generate(rate=10), self.model)
        self.assertTrue(all(r['state'] == 'unknown' for r in rows))

    def test_missing_subcarriers_abstain(self):
        recording = generate()
        recording.csi[500:1000, 5:20] = 0
        rows = analyze(recording, self.model)
        self.assertTrue(any(r['quality'] == 'missing_subcarriers' for r in rows))

    def test_reject_bad_baseline(self):
        for recording in (generate(duration=5), generate(rate=10)):
            with self.assertRaises(ValueError):
                calibrate(recording)

    def test_reject_geometry_and_source_mismatch(self):
        recording = generate()
        recording.metadata['source'] = 'measured'
        with self.assertRaises(ValueError):
            analyze(recording, self.model)

    def test_reject_nonmonotonic_and_nan(self):
        recording = generate()
        t = recording.timestamps.copy()
        t[5] = t[4]
        with self.assertRaises(ValueError):
            Recording(t, recording.csi, recording.metadata)
        h = recording.csi.copy()
        h[0, 5] = np.nan
        with self.assertRaises(ValueError):
            Recording(recording.timestamps, h, recording.metadata)

    def test_config_rejects_aliasing(self):
        with self.assertRaises(ValueError):
            Config(min_rate=10)


if __name__ == '__main__':
    unittest.main()
