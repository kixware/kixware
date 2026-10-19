"""Reversible, current-user Windows settings. No game/process modification."""
import json
import os
from pathlib import Path
import platform
import subprocess
from datetime import datetime, timezone

TWEAKS = {
    'game_mode': dict(title='Enable Windows Game Mode', path=r'Software\Microsoft\GameBar', name='AutoGameModeEnabled', value=1,
        reason='Allows Windows to prioritize the gaming workload. Gains depend on background activity.', impact='Changes Game Mode for all games on this Windows account.'),
    'capture': dict(title='Disable background game capture', path=r'Software\Microsoft\Windows\CurrentVersion\GameDVR', name='AppCaptureEnabled', value=0,
        reason='Can reduce recording overhead when Windows game capture is enabled.', impact='Disables Windows game capture for this account. Other recorders are unaffected.'),
    'mouse': dict(title='Disable pointer acceleration', path=r'Control Panel\Mouse', name='MouseSpeed', value='0',
        reason='Makes Windows pointer movement more consistent. Siege raw input may bypass this setting, so this is not an FPS tweak.', impact='Changes desktop pointer behavior; sign out and back in to ensure it takes effect.'),
}

class WindowsRegistry:
    def __init__(self):
        if platform.system() != 'Windows':
            raise RuntimeError('Windows tweaks can only be applied on Windows 10/11.')
        import winreg
        self.reg = winreg

    def read(self, path, name):
        r = self.reg
        try:
            with r.OpenKey(r.HKEY_CURRENT_USER, path) as key:
                value, kind = r.QueryValueEx(key, name)
                return {'exists': True, 'value': value, 'kind': kind}
        except FileNotFoundError:
            return {'exists': False}

    def write(self, path, name, value):
        r = self.reg
        with r.CreateKeyEx(r.HKEY_CURRENT_USER, path, 0, r.KEY_SET_VALUE) as key:
            r.SetValueEx(key, name, 0, r.REG_SZ if isinstance(value, str) else r.REG_DWORD, value)

    def restore(self, path, name, original):
        r = self.reg
        if original['exists']:
            with r.CreateKeyEx(r.HKEY_CURRENT_USER, path, 0, r.KEY_SET_VALUE) as key:
                r.SetValueEx(key, name, 0, original['kind'], original['value'])
        else:
            try:
                with r.OpenKey(r.HKEY_CURRENT_USER, path, 0, r.KEY_SET_VALUE) as key:
                    r.DeleteValue(key, name)
            except FileNotFoundError:
                pass

class TweakManager:
    def __init__(self, backend, state_path):
        self.backend = backend
        self.path = Path(state_path)
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {}
        if not isinstance(self.state, dict) or any(k not in TWEAKS for k in self.state):
            raise ValueError('Invalid backup file. Preserve it and restore a valid backup before continuing.')

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('w') as stream:
            json.dump(self.state, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self.path)

    def apply(self, key):
        tweak = TWEAKS[key]
        if key in self.state:
            raise ValueError('Already applied or pending: undo this tweak before applying it again.')
        original = self.backend.read(tweak['path'], tweak['name'])
        self.state[key] = {'original': original, 'status': 'pending', 'at': datetime.now(timezone.utc).isoformat()}
        self.save()  # Persist original BEFORE mutation, including interrupted/failed writes.
        self.backend.write(tweak['path'], tweak['name'], tweak['value'])
        self.state[key]['status'] = 'applied'
        self.save()

    def undo(self, key):
        tweak = TWEAKS[key]
        self.backend.restore(tweak['path'], tweak['name'], self.state[key]['original'])
        del self.state[key]
        self.save()


def recommendations(cpu, gpu, ram, vram, hz, laptop):
    if not cpu.strip() or not gpu.strip():
        raise ValueError('Enter your CPU and GPU model names.')
    ram, vram, hz = int(ram), int(vram), int(hz)
    if not (2 <= ram <= 1024 and 0 <= vram <= 128 and 30 <= hz <= 1000):
        raise ValueError('Use RAM 2–1024 GB, VRAM 0–128 GB, and refresh rate 30–1000 Hz.')
    rows = [
        ('Display', f'Select your native resolution and {hz} Hz in Windows and Siege.', 'Avoids accidentally playing below your monitor’s refresh rate.'),
        ('V-Sync', 'For lowest latency, try Off in Siege.', 'Can reduce queued frames; may introduce screen tearing. Compare with your VRR setup.'),
        ('Graphics baseline', 'Start with low shadows/effects and disable motion blur where available.', 'Reduces GPU load. Compare visibility and frame times in the built-in benchmark.'),
        ('Texture quality', 'Start Low; check game requirements and shared-memory pressure.' if vram < 2 else 'Start Low/Medium.' if vram <= 4 else 'Start Medium, then raise if VRAM usage has headroom.', 'VRAM capacity is a starting point, not a prediction of GPU speed.'),
        ('Frame limit', f'Try a sustainable cap near {hz} FPS; lower it if the benchmark cannot maintain it.', 'A stable cap can improve frame pacing; measure before and after.'),
    ]
    if 'nvidia' in gpu.lower() or 'geforce' in gpu.lower() or 'rtx' in gpu.lower() or 'gtx' in gpu.lower():
        rows.append(('NVIDIA Reflex', 'Enable Reflex in Siege if your current game version exposes it.', 'Can reduce render queue latency when GPU bound; compare On versus On + Boost for heat/power.'))
    if ram < 16:
        rows.append(('Memory pressure', 'Close unused browser tabs and launchers; keep the Windows page file system managed.', 'Less memory pressure may reduce paging stutters on systems below 16 GB.'))
    if laptop:
        rows.append(('Laptop power', 'Play plugged in; use the manufacturer’s performance profile and check temperatures.', 'Battery power and thermal limits can restrict sustained performance.'))
    rows.append(('Connection', 'Prefer Ethernet and pause downloads while playing.', 'May reduce local network contention; cannot change server distance or guarantee lower ping.'))
    return rows


def graphics_recommendations(gpu):
    """Manual AA/driver guidance; availability varies by Siege release and GPU."""
    name = gpu.strip().lower()
    if not name:
        raise ValueError('Enter your GPU model on the Your PC tab first.')
    rows = [
        ('In-game • Anti-aliasing',
         'For maximum clarity and a low GPU-cost baseline, try AA Off at native resolution if offered. Compare against T-AA at 100% render scale.',
         'Off preserves sharp edges but causes jagged edges/shimmering. T-AA reduces shimmering but can soften moving detail. Choose by visibility and measured frame times.'),
        ('In-game • Render scaling & sharpness',
         'Start at native resolution / 100% render scale. If GPU bound, compare a lower render scale or a supported upscaler; adjust sharpening moderately.',
         'Lower internal resolution can improve FPS but makes distant targets less clear. Excess sharpening creates halos; it does not restore missing detail.'),
    ]
    nvidia = any(word in name for word in ('nvidia', 'geforce', 'rtx', 'gtx'))
    if nvidia:
        rows.extend([
            ('In-game • NVIDIA Reflex',
             'If available, start with Reflex On. Try On + Boost only if measurements improve latency or frame pacing.',
             'Reflex can reduce the render queue. Boost may keep clocks higher at the cost of heat and power; it is not a guaranteed FPS increase.'),
            ('NVIDIA Control Panel • Low Latency Mode',
             'When using in-game Reflex, leave driver Low Latency Mode Off/default for the Siege program profile.',
             'Reflex manages latency in supported games; stacking driver Ultra does not provide an additive Reflex benefit. Driver behavior also depends on the rendering API.'),
            ('NVIDIA Control Panel • Anti-aliasing',
             'Use Application-controlled AA; leave driver FXAA, MFAA and transparency AA Off/default for Siege.',
             'Let the game control its rendering path. Forced AA can add blur or overhead and may not be supported by the current game renderer.'),
            ('NVIDIA Control Panel • Power management',
             'Start with Normal/default. Test Prefer maximum performance only in the Siege program profile if you observe clock-related stutters.',
             'Maximum performance can increase heat and idle power without raising FPS. Restore Normal if it offers no repeatable benefit.'),
            ('NVIDIA Control Panel • Scaling & filtering',
             'Leave Image Scaling/DSR off for a native-resolution baseline. Keep anisotropic filtering application-controlled and texture filtering at default Quality.',
             'Avoid stacking driver scaling with a game upscaler. Aggressive filtering overrides can reduce distant texture clarity.'),
        ])
        if 'rtx' in name:
            rows.append(('In-game • NVIDIA DLSS (RTX only, if offered)',
                         'Compare native rendering against DLSS Quality when GPU bound. At 1080p, prefer native first if target visibility suffers. For a low-latency baseline, leave frame generation Off if offered.',
                         'DLSS availability depends on the game version and RTX model. Upscaling can help GPU-limited FPS but may soften detail; generated frames are not equivalent to lower input latency.'))
        else:
            rows.append(('In-game • DLSS availability', 'Do not select a DLSS recommendation for a GTX GPU; use the AA and render-scale controls your game exposes.', 'DLSS requires supported RTX hardware and game integration.'))
    else:
        rows.append(('GPU-specific options', 'NVIDIA-only recommendations are hidden for this GPU. Use your game’s available native AA/upscaling options.', 'The NVIDIA driver controls and Reflex guidance above apply only to supported NVIDIA hardware.'))
    rows.append(('Validate your choice', 'Use the same Siege benchmark and a repeatable gameplay scene. Compare FPS, frame times, target visibility and tearing one option at a time.', 'A higher displayed FPS alone does not establish lower end-to-end input latency. Options vary by Siege version; skip settings that are absent.'))
    return rows
