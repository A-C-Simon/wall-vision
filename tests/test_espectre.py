import tempfile
import unittest
from pathlib import Path

import numpy as np

from wallvision.data import import_espectre_npz


class EspectreTests(unittest.TestCase):
    def capture(self, path, **overrides):
        fields = dict(format_version='1.2', csi_data=np.tile(np.array([3, 4], dtype=np.int8), (3, 64)),
                      wifi_rx_ts_us=np.array([100, 20100, 40100], dtype=np.uint32),
                      phy_mode=np.array(['ht'] * 3), ltf_type=np.array(['ht-ltf'] * 3),
                      channel_width=np.array(['20'] * 3), channel=np.array([4] * 3),
                      device_id=np.uint64(123456), chip='esp32', label='motion',
                      endpoint='http://private.invalid')
        fields.update(overrides)
        np.savez(path, **fields)

    def test_preserves_receiver_clock_and_removes_endpoint(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'capture.npz'
            self.capture(path)
            recording = import_espectre_npz(path)
            np.testing.assert_allclose(recording.timestamps, [0, .02, .04])
            self.assertEqual(recording.csi[0, 2], 4 + 3j)
            self.assertNotIn('endpoint', recording.metadata)
            self.assertNotIn('123456', recording.metadata['link_id'])

    def test_requires_real_timestamps_and_constant_radio_format(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'capture.npz'
            for overrides in (dict(channel=np.array([4, 5, 4])),
                              dict(wifi_rx_ts_us=np.array([100, 200, 150], dtype=np.uint32)),
                              dict(ltf_type=np.array(['ht-ltf', 'lltf', 'ht-ltf']))):
                self.capture(path, **overrides)
                with self.assertRaises(ValueError):
                    import_espectre_npz(path)

    def test_does_not_unpickle_object_arrays(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'capture.npz'
            self.capture(path, csi_data=np.array([{'bad': 'object'}], dtype=object))
            with self.assertRaises(ValueError):
                import_espectre_npz(path)
