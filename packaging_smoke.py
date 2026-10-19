"""Packaged smoke test: Tk UI and an isolated, temporary HKCU registry key."""
import json
import platform
from pathlib import Path
import sys
import tempfile
import uuid


def run(output):
    import tkinter as tk
    import winreg
    from engine import TWEAKS, TweakManager, WindowsRegistry
    from kixware import App
    from system_scan import normalize_inventory

    report = {'frozen': bool(getattr(sys, 'frozen', False)), 'platform': platform.system(), 'checks': []}
    probe_path = 'Software\\KixWare\\SmokeTest_' + uuid.uuid4().hex
    original_tweak = TWEAKS['game_mode']
    root = None
    try:
        # Exercise the shipped Windows backend without touching gaming settings.
        backend = WindowsRegistry()
        TWEAKS['game_mode'] = dict(original_tweak, path=probe_path, name='Probe')
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / 'backup.json'
            manager = TweakManager(backend, state)
            manager.apply('game_mode')
            assert backend.read(probe_path, 'Probe')['value'] == 1
            manager = TweakManager(backend, state)
            manager.undo('game_mode')
            assert backend.read(probe_path, 'Probe') == {'exists': False}
            backend.write(probe_path, 'Probe', 'original')
            manager.apply('game_mode')
            TweakManager(backend, state).undo('game_mode')
            assert backend.read(probe_path, 'Probe')['value'] == 'original'
        report['checks'].append('Windows registry apply, persisted backup, undo: absent and existing values')
        TWEAKS['game_mode'] = original_tweak
        root = tk.Tk()
        app = App(root)
        assert app.manager is not None, app.error
        for key, value in {'CPU model': 'Ryzen 5 5600', 'GPU model': 'NVIDIA RTX 3060', 'RAM (GB)': '16', 'GPU VRAM (GB)': '12', 'Monitor refresh (Hz)': '144'}.items():
            app.fields[key].set(value)
        app.generate()
        text = app.output.get('1.0', 'end')
        assert 'NVIDIA REFLEX' in text and '144 Hz' in text
        graphics = app.graphics_output.get('1.0', 'end')
        assert 'ANTI-ALIASING' in graphics and 'DLSS' in graphics and 'LOW LATENCY MODE' in graphics
        for tab in range(4):
            app.notebook.select(tab)
            root.update()
        report['checks'].append('Tk window, all four tabs, hardware form and generated recommendations')
        fixture = normalize_inventory({'cpu': 'Detected CPU', 'ram_bytes': 32*2**30,
            'os': 'Windows 11 test inventory', 'laptop': True,
            'video': [{'name': 'Integrated', 'hz': 60}, {'name': 'RTX 4070', 'hz': 165}]},
            [{'name': 'Integrated', 'vram_bytes': 256*2**20}, {'name': 'RTX 4070', 'vram_bytes': 12*2**30}])
        before = {key: var.get() for key, var in app.fields.items()}
        dialog = app.show_scan_confirmation(fixture)
        root.update()
        assert {key: var.get() for key, var in app.fields.items()} == before
        dialog.cancel_scan()
        assert {key: var.get() for key, var in app.fields.items()} == before
        dialog = app.show_scan_confirmation(fixture)
        dialog.gpu_selector.current(1)
        dialog.gpu_selector.event_generate('<<ComboboxSelected>>')
        root.update()
        assert dialog.scan_variables['GPU VRAM (GB)'].get() == '12'
        assert dialog.scan_variables['Monitor refresh (Hz)'].get() == '165'
        dialog.scan_variables['CPU model'].set('Corrected CPU')
        dialog.confirm_scan()
        assert app.fields['CPU model'].get() == 'Corrected CPU'
        assert app.fields['GPU model'].get() == 'RTX 4070'
        assert app.laptop.get()
        assert 'NVIDIA REFLEX' in app.output.get('1.0', 'end')
        report['checks'].append('Scan confirmation with fixture inventory: no changes before consent, cancel, GPU selection, correction and confirm')
        report['status'] = 'passed'
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = repr(exc)
        raise
    finally:
        TWEAKS['game_mode'] = original_tweak
        if root is not None:
            root.destroy()
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, probe_path)
        except FileNotFoundError:
            pass
        Path(output).write_text(json.dumps(report, indent=2), encoding='utf-8')
