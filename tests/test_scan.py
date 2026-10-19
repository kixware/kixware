import unittest
from unittest.mock import patch
from types import SimpleNamespace
import subprocess
import json
from system_scan import normalize_inventory, scan_system

class ScanTests(unittest.TestCase):
    def test_dedicated_vram_above_four_gb_and_multiple_gpus(self):
        raw = {'cpu': 'Ryzen 7', 'ram_bytes': 32*2**30, 'os': 'Windows 11', 'laptop': True,
               'video': [{'name': 'RTX 4070', 'hz': 165}, {'name': 'Integrated', 'hz': 60}]}
        result = normalize_inventory(raw, [{'name': 'RTX 4070', 'vram_bytes': 12*2**30}, {'name': 'Integrated', 'vram_bytes': 512*2**20}])
        self.assertEqual(result['ram'], '32')
        self.assertEqual(result['gpus'][0], {'name': 'RTX 4070', 'vram': '12', 'hz': '165'})
        self.assertEqual(result['gpus'][1]['vram'], '0')
        self.assertTrue(result['laptop'])
    def test_fallback_does_not_trust_truncated_wmi_vram(self):
        result = normalize_inventory({'video': {'name': 'RTX 4090', 'hz': 0, 'AdapterRAM': 4294967295}}, [])
        self.assertEqual(result['gpus'], [{'name': 'RTX 4090', 'vram': '', 'hz': ''}])
        self.assertEqual(result['cpu'], '')
        self.assertEqual(result['ram'], '')
    def test_empty_inventory_and_non_windows(self):
        self.assertEqual(normalize_inventory({}, [])['gpus'], [])
        with patch('system_scan.platform.system', return_value='Linux'):
            with self.assertRaisesRegex(RuntimeError, 'requires Windows'): scan_system()
    def test_windows_scan_collects_read_only_inventory(self):
        data = {'cpu': 'Ryzen 7', 'ram_bytes': 16*2**30, 'video': [{'name': 'RTX 4060', 'hz': 144}]}
        with patch('system_scan.platform.system', return_value='Windows'), patch('system_scan.subprocess.CREATE_NO_WINDOW', 0x08000000, create=True), patch('system_scan.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(data).encode())) as run, patch('system_scan.dxgi_adapters', return_value=[{'name': 'RTX 4060', 'vram_bytes': 8*2**30}]):
            result = scan_system()
        self.assertEqual(result['gpus'][0]['vram'], '8')
        self.assertEqual(result['ram'], '16')
        self.assertEqual(run.call_args.kwargs['timeout'], 35)
        self.assertIn('-NonInteractive', run.call_args.args[0])
        self.assertNotIn('-ExecutionPolicy', run.call_args.args[0])
    def test_failed_or_malformed_windows_inventory(self):
        for process in [SimpleNamespace(returncode=1, stdout=b''), SimpleNamespace(returncode=0, stdout=b'not json')]:
            with patch('system_scan.platform.system', return_value='Windows'), patch('system_scan.subprocess.CREATE_NO_WINDOW', 0, create=True), patch('system_scan.subprocess.run', return_value=process):
                with self.assertRaises(RuntimeError): scan_system()
        with patch('system_scan.platform.system', return_value='Windows'), patch('system_scan.subprocess.CREATE_NO_WINDOW', 0, create=True), patch('system_scan.subprocess.run', side_effect=subprocess.TimeoutExpired('powershell',35)):
            with self.assertRaisesRegex(RuntimeError,'timed out'): scan_system()
    def test_invalid_inventory(self):
        with self.assertRaises(ValueError): normalize_inventory([], [])

if __name__ == '__main__': unittest.main()
