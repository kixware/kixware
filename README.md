# KixWare

A Windows 10/11 desktop companion for Rainbow Six Siege. Enter CPU, GPU, RAM, dedicated VRAM and monitor refresh rate to generate a conservative starting profile. Recommendations use VRAM, RAM, refresh rate, laptop status and NVIDIA GPU identification; CPU names are recorded as context, not used to invent performance estimates.

## Run the packaged Windows app (no Python installation)

Download [KixWare-Windows-x64.zip](https://github.com/kixware/kixware/raw/refs/heads/main/downloads/KixWare-Windows-x64.zip), extract it, and double-click **KixWare.exe**. Keep the included quick-start guide. This is a portable, unsigned Windows x64 app; Windows may show SmartScreen. Do not disable Windows security or antivirus. Actual FPS and latency improvements require measurement on your hardware.

## Open and run from source

1. Download this repository to your Windows PC and extract the ZIP.
2. Install **Python 3.10 or newer** from https://www.python.org/downloads/windows/ with the Python launcher and Tcl/Tk (included in the standard installer).
3. Double-click **Start-KixWare.bat** in the extracted folder. Alternatively, open a terminal there and run `py -3 kixware.py`.
4. Click **Scan this PC** on **Your PC**, review the editable system confirmation, select the GPU Siege uses, and confirm. Manual entry remains available.
5. In **Windows tweaks**, review and apply individual changes. In **Applied & recovery**, click **Undo / remove tweak** to restore the original setting.

No packages, account, internet connection or administrator rights are required to run. The source launch method requires Python; the packaged executable includes its runtime. Do not run multiple copies simultaneously.

## What it changes

| Optional Windows tweak | Reason | Scope / tradeoff |
| --- | --- | --- |
| Enable Game Mode | Allows Windows gaming workload prioritization | Current user, all games; improvement depends on workload |
| Disable Windows game capture | Can remove recording overhead | Disables Windows capture for current user; other recorders unaffected |
| Disable pointer acceleration | Consistent Windows pointer movement | Desktop behavior changes; Siege raw input may bypass it; no FPS benefit claimed |

Every change requires review and saves the original registry value and type before writing. Backups are stored in `%LOCALAPPDATA%\KixWare\backups.json`. Missing original values are deleted during Undo. Pending changes from failed/interrupted operations remain recoverable. Keep this file until you undo your changes. Undo replaces later manual edits to the same setting. Other tools changing settings concurrently can cause conflicts.

Restart Siege after changing settings. Sign out and back in for pointer settings. The app does not edit Siege configuration, so it cannot overwrite game profiles. Graphics, Reflex, frame-cap, power and network recommendations are manual instructions and are **not** listed as applied Windows changes.

## Check whether a change helps

Run Siege's built-in benchmark before changing anything. Record average FPS, low FPS/frame times when available, resolution and graphics settings. Apply one change, restart as needed, and repeat the same benchmark several times. Keep only changes that measurably help your system. FPS and ping improvements are not guaranteed. CPU/GPU model names alone cannot establish a bottleneck; watch utilization, temperatures and frame-time behavior. Settings exposed by Siege vary by game version.

KixWare does not disable security, anti-cheat, Windows services, alter timers/network registry settings, overclock, inject into the game or claim to measure latency. It makes no assertion of anti-cheat vendor approval.

## Development

Use the existing checkout; each cloud task is isolated and needs no extra Git worktree. Python 3.10+ and its standard library are sufficient.

```sh
python3 -m unittest discover -s tests -v
python3 kixware.py
```

Windows is required for real registry operations. Linux can render the interface with Tk/display support in preview mode; Apply buttons are disabled. Tests exercise hardware recommendations and persisted apply/undo recovery using a fake registry. Native Windows behavior, sign-out effects, and actual Siege performance require validation on a Windows gaming PC.

## Rebuild the Windows EXE

On Windows, install Python 3.12 with Tcl/Tk and the launcher, then run:

```powershell
powershell -File packaging/build-windows.ps1
```

The build script installs pinned packaging dependencies into `.venv-build`, runs the unit tests, builds a single-file GUI executable with PyInstaller, launches it with `--smoke-test`, verifies its fresh JSON report, and produces `dist/KixWare-Windows-x64.zip`. The smoke test opens the four UI tabs, generates a sample profile and checks the real Windows registry backend using a temporary isolated key. It does not apply gaming tweaks. It briefly writes and then deletes its test key under `HKCU\Software\KixWare`.

The **AA & NVIDIA** tab adds manual recommendations for AA Off versus T-AA, render scaling, RTX DLSS where available, Reflex, and NVIDIA Control Panel AA, latency, power and filtering settings. Generate a profile on Your PC to populate it; NVIDIA-specific advice is hidden for other GPUs.

The Windows GitHub Actions workflow can run the same script when manually dispatched or when a `v*` tag is pushed. It uploads the ZIP and smoke-test report as build artifacts; it does not publish a release. The workflow must first be committed and pushed to GitHub. No remote workflow execution is claimed unless a successful run is recorded.

The cloud-built package uses Windows Python from Astral's python-build-standalone (3.12.15, release 20261013, verified against release SHA256SUMS) under Wine. Wine smoke tests establish packaging behavior, not native Windows compatibility or Siege performance. Python and Tcl/Tk license files are bundled in the executable.

## Local system scan

**Scan this PC** reads CPU, installed RAM, Windows version, laptop status, display-adapter names, dedicated GPU memory and the driver-reported refresh rate. A confirmation window lets you choose between detected GPUs, correct values, cancel without replacing your existing profile, or confirm and generate recommendations. Scanning never applies tweaks.

The scan uses built-in Windows PowerShell/CIM for system inventory and DXGI for dedicated VRAM. WMI's 32-bit AdapterRAM value is not trusted because it can truncate memory above 4 GB. If DXGI is unavailable, GPU names can still be shown but VRAM stays blank. Shared GPU memory is not counted as dedicated VRAM. Missing/unknown fields must be corrected before confirmation. Check the refresh rate against your gaming monitor, especially with multiple monitors. Laptop detection is also editable. GPUs with less than 1 GB dedicated VRAM show 0 GB; shared memory is excluded. Low-memory profiles recommend Low textures and checking game requirements.

No personal identifiers, installed-app inventory, network requests or administrator permissions are needed. The scan runs in the background with a 35-second inventory timeout. If Windows management tools are unavailable, a clear error leaves manual entry available. Native Windows hardware scanning remains to be verified on a real Windows machine; fixture tests and Wine cannot validate detection of your physical GPU.
