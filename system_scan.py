"""Read-only local Windows inventory. No network, administrator rights or changes."""
import ctypes
import json
import os
import platform
from pathlib import Path
import subprocess
import uuid

POWERSHELL_SCAN = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$cpu = @(Get-CimInstance Win32_Processor | ForEach-Object { $_.Name })
$memory = (Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum
$system = Get-CimInstance Win32_ComputerSystem
$os = Get-CimInstance Win32_OperatingSystem
$video = @(Get-CimInstance Win32_VideoController | ForEach-Object {
    @{name=$_.Name; hz=$_.CurrentRefreshRate}
})
@{cpu=($cpu -join ' / '); ram_bytes=$memory; os=$os.Caption;
  laptop=($system.PCSystemType -eq 2); video=$video} | ConvertTo-Json -Depth 4 -Compress
'''


def dxgi_adapters():
    """Read dedicated VRAM via DXGI; Win32_VideoController.AdapterRAM truncates at 4GB."""
    from ctypes import wintypes as w
    class LUID(ctypes.Structure):
        _fields_ = [('LowPart', w.DWORD), ('HighPart', w.LONG)]
    class Description(ctypes.Structure):
        _fields_ = [('Description', w.WCHAR * 128), ('VendorId', w.UINT),
                    ('DeviceId', w.UINT), ('SubSysId', w.UINT), ('Revision', w.UINT),
                    ('DedicatedVideoMemory', ctypes.c_size_t),
                    ('DedicatedSystemMemory', ctypes.c_size_t),
                    ('SharedSystemMemory', ctypes.c_size_t), ('AdapterLuid', LUID), ('Flags', w.UINT)]
    def method(obj, slot, result, *args):
        table = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return ctypes.WINFUNCTYPE(result, ctypes.c_void_p, *args)(table[slot])
    factory = ctypes.c_void_p()
    iid = (ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID('770aae78-f26f-4dba-a829-253c83d1b387').bytes_le)
    create = ctypes.WinDLL('dxgi').CreateDXGIFactory1
    create.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    create.restype = ctypes.c_long
    if create(ctypes.byref(iid), ctypes.byref(factory)) < 0:
        raise RuntimeError('DXGI GPU inventory is unavailable.')
    result = []
    try:
        for index in range(32):
            adapter = ctypes.c_void_p()
            hr = method(factory, 12, ctypes.c_long, w.UINT, ctypes.POINTER(ctypes.c_void_p))(factory, index, ctypes.byref(adapter))
            if hr == -2005270526:  # DXGI_ERROR_NOT_FOUND
                break
            if hr < 0:
                raise RuntimeError('Could not enumerate every display adapter.')
            try:
                desc = Description()
                if method(adapter, 10, ctypes.c_long, ctypes.POINTER(Description))(adapter, ctypes.byref(desc)) < 0:
                    raise RuntimeError('Could not read display adapter details.')
                if not desc.Flags & 2:  # Exclude the software rendering adapter.
                    result.append({'name': desc.Description, 'vram_bytes': desc.DedicatedVideoMemory})
            finally:
                method(adapter, 2, w.ULONG)(adapter)
    finally:
        method(factory, 2, w.ULONG)(factory)
    return result


def normalize_inventory(raw, adapters):
    if not isinstance(raw, dict):
        raise ValueError('Windows returned an invalid inventory.')
    videos = raw.get('video') or []
    if isinstance(videos, dict): videos = [videos]
    gpus = []
    for adapter in adapters:
        name = str(adapter.get('name') or '').strip()
        if not name: continue
        size = adapter.get('vram_bytes')
        # Shared system RAM is not dedicated VRAM. Do not fabricate a value.
        vram = str(int(size / 2**30 + 0.5)) if isinstance(size, (int, float)) and size >= 2**30 else ('0' if isinstance(size, (int, float)) and size >= 0 else '')
        matching = next((v for v in videos if str(v.get('name', '')).casefold() == name.casefold()), {})
        hz = matching.get('hz')
        hz = str(int(hz)) if isinstance(hz, (int, float)) and 30 <= hz <= 1000 else ''
        gpus.append({'name': name, 'vram': vram, 'hz': hz})
    if not gpus:
        for video in videos:
            if video.get('name'):
                hz = video.get('hz')
                gpus.append({'name': str(video['name']), 'vram': '',
                             'hz': str(int(hz)) if isinstance(hz, (int, float)) and 30 <= hz <= 1000 else ''})
    ram = raw.get('ram_bytes') or 0
    return {'cpu': str(raw.get('cpu') or '').strip(), 'ram': str(round(ram / 2**30)) if ram else '',
            'os': str(raw.get('os') or 'Windows (version unavailable)'),
            'laptop': bool(raw.get('laptop')), 'gpus': gpus}


def scan_system():
    if platform.system() != 'Windows':
        raise RuntimeError('System scanning requires Windows 10/11. You can still enter specs manually.')
    shell = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    try:
        process = subprocess.run([str(shell), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', POWERSHELL_SCAN],
                                 capture_output=True, timeout=35, creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError('Windows inventory could not run or timed out. Retry, or enter specs manually.') from exc
    if process.returncode:
        raise RuntimeError('Windows blocked or could not complete the read-only inventory. Enter specs manually or check Windows Management Instrumentation availability.')
    try:
        raw = json.loads(process.stdout.decode('utf-8-sig'))
    except (UnicodeError, ValueError) as exc:
        raise RuntimeError('Windows returned unreadable scan results. Enter specs manually.') from exc
    try:
        adapters = dxgi_adapters()
    except (OSError, RuntimeError, AttributeError):
        adapters = []
    return normalize_inventory(raw, adapters)
