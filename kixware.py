"""KixWare Windows desktop UI (Python standard library only)."""
import os
import platform
import queue
import threading
from system_scan import scan_system
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from engine import TWEAKS, TweakManager, WindowsRegistry, recommendations, graphics_recommendations

BG, PANEL, FG, MUTED, ACCENT = '#0b1018', '#141e2c', '#ecf3ff', '#9fb0c6', '#77e4bd'

class App:
    def __init__(self, root):
        self.root = root
        root.title('KixWare • Siege performance lab')
        root.geometry('1060x780')
        root.minsize(800, 650)
        root.configure(bg=BG)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background=PANEL, foreground=FG, font=('Segoe UI', 10))
        style.configure('TNotebook.Tab', padding=(18, 10))
        style.configure('TButton', padding=8)
        style.configure('TEntry', fieldbackground=BG, foreground=FG)
        self.manager = None
        self.error = ''
        if platform.system() == 'Windows':
            try:
                base = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'KixWare'
                self.manager = TweakManager(WindowsRegistry(), base / 'backups.json')
            except Exception as exc:
                self.error = str(exc)
        else:
            self.error = 'Preview mode: Windows tweaks require Windows 10/11.'
        tk.Label(root, text='KIXWARE', font=('Segoe UI', 27, 'bold'), fg=ACCENT, bg=BG).pack(anchor='w', padx=28, pady=(22, 0))
        tk.Label(root, text='RAINBOW SIX SIEGE  /  PERFORMANCE LAB', fg=MUTED, bg=BG).pack(anchor='w', padx=30, pady=(3, 16))
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=24, pady=(0, 16))
        self.spec_tab = ttk.Frame(self.notebook, padding=20)
        self.tweak_tab = ttk.Frame(self.notebook, padding=20)
        self.graphics_tab = ttk.Frame(self.notebook, padding=20)
        self.history_tab = ttk.Frame(self.notebook, padding=20)
        for tab, title in [(self.spec_tab, '01  Your PC'), (self.tweak_tab, '02  Windows tweaks'), (self.graphics_tab, '03  AA & NVIDIA'), (self.history_tab, '04  Applied & recovery')]:
            self.notebook.add(tab, text=title)
        self.build_specs()
        self.build_tweaks()
        self.build_graphics()
        self.refresh_history()
        tk.Label(root, text='Measure first. Change one thing. Benchmark again. No guaranteed FPS or ping gains.', fg=MUTED, bg=BG).pack(pady=(0, 14))

    def build_specs(self):
        ttk.Label(self.spec_tab, text='Build your Siege starting profile', font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(self.spec_tab, text='Scan your PC, review the results, then confirm. You can also enter specs manually.').pack(anchor='w', pady=(6, 16))
        scan_row = ttk.Frame(self.spec_tab)
        scan_row.pack(fill='x', pady=(0, 8))
        self.scan_button = ttk.Button(scan_row, text='Scan this PC', command=self.start_scan)
        self.scan_button.pack(side='left')
        self.scan_status = tk.StringVar(value='Read-only scan. Nothing is applied or uploaded.')
        ttk.Label(scan_row, textvariable=self.scan_status).pack(side='left', padx=12)
        form = ttk.Frame(self.spec_tab)
        form.pack(fill='x')
        self.fields = {}
        for i, (label, default) in enumerate([('CPU model', ''), ('GPU model', ''), ('RAM (GB)', ''), ('GPU VRAM (GB)', ''), ('Monitor refresh (Hz)', '')]):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky='w', pady=5, padx=(0, 20))
            var = tk.StringVar(value=default)
            ttk.Entry(form, textvariable=var, width=46).grid(row=i, column=1, sticky='ew', pady=5)
            self.fields[label] = var
        self.laptop = tk.BooleanVar()
        ttk.Checkbutton(form, text='This is a laptop', variable=self.laptop).grid(row=5, column=1, sticky='w', pady=8)
        ttk.Button(self.spec_tab, text='Generate recommendations →', command=self.generate).pack(anchor='w', pady=10)
        self.output = tk.Text(self.spec_tab, wrap='word', bg=BG, fg=FG, relief='flat', padx=14, pady=12, height=10, font=('Segoe UI', 10))
        self.output.pack(fill='both', expand=True)
        self.set_output('Your profile will appear here. These game settings are manual recommendations; Windows tweaks are on the next tab.')

    def start_scan(self):
        self.scan_button.configure(state='disabled')
        self.scan_status.set('Scanning locally… this can take up to 35 seconds.')
        results = queue.Queue()
        def worker():
            try:
                results.put((scan_system(), None))
            except Exception as exc:
                results.put((None, str(exc)))
        threading.Thread(target=worker, daemon=True).start()
        def poll():
            try:
                inventory, error = results.get_nowait()
            except queue.Empty:
                self.root.after(100, poll)
                return
            self.scan_button.configure(state='normal')
            if error:
                self.scan_status.set('Scan unavailable. Manual entry is available below.')
                messagebox.showerror('System scan', error)
            else:
                self.scan_status.set('Scan finished. Review and confirm the detected hardware.')
                self.show_scan_confirmation(inventory)
        self.root.after(100, poll)

    def show_scan_confirmation(self, inventory):
        window = tk.Toplevel(self.root)
        window.title('KixWare • Confirm detected system')
        window.geometry('820x540')
        window.transient(self.root)
        window.grab_set()
        body = ttk.Frame(window, padding=22)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='Does this match your PC?', font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(body, text=inventory['os'], wraplength=750).pack(anchor='w', pady=8)
        ttk.Label(body, text='Choose the GPU Siege uses. Review every value and correct anything missing.\nReported refresh rate may belong to a different display; verify your gaming monitor.', wraplength=750).pack(anchor='w', pady=(0, 12))
        form = ttk.Frame(body)
        form.pack(fill='x')
        form.columnconfigure(1, weight=1)
        values = {'CPU model': inventory['cpu'], 'GPU model': '', 'RAM (GB)': inventory['ram'], 'GPU VRAM (GB)': '', 'Monitor refresh (Hz)': ''}
        variables = {key: tk.StringVar(value=value) for key, value in values.items()}
        for row, (key, variable) in enumerate(variables.items()):
            ttk.Label(form, text=key).grid(row=row, column=0, sticky='w', pady=7, padx=(0, 18))
            if key == 'GPU model':
                widget = ttk.Combobox(form, textvariable=variable, values=[g['name'] for g in inventory['gpus']])
            else:
                widget = ttk.Entry(form, textvariable=variable)
            widget.grid(row=row, column=1, sticky='ew', pady=7)
            if key == 'GPU model':
                gpu_selector = widget
        def select_gpu(event=None):
            selected = next((g for g in inventory['gpus'] if g['name'] == variables['GPU model'].get()), None)
            variables['GPU VRAM (GB)'].set(selected['vram'] if selected else '')
            variables['Monitor refresh (Hz)'].set(selected['hz'] if selected else '')
        gpu_selector.bind('<<ComboboxSelected>>', select_gpu)
        if inventory['gpus']:
            gpu_selector.current(0)
            select_gpu()
        laptop = tk.BooleanVar(value=inventory['laptop'])
        ttk.Checkbutton(body, text='This is a laptop (verify)', variable=laptop).pack(anchor='w', pady=10)
        ttk.Label(body, text='Blank VRAM means it could not be verified. Enter dedicated VRAM from Task Manager → Performance → GPU. 0 means less than 1 GB dedicated (common on integrated GPUs). Shared memory is excluded.', wraplength=750).pack(anchor='w', pady=5)
        buttons = ttk.Frame(body)
        buttons.pack(fill='x', pady=12)
        def cancel():
            self.scan_status.set('Scan cancelled. Your previous specs were kept.')
            window.destroy()
        def confirm():
            try:
                recommendations(*(value.get() for value in variables.values()), laptop.get())
            except ValueError as exc:
                messagebox.showerror('Review detected specs', str(exc), parent=window)
                return
            for key, variable in variables.items():
                self.fields[key].set(variable.get())
            self.laptop.set(laptop.get())
            self.scan_status.set('System confirmed. Recommendations updated; no tweaks applied.')
            window.destroy()
            self.generate()
        ttk.Button(buttons, text='Cancel', command=cancel).pack(side='left')
        ttk.Button(buttons, text='Confirm system & generate profile', command=confirm).pack(side='right')
        window.protocol('WM_DELETE_WINDOW', cancel)
        # Expose controls for the packaged functional smoke test.
        window.scan_variables = variables
        window.confirm_scan = confirm
        window.cancel_scan = cancel
        window.gpu_selector = gpu_selector
        return window

    def set_output(self, content):
        self.output.configure(state='normal')
        self.output.delete('1.0', 'end')
        self.output.insert('end', content)
        self.output.configure(state='disabled')

    def generate(self):
        try:
            rows = recommendations(*(var.get() for var in self.fields.values()), self.laptop.get())
            self.set_output('\n\n'.join(f'{name.upper()}\n{action}\nWhy: {reason}' for name, action, reason in rows))
            self.update_graphics()
        except ValueError as exc:
            messagebox.showerror('Check your specs', str(exc))

    def build_graphics(self):
        ttk.Label(self.graphics_tab, text='Anti-aliasing & NVIDIA settings', font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(self.graphics_tab, text='Manual recommendations • enter your GPU on Your PC, then generate or refresh here.', wraplength=850).pack(anchor='w', pady=10)
        ttk.Button(self.graphics_tab, text='Refresh from my GPU', command=self.update_graphics).pack(anchor='w', pady=(0, 12))
        frame = ttk.Frame(self.graphics_tab)
        frame.pack(fill='both', expand=True)
        self.graphics_output = tk.Text(frame, wrap='word', bg=BG, fg=FG, relief='flat', padx=14, pady=12, font=('Segoe UI', 10))
        scroll = ttk.Scrollbar(frame, command=self.graphics_output.yview)
        self.graphics_output.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.graphics_output.pack(side='left', fill='both', expand=True)
        self.graphics_output.insert('end', 'Enter your GPU model on Your PC and generate recommendations. These recommendations do not change your game or NVIDIA driver settings.')
        self.graphics_output.configure(state='disabled')

    def update_graphics(self):
        try:
            rows = graphics_recommendations(self.fields['GPU model'].get())
            self.graphics_output.configure(state='normal')
            self.graphics_output.delete('1.0', 'end')
            self.graphics_output.insert('end', '\n\n'.join(f'{title.upper()}\n{action}\nWhy: {reason}' for title, action, reason in rows))
            self.graphics_output.configure(state='disabled')
        except ValueError as exc:
            messagebox.showerror('Check your GPU', str(exc))

    def build_tweaks(self):
        ttk.Label(self.tweak_tab, text='Small changes. Clear reasons. Full control.', font=('Segoe UI', 17, 'bold')).pack(anchor='w')
        ttk.Label(self.tweak_tab, text='Review each change before applying. Originals are backed up locally. No administrator rights needed.', wraplength=900).pack(anchor='w', pady=(8, 14))
        if self.error:
            ttk.Label(self.tweak_tab, text=self.error, wraplength=850).pack(anchor='w', pady=8)
        for key, tweak in TWEAKS.items():
            frame = ttk.LabelFrame(self.tweak_tab, text=tweak['title'], padding=12)
            frame.pack(fill='x', pady=7)
            ttk.Label(frame, text=tweak['reason'] + '\n' + tweak['impact'], wraplength=850).pack(anchor='w')
            ttk.Label(frame, text=f"HKCU\\{tweak['path']}  •  {tweak['name']} = {tweak['value']}", wraplength=850, foreground=MUTED).pack(anchor='w', pady=5)
            ttk.Button(frame, text='Review & apply', command=lambda k=key: self.apply(k), state='normal' if self.manager else 'disabled').pack(anchor='e')

    def apply(self, key):
        tweak = TWEAKS[key]
        if messagebox.askyesno(tweak['title'], tweak['reason'] + '\n\n' + tweak['impact'] + '\n\nApply this change? Its original value will be saved for Undo.'):
            try:
                self.manager.apply(key)
                messagebox.showinfo('Applied', 'Setting saved. Restart Siege; sign out and back in for pointer settings. See Applied & recovery to undo.')
            except Exception as exc:
                messagebox.showerror('Could not complete change', str(exc) + '\nIf a backup is listed, use Undo to recover.')
            self.refresh_history()

    def refresh_history(self):
        for child in self.history_tab.winfo_children():
            child.destroy()
        ttk.Label(self.history_tab, text='Your change log & recovery', font=('Segoe UI', 18, 'bold')).pack(anchor='w', pady=(0, 14))
        ttk.Label(self.history_tab, text='Undo restores the exact original value (or removes a value that did not exist).\nUndo also removes that tweak from the active list. Keep backups until all tweaks are undone.', wraplength=850).pack(anchor='w', pady=(0, 12))
        if not self.manager or not self.manager.state:
            ttk.Label(self.history_tab, text='No saved changes on this PC.').pack(anchor='w', pady=20)
        if self.manager:
            for key, entry in self.manager.state.items():
                frame = ttk.LabelFrame(self.history_tab, text=TWEAKS[key]['title'], padding=12)
                frame.pack(fill='x', pady=8)
                ttk.Label(frame, text=f"Status: {entry['status']}  •  {entry['at']}\nWhy: {TWEAKS[key]['reason']}", wraplength=800).pack(anchor='w')
                ttk.Button(frame, text='Undo / remove tweak', command=lambda k=key: self.undo(k)).pack(anchor='e', pady=6)
            ttk.Label(self.history_tab, text=f'Backup: {self.manager.path}', wraplength=850, foreground=MUTED).pack(anchor='w', pady=18)

    def undo(self, key):
        if messagebox.askyesno('Restore original setting?', 'This restores the value from before KixWare applied this tweak. Any later manual change to the same setting will be replaced.'):
            try:
                self.manager.undo(key)
                messagebox.showinfo('Restored', 'Original setting restored. Restart Siege; sign out and back in for pointer settings.')
            except Exception as exc:
                messagebox.showerror('Restore failed', str(exc) + '\nThe backup has been retained; retry after resolving the error.')
            self.refresh_history()

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == '--smoke-test':
        from packaging_smoke import run
        run(sys.argv[2])
    else:
        App(tk.Tk()).root.mainloop()
