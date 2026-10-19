import tempfile
import unittest
from pathlib import Path
from engine import TweakManager, recommendations, graphics_recommendations

class Registry:
    def __init__(self, original=None):
        self.value = original or {'exists': False}
        self.fail_write = False
        self.fail_restore = False
    def read(self, *args): return self.value.copy()
    def write(self, path, name, value):
        if self.fail_write: raise OSError('write failed')
        self.value = {'exists': True, 'value': value, 'kind': 4}
    def restore(self, path, name, original):
        if self.fail_restore: raise OSError('restore failed')
        self.value = original.copy()

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'backup.json'
    def test_restore_original_after_restart(self):
        original = {'exists': True, 'value': 7, 'kind': 4}
        backend = Registry(original)
        TweakManager(backend, self.path).apply('game_mode')
        manager = TweakManager(backend, self.path)
        with self.assertRaises(ValueError): manager.apply('game_mode')
        manager.undo('game_mode')
        self.assertEqual(backend.value, original)
        self.assertEqual(TweakManager(backend, self.path).state, {})
    def test_absent_value_restored_as_absent(self):
        backend = Registry()
        manager = TweakManager(backend, self.path)
        manager.apply('capture')
        manager.undo('capture')
        self.assertEqual(backend.value, {'exists': False})
    def test_failed_write_keeps_durable_original(self):
        backend = Registry()
        backend.fail_write = True
        manager = TweakManager(backend, self.path)
        with self.assertRaises(OSError): manager.apply('capture')
        restarted = TweakManager(backend, self.path)
        self.assertEqual(restarted.state['capture']['status'], 'pending')
        restarted.undo('capture')
        self.assertEqual(restarted.state, {})
    def test_failed_undo_retains_backup(self):
        backend = Registry()
        manager = TweakManager(backend, self.path)
        manager.apply('mouse')
        backend.fail_restore = True
        with self.assertRaises(OSError): manager.undo('mouse')
        self.assertIn('mouse', TweakManager(backend, self.path).state)
    def test_recommendations_use_hardware(self):
        rows = recommendations('Ryzen 5', 'NVIDIA RTX 3060', '8', '4', '144', True)
        titles = [r[0] for r in rows]
        self.assertIn('NVIDIA Reflex', titles)
        self.assertIn('Memory pressure', titles)
        self.assertIn('Laptop power', titles)
        self.assertIn('Low/Medium', dict((r[0], r[1]) for r in rows)['Texture quality'])
        other = recommendations('Ryzen 7', 'AMD Radeon', 32, 16, 240, False)
        self.assertNotIn('NVIDIA Reflex', [r[0] for r in other])
    def test_graphics_recommendations_match_gpu(self):
        rtx = graphics_recommendations('GeForce RTX 4070')
        self.assertTrue(any('DLSS (RTX only' in row[0] for row in rtx))
        self.assertTrue(any('Low Latency Mode' in row[0] for row in rtx))
        gtx = graphics_recommendations('NVIDIA GTX 1660')
        self.assertFalse(any('DLSS (RTX only' in row[0] for row in gtx))
        amd = graphics_recommendations('AMD Radeon RX 7800 XT')
        self.assertTrue(any('Anti-aliasing' in row[0] for row in amd))
        self.assertFalse(any('NVIDIA Control Panel' in row[0] for row in amd))
        with self.assertRaises(ValueError): graphics_recommendations('')

    def test_invalid_specs(self):
        for args in [('', 'GPU', 16, 8, 144, False), ('CPU', 'GPU', 'bad', 8, 144, False), ('CPU', 'GPU', 16, 8, 0, False)]:
            with self.assertRaises(ValueError): recommendations(*args)

if __name__ == '__main__': unittest.main()
