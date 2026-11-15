"""
CyberShield Toolkit - consolidated GUI prototype for Windows 10/11.
Run with Python 3.10+. Build a portable EXE on Windows with scripts/build_portable_windows.bat.

Safety design:
- Firewall: inspect and ENABLE only; no disable control.
- Microsoft Defender: read-only status.
- RDP: enable/disable with confirmation.
- Remote-support apps: detect and stop/launch common clients; this is not a guarantee
  that all remote access paths are blocked.
- Wi-Fi: enable/disable first detected wireless adapter.
- Port scan: common TCP ports, localhost by default; only scan hosts you are authorized to test.
- Maintenance tools: DNS flush, IP configuration, ping, traceroute, process list,
  startup list, system information, temp-folder cleanup preview/cleanup.
"""
import ctypes
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

APP_TITLE = "CyberShield Toolkit"
DATA_DIR = os.path.join(os.getenv("LOCALAPPDATA", os.path.expanduser("~")), "CyberShieldToolkit")
os.makedirs(DATA_DIR, exist_ok=True)
LOG_PATH = os.path.join(DATA_DIR, "activity.log")

REMOTE_APPS = {
    "AnyDesk": {"processes": ["AnyDesk"], "paths": [
        os.path.expandvars(r"%ProgramFiles(x86)%\AnyDesk\AnyDesk.exe"),
        os.path.expandvars(r"%ProgramFiles%\AnyDesk\AnyDesk.exe"),
        os.path.expandvars(r"%LocalAppData%\Programs\AnyDesk\AnyDesk.exe")]},
    "TeamViewer": {"processes": ["TeamViewer", "TeamViewer_Service"], "paths": [
        os.path.expandvars(r"%ProgramFiles%\TeamViewer\TeamViewer.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\TeamViewer\TeamViewer.exe")]},
    "RustDesk": {"processes": ["rustdesk"], "paths": [
        os.path.expandvars(r"%ProgramFiles%\RustDesk\rustdesk.exe"),
        os.path.expandvars(r"%LocalAppData%\Programs\RustDesk\rustdesk.exe")]},
    "Chrome Remote Desktop": {"processes": ["remoting_host"], "paths": []},
}

def hidden_opts():
    if os.name != "nt":
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0
    return {"startupinfo": si, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}

def run_cmd(args, timeout=25):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, **hidden_opts())

def ps(command, timeout=25):
    return run_cmd(["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
                    "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-Command", command], timeout)

def admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def log(message):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return line

def json_ps(command):
    p = ps(command)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or "PowerShell command failed")
    return json.loads(p.stdout) if p.stdout.strip() else None

def firewall_state():
    data = json_ps("Get-NetFirewallProfile | Select-Object Name,Enabled | ConvertTo-Json -Compress")
    if isinstance(data, dict): data = [data]
    return ", ".join(f"{x['Name']}: {'ON' if x['Enabled'] else 'OFF'}" for x in data)

def defender_state():
    d = json_ps("Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,AMServiceEnabled | ConvertTo-Json -Compress")
    return (f"Antivirus {'ON' if d.get('AntivirusEnabled') else 'OFF'} | "
            f"Real-time {'ON' if d.get('RealTimeProtectionEnabled') else 'OFF'} | "
            f"AM Service {'ON' if d.get('AMServiceEnabled') else 'OFF'}")

def rdp_state():
    p = ps("(Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server' -Name fDenyTSConnections).fDenyTSConnections")
    if p.returncode: raise RuntimeError(p.stderr.strip() or "Could not read RDP setting")
    return "OFF" if p.stdout.strip() == "1" else "ON"

def require_admin():
    if not admin():
        raise PermissionError("এই কাজের জন্য Administrator permission দরকার। CyberShield-এ right-click করে Run as administrator দাও।")

def set_rdp(enabled):
    require_admin()
    val = 0 if enabled else 1
    command = f"Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server' -Name fDenyTSConnections -Value {val}; "
    command += ("Enable-NetFirewallRule -DisplayGroup 'Remote Desktop' -ErrorAction SilentlyContinue" if enabled
                else "Disable-NetFirewallRule -DisplayGroup 'Remote Desktop' -ErrorAction SilentlyContinue")
    p = ps(command)
    if p.returncode: raise RuntimeError(p.stderr.strip() or p.stdout.strip())

def enable_firewall():
    require_admin()
    p = ps("Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled True")
    if p.returncode: raise RuntimeError(p.stderr.strip() or p.stdout.strip())

def get_wifi():
    data = json_ps("Get-NetAdapter -Physical | Where-Object {$_.Name -match 'Wi-Fi|Wireless|WLAN' -or $_.InterfaceDescription -match 'Wireless|Wi-Fi'} | Select-Object Name,Status | ConvertTo-Json -Compress")
    if not data: return None
    if isinstance(data, dict): data = [data]
    return data[0]

def wifi_toggle(enable):
    require_admin()
    adapter = get_wifi()
    if not adapter: raise RuntimeError("Wi-Fi adapter পাওয়া যায়নি।")
    verb = "Enable-NetAdapter" if enable else "Disable-NetAdapter"
    name = adapter["Name"].replace("'", "''")
    p = ps(f"{verb} -Name '{name}' -Confirm:$false")
    if p.returncode: raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return adapter["Name"]

def process_names():
    p = ps("Get-Process | Select-Object -ExpandProperty ProcessName")
    if p.returncode: raise RuntimeError(p.stderr.strip())
    return {x.strip().lower() for x in p.stdout.splitlines() if x.strip()}

def remote_status():
    running = process_names()
    return {app: any(proc.lower() in running for proc in info["processes"])
            for app, info in REMOTE_APPS.items()}

def remote_stop(app):
    require_admin()
    names = REMOTE_APPS[app]["processes"]
    arr = ",".join("'" + n.replace("'", "''") + "'" for n in names)
    p = ps(f"Get-Process -ErrorAction SilentlyContinue | Where-Object {{$_.ProcessName -in @({arr})}} | Stop-Process -Force")
    if p.returncode: raise RuntimeError(p.stderr.strip() or p.stdout.strip())

def remote_start(app):
    info = REMOTE_APPS[app]
    running = remote_status().get(app, False)
    if running: return "Already running"
    for path in info["paths"]:
        if path and os.path.isfile(path):
            subprocess.Popen([path], **hidden_opts())
            return f"Started {app}"
    raise FileNotFoundError(f"{app} executable পাওয়া যায়নি। App install path detect হয়নি।")

def flush_dns():
    p = run_cmd(["ipconfig.exe", "/flushdns"])
    if p.returncode: raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return p.stdout.strip()

def ip_config():
    p = run_cmd(["ipconfig.exe", "/all"])
    if p.returncode: raise RuntimeError(p.stderr.strip())
    return p.stdout

def refresh_dhcp_ip():
    """Release and renew DHCP leases. This briefly disconnects DHCP interfaces."""
    require_admin()
    released = run_cmd(["ipconfig.exe", "/release"], timeout=35)
    # ipconfig may return non-zero when an adapter is not DHCP-enabled; continue to renew.
    renewed = run_cmd(["ipconfig.exe", "/renew"], timeout=60)
    if renewed.returncode:
        raise RuntimeError(renewed.stderr.strip() or renewed.stdout.strip() or "DHCP renew failed")
    details = run_cmd(["ipconfig.exe"], timeout=15)
    return "DHCP release/renew completed.\n\n" + (details.stdout or renewed.stdout)

def ping_host(host):
    p = run_cmd(["ping.exe", "-n", "4", host], timeout=20)
    return p.stdout or p.stderr

def trace_host(host):
    p = run_cmd(["tracert.exe", "-d", "-h", "12", "-w", "700", host], timeout=35)
    return p.stdout or p.stderr

def scan(host):
    ports = [21,22,23,25,53,80,110,135,139,143,443,445,3306,3389,5000,5900,5938,7070,8000,8080,8443,9000]
    out = []
    for port in ports:
        s = socket.socket()
        s.settimeout(.3)
        try:
            s.connect((host, port))
            try: svc = socket.getservbyport(port, "tcp")
            except OSError: svc = "unknown"
            state = "OPEN"
        except socket.timeout:
            state, svc = "FILTERED/TIMEOUT", "unknown"
        except OSError:
            state, svc = "CLOSED", "unknown"
        finally: s.close()
        out.append((port, state, svc))
    return out

def system_info():
    return (f"Computer: {platform.node()}\nOS: {platform.platform()}\n"
            f"Windows: {platform.version()}\nArchitecture: {platform.machine()}\n"
            f"Python: {platform.python_version()}\n")

def startup_items():
    command = "Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location,User | ConvertTo-Json -Compress"
    data = json_ps(command)
    if not data: return []
    return data if isinstance(data, list) else [data]

def running_processes():
    command = "Get-Process | Sort-Object CPU -Descending | Select-Object -First 80 ProcessName,Id,CPU,WorkingSet64 | ConvertTo-Json -Compress"
    data = json_ps(command)
    if not data: return []
    return data if isinstance(data, list) else [data]

def cleanup_temp():
    temp = tempfile.gettempdir()
    removed, failed = 0, 0
    for name in os.listdir(temp):
        path = os.path.join(temp, name)
        try:
            if os.path.isfile(path) or os.path.islink(path): os.remove(path)
            elif os.path.isdir(path): shutil.rmtree(path)
            removed += 1
        except Exception: failed += 1
    return removed, failed


def taskbar_windows():
    """List visible top-level windows similar to items shown on the Windows taskbar."""
    script = r"""
Add-Type @'
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class WinList {
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr lp);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
  public static List<string> Get() {
    var rows = new List<string>();
    EnumWindows(delegate(IntPtr h, IntPtr l) {
      if (IsWindowVisible(h)) {
        var sb = new StringBuilder(512); GetWindowText(h, sb, sb.Capacity);
        string title = sb.ToString().Trim();
        uint pid; GetWindowThreadProcessId(h, out pid);
        if (title.Length > 0) rows.Add(pid + "|" + title.Replace("|"," "));
      }
      return true;
    }, IntPtr.Zero);
    return rows;
  }
}
'@
[WinList]::Get() | ForEach-Object { $_ }
"""
    p = ps(script, timeout=30)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    rows = []
    for line in p.stdout.splitlines():
        if "|" in line:
            pid, title = line.split("|", 1)
            rows.append({"pid": int(pid.strip()), "title": title.strip()})
    return rows

def close_window_process(pid):
    """Close an app gracefully first; do not force-kill Windows shell/system processes."""
    protected = {"0", "4"}
    if str(pid) in protected:
        raise RuntimeError("এই system process বন্ধ করা যাবে না।")
    require_admin()
    p = ps(f"$p = Get-Process -Id {int(pid)} -ErrorAction Stop; $null = $p.CloseMainWindow(); Start-Sleep -Seconds 2; if (!$p.HasExited) {{ Write-Output 'StillRunning' }} else {{ Write-Output 'Closed' }}")
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return p.stdout.strip() or "Close request sent"

def hardware_details():
    """Read CPU, physical memory, board, BIOS, graphics and storage via CIM/WMI."""
    script = r"""
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1 Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,CurrentClockSpeed
$cs = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,TotalPhysicalMemory
$bb = Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,Product,SerialNumber
$bios = Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion,ReleaseDate
$gpu = Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion,VideoModeDescription
$disk = Get-CimInstance Win32_DiskDrive | Select-Object Model,InterfaceType,MediaType,Size,Status
$ram = Get-CimInstance Win32_PhysicalMemory | Select-Object BankLabel,DeviceLocator,Manufacturer,PartNumber,SerialNumber,Capacity,Speed,ConfiguredClockSpeed,ConfiguredVoltage,DataWidth,TotalWidth,FormFactor,SMBIOSMemoryType
[PSCustomObject]@{CPU=$cpu; Computer=$cs; Board=$bb; BIOS=$bios; GPU=@($gpu); Disk=@($disk); RAM=@($ram)} | ConvertTo-Json -Depth 5 -Compress
"""
    data = json_ps(script)
    return data

def format_hardware(data):
    lines = []
    cpu = data.get("CPU") or {}
    comp = data.get("Computer") or {}
    board = data.get("Board") or {}
    lines += ["PROCESSOR", "-" * 60]
    for key, label in [("Name","Model"),("Manufacturer","Manufacturer"),("NumberOfCores","Cores"),
                       ("NumberOfLogicalProcessors","Logical Processors"),("MaxClockSpeed","Max Clock (MHz)"),
                       ("CurrentClockSpeed","Current Clock (MHz)")]:
        lines.append(f"{label}: {cpu.get(key, 'N/A')}")
    lines += ["", "MEMORY MODULES (RAM)", "-" * 60]
    modules = data.get("RAM") or []
    if isinstance(modules, dict): modules = [modules]
    for idx, ram in enumerate(modules, 1):
        try: cap = f"{int(ram.get('Capacity',0)) // (1024**3)} GB"
        except Exception: cap = "Unknown"
        lines += [
            f"Module {idx}:",
            f"  Slot: {ram.get('DeviceLocator') or ram.get('BankLabel') or 'N/A'}",
            f"  Manufacturer: {(ram.get('Manufacturer') or '').strip() or 'N/A'}",
            f"  Part Number: {(ram.get('PartNumber') or '').strip() or 'N/A'}",
            f"  Capacity: {cap}",
            f"  SPD Rated Speed: {ram.get('Speed', 'N/A')} MT/s",
            f"  Configured Speed: {ram.get('ConfiguredClockSpeed', 'N/A')} MT/s",
            f"  Data Width / Total Width: {ram.get('DataWidth','N/A')} / {ram.get('TotalWidth','N/A')}",
            f"  Form Factor: {ram.get('FormFactor','N/A')}",
            f"  SMBIOS Memory Type: {ram.get('SMBIOSMemoryType','N/A')}",
            "  CAS Latency (CL): Not reliably exposed by standard Windows CIM/WMI"
        ]
    lines += ["", "SYSTEM / MOTHERBOARD / BIOS", "-" * 60,
              f"System Manufacturer: {comp.get('Manufacturer','N/A')}",
              f"System Model: {comp.get('Model','N/A')}",
              f"Motherboard Manufacturer: {board.get('Manufacturer','N/A')}",
              f"Motherboard Product: {board.get('Product','N/A')}",
              f"Motherboard Serial: {board.get('SerialNumber','N/A')}",
              f"Total Physical RAM: {int(comp.get('TotalPhysicalMemory') or 0)//(1024**3)} GB"]
    bios = data.get("BIOS") or {}
    lines += [f"BIOS Manufacturer: {bios.get('Manufacturer','N/A')}",
              f"BIOS Version: {bios.get('SMBIOSBIOSVersion','N/A')}",
              f"BIOS Release Date: {bios.get('ReleaseDate','N/A')}", "", "GRAPHICS", "-" * 60]
    gpus = data.get("GPU") or []
    if isinstance(gpus, dict): gpus = [gpus]
    for gpu in gpus:
        vram = int(gpu.get("AdapterRAM") or 0) // (1024**2)
        lines.append(f"GPU: {gpu.get('Name','N/A')} | VRAM reported: {vram} MB | Driver: {gpu.get('DriverVersion','N/A')}")
    lines += ["", "STORAGE", "-" * 60]
    disks = data.get("Disk") or []
    if isinstance(disks, dict): disks = [disks]
    for disk in disks:
        size_gb = int(disk.get("Size") or 0) // (1024**3)
        lines.append(f"{disk.get('Model','N/A')} | {size_gb} GB | {disk.get('InterfaceType','N/A')} | Status: {disk.get('Status','N/A')}")
    lines += ["", "Note: RAM CL timings and live sensor values (temperature, voltage, fan RPM) are not reliably exposed by standard Windows CIM/WMI. N/A means this interface did not return the value."]
    return "\n".join(lines)

class CyberShield(tk.Tk):
    BG = "#0b1220"; PANEL = "#111c2e"; PANEL2 = "#17263c"; TEXT = "#edf3fb"
    MUTED = "#9fb0c7"; GREEN = "#64d99b"; RED = "#ff8585"; BLUE = "#75b8ff"; AMBER = "#f4c66a"

    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1120x820")
        self.minsize(980, 720)
        self.configure(bg=self.BG)
        self._setup_style()
        self._build()
        self.refresh_all()

    def _setup_style(self):
        st = ttk.Style(self); st.theme_use("clam")
        st.configure("TFrame", background=self.PANEL)
        st.configure("TLabel", background=self.PANEL, foreground=self.TEXT, font=("Segoe UI", 10))
        st.configure("Title.TLabel", font=("Segoe UI", 22, "bold"), foreground="#ffffff")
        st.configure("Muted.TLabel", foreground=self.MUTED, font=("Segoe UI", 9))
        st.configure("TButton", font=("Segoe UI", 9, "bold"), padding=(10, 7))
        st.configure("Treeview", background="#0a1423", fieldbackground="#0a1423", foreground=self.TEXT, rowheight=24)
        st.configure("Treeview.Heading", background="#263a56", foreground="#ffffff")
        st.map("TButton", background=[("active", "#35577e")])

    def _build(self):
        head = ttk.Frame(self, padding=(20, 15)); head.pack(fill="x", padx=15, pady=(15, 7))
        ttk.Label(head, text="🛡  CyberShield Toolkit", style="Title.TLabel").pack(anchor="w")
        ttk.Label(head, text="Windows security • Remote access • Network • Maintenance", style="Muted.TLabel").pack(anchor="w", pady=(4,0))
        self.admin_lbl = ttk.Label(head, text=("ADMIN: YES" if admin() else "ADMIN: NO  |  Run as administrator for system controls"), foreground=self.GREEN if admin() else self.AMBER)
        self.admin_lbl.pack(anchor="e")

        nb = ttk.Notebook(self); nb.pack(fill="both", expand=True, padx=15, pady=8)
        self.home = ttk.Frame(nb, padding=12); nb.add(self.home, text="  Dashboard  ")
        self.network = ttk.Frame(nb, padding=12); nb.add(self.network, text="  Network Tools  ")
        self.maintenance = ttk.Frame(nb, padding=12); nb.add(self.maintenance, text="  PC Maintenance  ")
        self.taskbar = ttk.Frame(nb, padding=12); nb.add(self.taskbar, text="  Taskbar Apps  ")
        self.hardware = ttk.Frame(nb, padding=12); nb.add(self.hardware, text="  Hardware Details  ")
        self.spd = ttk.Frame(nb, padding=12); nb.add(self.spd, text="  RAM SPD  ")
        self._dashboard()
        self._network_tab()
        self._maintenance_tab()
        self._taskbar_tab()
        self._hardware_tab()
        self._spd_tab()
        foot = ttk.Frame(self, padding=(18, 5, 18, 12)); foot.pack(fill="x")
        ttk.Button(foot, text="REFRESH ALL", command=self.refresh_all).pack(side="left")
        ttk.Button(foot, text="OPEN ACTIVITY LOG", command=self.open_log).pack(side="left", padx=8)
        ttk.Label(foot, text="Local controls only • Use only on devices you own/manage", style="Muted.TLabel").pack(side="right")

    def card(self, parent, title, row, col, colspan=1):
        frame = ttk.Frame(parent, padding=12)
        frame.grid(row=row, column=col, columnspan=colspan, sticky="nsew", padx=6, pady=6)
        ttk.Label(frame, text=title, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0,8))
        return frame

    def status_row(self, parent, title, key, buttons):
        row = ttk.Frame(parent); row.pack(fill="x", pady=4)
        ttk.Label(row, text=title).pack(side="left")
        label = ttk.Label(row, text="Checking...", foreground=self.AMBER)
        label.pack(side="left", padx=8)
        self.status_labels[key] = label
        for text, callback in buttons:
            ttk.Button(row, text=text, command=callback).pack(side="right", padx=(4,0))

    def _dashboard(self):
        self.status_labels = {}
        self.home.columnconfigure((0,1), weight=1)
        sec = self.card(self.home, "WINDOWS SECURITY", 0, 0)
        self.status_row(sec, "Firewall", "firewall", [("ENABLE", self.firewall_enable)])
        self.status_row(sec, "Microsoft Defender", "defender", [])
        self.status_row(sec, "Remote Desktop", "rdp", [("TOGGLE", self.rdp_toggle)])
        rem = self.card(self.home, "REMOTE ACCESS APPS", 0, 1)
        self.remote_buttons = {}
        for app in REMOTE_APPS:
            row = ttk.Frame(rem); row.pack(fill="x", pady=4)
            ttk.Label(row, text=app).pack(side="left")
            label = ttk.Label(row, text="Checking...", foreground=self.AMBER); label.pack(side="left", padx=8)
            self.status_labels["remote_"+app] = label
            ttk.Button(row, text="OFF / STOP", command=lambda a=app: self.remote_action(a, False)).pack(side="right", padx=(4,0))
            ttk.Button(row, text="ON / START", command=lambda a=app: self.remote_action(a, True)).pack(side="right")
        net = self.card(self.home, "WIRELESS NETWORK", 1, 0)
        self.status_row(net, "Wi-Fi Adapter", "wifi", [("TOGGLE", self.wifi_toggle)])
        self.status_row(net, "DNS Cache", "dns", [("FLUSH DNS", self.dns_flush)])
        note = self.card(self.home, "IMPORTANT NOTES", 1, 1)
        ttk.Label(note, text=("Defender: status only. Firewall: enable only.\n"
             "Remote app STOP closes detected app processes; it does not\n"
             "uninstall the app or guarantee all remote access is blocked.\n"
             "Some actions require Administrator permission."), wraplength=420, justify="left").pack(anchor="w")

    def _network_tab(self):
        self.network.columnconfigure(0, weight=1); self.network.rowconfigure(1, weight=1)
        bar = ttk.Frame(self.network); bar.grid(row=0, column=0, sticky="ew", pady=5)
        ttk.Label(bar, text="Host / IP:").pack(side="left")
        self.host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(bar, textvariable=self.host_var, width=24).pack(side="left", padx=7)
        ttk.Button(bar, text="SCAN COMMON TCP PORTS", command=self.scan_ports).pack(side="left", padx=4)
        ttk.Label(self.network, text="Only scan localhost or a host/network you are authorized to test.", style="Muted.TLabel").grid(row=0, column=0, sticky="e")
        self.scan_tree = ttk.Treeview(self.network, columns=("port","state","service"), show="headings")
        for c,w in [("port",100),("state",220),("service",220)]:
            self.scan_tree.heading(c,text=c.upper()); self.scan_tree.column(c,width=w,anchor="w")
        self.scan_tree.grid(row=1,column=0,sticky="nsew",pady=10)
        tools = ttk.Frame(self.network); tools.grid(row=2,column=0,sticky="ew")
        ttk.Button(tools,text="IP CONFIGURATION",command=lambda:self.show_output("IP Configuration",ip_config)).pack(side="left",padx=4)
        ttk.Button(tools,text="REFRESH / RENEW IP",command=self.ip_refresh).pack(side="left",padx=4)
        ttk.Button(tools,text="PING HOST",command=lambda:self.show_output("Ping",lambda:ping_host(self.host_var.get().strip()))).pack(side="left",padx=4)
        ttk.Button(tools,text="TRACEROUTE",command=lambda:self.show_output("Traceroute",lambda:trace_host(self.host_var.get().strip()))).pack(side="left",padx=4)

    def _maintenance_tab(self):
        self.maintenance.columnconfigure(0,weight=1); self.maintenance.rowconfigure(1,weight=1)
        top = ttk.Frame(self.maintenance); top.grid(row=0,column=0,sticky="ew")
        ttk.Button(top,text="SYSTEM INFORMATION",command=lambda:self.show_text("System Information",system_info())).pack(side="left",padx=4)
        ttk.Button(top,text="RUNNING PROCESSES",command=self.show_processes).pack(side="left",padx=4)
        ttk.Button(top,text="STARTUP ITEMS",command=self.show_startup).pack(side="left",padx=4)
        ttk.Button(top,text="CLEAN TEMP FILES",command=self.clean_temp).pack(side="left",padx=4)
        ttk.Label(self.maintenance,text="Activity Log",font=("Segoe UI",12,"bold")).grid(row=1,column=0,sticky="nw",pady=(18,5))
        self.log_box = tk.Text(self.maintenance,bg="#081321",fg="#d5e2f2",insertbackground="white",relief="flat",font=("Consolas",9))
        self.log_box.grid(row=2,column=0,sticky="nsew")
        self.maintenance.rowconfigure(2,weight=1)
        self.log_box.insert("end",f"Log location: {LOG_PATH}\n")
        self.log_box.configure(state="disabled")


    def _taskbar_tab(self):
        self.taskbar.columnconfigure(0, weight=1)
        self.taskbar.rowconfigure(1, weight=1)
        top = ttk.Frame(self.taskbar); top.grid(row=0, column=0, sticky="ew", pady=5)
        ttk.Label(top, text="Visible application windows (taskbar-like list)", font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Button(top, text="REFRESH WINDOWS", command=self.refresh_taskbar).pack(side="right")
        ttk.Button(top, text="CLOSE SELECTED APP", command=self.close_selected_window).pack(side="right", padx=6)
        self.taskbar_tree = ttk.Treeview(self.taskbar, columns=("pid", "title"), show="headings")
        self.taskbar_tree.heading("pid", text="PROCESS ID")
        self.taskbar_tree.heading("title", text="WINDOW / APP TITLE")
        self.taskbar_tree.column("pid", width=110, anchor="w")
        self.taskbar_tree.column("title", width=700, anchor="w")
        self.taskbar_tree.grid(row=1, column=0, sticky="nsew", pady=8)
        ttk.Label(self.taskbar, text="Close selected sends a graceful close request first. Windows shell/system processes are protected; unsaved work may be lost if an app is later force-closed manually.", style="Muted.TLabel", wraplength=900).grid(row=2, column=0, sticky="w")

    def _hardware_tab(self):
        self.hardware.columnconfigure(0, weight=1)
        self.hardware.rowconfigure(1, weight=1)
        top = ttk.Frame(self.hardware); top.grid(row=0, column=0, sticky="ew", pady=5)
        ttk.Label(top, text="CPU • RAM SPD summary • Motherboard", font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Button(top, text="SCAN HARDWARE", command=self.refresh_hardware).pack(side="right")
        self.hardware_text = tk.Text(self.hardware, bg="#081321", fg=self.TEXT, insertbackground="white",
                                     relief="flat", font=("Consolas", 10), wrap="word")
        self.hardware_text.grid(row=1, column=0, sticky="nsew", pady=8)
        self.hardware_text.insert("end", "Click SCAN HARDWARE to read processor, memory modules, part numbers and reported speeds.")
        self.hardware_text.configure(state="disabled")

    def _spd_tab(self):
        self.spd.columnconfigure(0, weight=1)
        self.spd.rowconfigure(2, weight=1)
        top = ttk.Frame(self.spd); top.grid(row=0, column=0, sticky="ew", pady=5)
        ttk.Label(top, text="RAM SPD Inspector", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Button(top, text="READ SPD / RAM INFO", command=self.refresh_spd).pack(side="right")
        edit = ttk.Frame(self.spd); edit.grid(row=1, column=0, sticky="ew", pady=8)
        ttk.Label(edit, text="Selected module Part Number (display only):").pack(side="left")
        self.spd_part_var = tk.StringVar()
        ttk.Entry(edit, textvariable=self.spd_part_var, width=38).pack(side="left", padx=8)
        self.spd_write_btn = ttk.Button(edit, text="WRITE TO SPD (UNAVAILABLE)", state="disabled")
        self.spd_write_btn.pack(side="left")
        self.spd_text = tk.Text(self.spd, bg="#081321", fg=self.TEXT, insertbackground="white",
                                relief="flat", font=("Consolas", 10), wrap="word")
        self.spd_text.grid(row=2, column=0, sticky="nsew", pady=8)
        self.spd_text.insert("1.0", "Read-only SPD inspection. Click READ SPD / RAM INFO.\n\n"
            "Important: Generic Windows CIM/WMI does not provide a safe, universal SPD write interface. "
            "Writing EEPROM bytes requires memory-controller and module-specific support. An incorrect write "
            "can make a DIMM unbootable. This build will not attempt blind SPD writes or bypass write protection.")
        self.spd_text.configure(state="disabled")

    def refresh_spd(self):
        def work():
            data = hardware_details()
            modules = data.get("RAM") or []
            if isinstance(modules, dict): modules = [modules]
            lines = ["SPD / MEMORY MODULE READOUT", "=" * 64]
            for i, m in enumerate(modules, 1):
                lines += [f"Module {i}", "-" * 64,
                    f"Locator: {m.get('DeviceLocator') or m.get('BankLabel') or 'N/A'}",
                    f"Manufacturer: {(m.get('Manufacturer') or '').strip() or 'N/A'}",
                    f"Part Number: {(m.get('PartNumber') or '').strip() or 'N/A'}",
                    f"Serial Number: {(m.get('SerialNumber') or '').strip() or 'N/A'}",
                    f"Capacity: {int(m.get('Capacity') or 0)//(1024**3)} GB",
                    f"SPD speed: {m.get('Speed', 'N/A')} MT/s",
                    f"Configured speed: {m.get('ConfiguredClockSpeed', 'N/A')} MT/s",
                    f"Configured voltage: {m.get('ConfiguredVoltage', 'N/A')} mV",
                    f"Form factor: {m.get('FormFactor', 'N/A')}",
                    f"SMBIOS memory type: {m.get('SMBIOSMemoryType', 'N/A')}",
                    f"CL / JEDEC / XMP profiles: Not exposed by this Windows CIM/WMI readout", ""]
            if not modules: lines.append("No physical memory module information was returned by Windows.")
            lines += ["", "WRITE STATUS: DISABLED IN THIS BUILD", 
                "Reason: Windows CIM/WMI is read-only for SPD. A safe write requires a verified, supported SPD programmer/interface and module-specific validation.",
                "The Part Number field above is for notes/display only; editing it does not change the RAM SPD chip."]
            return "\n".join(lines), modules
        def done(result, err):
            if err: self.show_error("RAM SPD Inspector", err); return
            text, modules = result
            self.spd_text.configure(state="normal"); self.spd_text.delete("1.0", "end"); self.spd_text.insert("1.0", text); self.spd_text.configure(state="disabled")
            self.spd_part_var.set(((modules[0].get("PartNumber") or "").strip() if modules else ""))
            self.log_ui("RAM SPD information read (Windows CIM/WMI; read-only)")
        self.async_task(work, done, "Read SPD")

    def ip_refresh(self):
        if not self.confirm_action("Refresh / Renew IP", "DHCP IP release ও renew হবে। কয়েক মুহূর্তের জন্য internet/network disconnect হতে পারে। Administrator permission লাগবে। Continue?"):
            return
        def done(result, err):
            if err: self.show_error("IP Refresh", err)
            else:
                self.log_ui("DHCP IP release/renew completed")
                self.show_text("New IP Configuration", result)
            self.refresh_all()
        self.async_task(refresh_dhcp_ip, done, "IP Renew")

    def refresh_taskbar(self):
        def done(rows, err):
            if err:
                self.show_error("Taskbar Apps", err); return
            for item in self.taskbar_tree.get_children():
                self.taskbar_tree.delete(item)
            for row in rows:
                self.taskbar_tree.insert("", "end", values=(row["pid"], row["title"]))
            self.log_ui(f"Taskbar window list refreshed ({len(rows)} windows)")
        self.async_task(taskbar_windows, done)

    def close_selected_window(self):
        selected = self.taskbar_tree.selection()
        if not selected:
            messagebox.showinfo("Taskbar Apps", "আগে তালিকা থেকে একটি app select করো।"); return
        values = self.taskbar_tree.item(selected[0], "values")
        pid, title = int(values[0]), values[1]
        if not self.confirm_action("Close Application", f"'{title}' window বন্ধ করার request পাঠাবে? আগে কাজ save করে নাও।"):
            return
        def done(result, err):
            if err: self.show_error("Close Application", err)
            else: self.log_ui(f"Close request for {title} (PID {pid}): {result}")
            self.refresh_taskbar()
        self.async_task(lambda: close_window_process(pid), done)

    def refresh_hardware(self):
        def work():
            return format_hardware(hardware_details())
        def done(result, err):
            if err: self.show_error("Hardware Details", err); return
            self.hardware_text.configure(state="normal")
            self.hardware_text.delete("1.0", "end")
            self.hardware_text.insert("1.0", result)
            self.hardware_text.configure(state="disabled")
            self.log_ui("Hardware information refreshed")
        self.async_task(work, done)

    def log_ui(self,msg):
        line=log(msg)
        if hasattr(self,"log_box"):
            self.log_box.configure(state="normal"); self.log_box.insert("end",line+"\n")
            self.log_box.see("end"); self.log_box.configure(state="disabled")

    def set_status(self,key,text,color=None):
        w=self.status_labels.get(key)
        if w: w.configure(text=text,foreground=color or self.MUTED)

    def async_task(self, func, done, title="Task"):
        def worker():
            try: result=func(); err=None
            except Exception as e: result=None; err=e
            self.after(0,lambda:done(result,err))
        threading.Thread(target=worker,daemon=True).start()

    def refresh_all(self):
        def work():
            result={}
            for key,fn in [("firewall",firewall_state),("defender",defender_state),("rdp",rdp_state),("wifi",get_wifi),("remote",remote_status)]:
                try: result[key]=fn()
                except Exception as e: result[key]=f"Error: {e}"
            def update():
                fw=result["firewall"]; self.set_status("firewall",fw,"#64d99b" if "OFF" not in fw and "Error" not in fw else self.RED)
                df=result["defender"]; self.set_status("defender",df,"#64d99b" if "OFF" not in df and "Error" not in df else self.AMBER)
                rd=result["rdp"]; self.set_status("rdp",rd,"#ff8585" if rd=="ON" else self.GREEN)
                wi=result["wifi"]
                self._wifi_data=wi if isinstance(wi,dict) else None
                self.set_status("wifi",(f"{wi.get('Name')} ({wi.get('Status')})" if isinstance(wi,dict) else str(wi)),self.GREEN if isinstance(wi,dict) and wi.get("Status")=="Up" else self.AMBER)
                self.set_status("dns","Ready")
                rem=result["remote"]
                if isinstance(rem,dict):
                    for app,running in rem.items():
                        self.set_status("remote_"+app,"RUNNING" if running else "STOPPED",self.RED if running else self.GREEN)
                else:
                    for app in REMOTE_APPS: self.set_status("remote_"+app,str(rem),self.AMBER)
            self.after(0,update)
        threading.Thread(target=work,daemon=True).start()

    def confirm_action(self,title,msg):
        return messagebox.askyesno(title,msg,parent=self)

    def show_error(self,title,err):
        messagebox.showerror(title,str(err),parent=self)

    def firewall_enable(self):
        if not self.confirm_action("Enable Firewall","সব Windows network profile-এ Firewall ON করবে?"): return
        def done(r,e):
            if e:self.show_error("Firewall",e)
            else:self.log_ui("Enabled Windows Firewall"); messagebox.showinfo("Firewall","Firewall enable command completed.")
            self.refresh_all()
        self.async_task(enable_firewall,done)

    def rdp_toggle(self):
        def done(state,e):
            if e:self.show_error("RDP",e); return
            enable=state!="ON"
            verb="ENABLE" if enable else "DISABLE"
            if self.confirm_action("Remote Desktop",f"Remote Desktop {verb} করবে?"):
                def changed(r,err):
                    if err:self.show_error("RDP",err)
                    else:self.log_ui(f"RDP set to {'ON' if enable else 'OFF'}")
                    self.refresh_all()
                self.async_task(lambda:set_rdp(enable),changed)
        self.async_task(rdp_state,done)

    def remote_action(self,app,start):
        action="start" if start else "stop"
        if not self.confirm_action(app,f"{app} {action.upper()} করতে চাও? STOP শুধু detected process বন্ধ করে; সব remote access path বন্ধ হওয়ার নিশ্চয়তা নয়."):
            return
        def work():
            return remote_start(app) if start else remote_stop(app)
        def done(r,e):
            if e:self.show_error(app,e)
            else:self.log_ui(f"{app}: {action} request. {r or ''}")
            self.refresh_all()
        self.async_task(work,done,app)

    def wifi_toggle(self):
        wi=getattr(self,"_wifi_data",None)
        if not wi:
            messagebox.showwarning("Wi-Fi","Wi-Fi adapter পাওয়া যায়নি। Refresh করো।"); return
        enable=wi.get("Status")!="Up"
        if not self.confirm_action("Wi-Fi",f"{wi.get('Name')} adapter {'ON' if enable else 'OFF'} করবে?"):
            return
        def done(r,e):
            if e:self.show_error("Wi-Fi",e)
            else:self.log_ui(f"Wi-Fi {r}: {'ON' if enable else 'OFF'}")
            self.refresh_all()
        self.async_task(lambda:wifi_toggle(enable),done)

    def dns_flush(self):
        def done(r,e):
            if e:self.show_error("Flush DNS",e)
            else:self.log_ui("DNS cache flushed"); messagebox.showinfo("Flush DNS",r or "Completed")
            self.refresh_all()
        self.async_task(flush_dns,done)

    def scan_ports(self):
        host=self.host_var.get().strip()
        if not host: messagebox.showwarning("Scanner","Enter a host/IP."); return
        if not self.confirm_action("Port Scan",f"{host} common TCP ports scan করবে? শুধু অনুমোদিত host scan করো."): return
        for item in self.scan_tree.get_children(): self.scan_tree.delete(item)
        def done(rows,e):
            if e:self.show_error("Port Scanner",e); return
            for port,state,svc in rows:self.scan_tree.insert("","end",values=(port,state,svc))
            self.log_ui(f"Port scan completed: {host}")
        self.async_task(lambda:scan(host),done)

    def show_text(self,title,text):
        win=tk.Toplevel(self); win.title(title); win.geometry("780x520"); win.configure(bg=self.BG)
        box=tk.Text(win,bg="#081321",fg=self.TEXT,insertbackground="white",wrap="word",font=("Consolas",9))
        box.pack(fill="both",expand=True,padx=10,pady=10); box.insert("1.0",text); box.configure(state="disabled")

    def show_output(self,title,func):
        def done(r,e):
            if e:self.show_error(title,e)
            else:self.show_text(title,r)
        self.async_task(func,done)

    def show_processes(self):
        def work():
            rows=running_processes()
            return "\n".join(f"{x.get('ProcessName','')} | PID {x.get('Id','')} | CPU {x.get('CPU','')} | RAM {int(x.get('WorkingSet64') or 0)//1024} KB" for x in rows)
        self.show_output("Running Processes",work)

    def show_startup(self):
        def work():
            rows=startup_items()
            return "\n\n".join(f"{x.get('Name','')}\nUser: {x.get('User','')}\nLocation: {x.get('Location','')}\nCommand: {x.get('Command','')}" for x in rows) or "No startup entries returned."
        self.show_output("Startup Items",work)

    def clean_temp(self):
        if not self.confirm_action("Temporary File Cleanup","Windows TEMP folder-এর যেসব file locked নয় সেগুলো delete করার চেষ্টা করবে। Continue?"):return
        def done(r,e):
            if e:self.show_error("Cleanup",e)
            else:self.log_ui(f"Temp cleanup: removed {r[0]} entries, skipped {r[1]}"); messagebox.showinfo("Cleanup",f"Removed: {r[0]}\nSkipped: {r[1]}")
        self.async_task(cleanup_temp,done)

    def open_log(self):
        if not os.path.exists(LOG_PATH): log("Activity log created")
        try: os.startfile(LOG_PATH)
        except Exception as e:self.show_error("Log",e)

if __name__=="__main__":
    if os.name!="nt":
        print("CyberShield Toolkit is designed for Windows 10/11.")
    CyberShield().mainloop()
