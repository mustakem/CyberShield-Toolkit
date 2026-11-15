# CyberShield Toolkit Complete Portable GUI - Md. Mustakem (Dubai, UAE)

A consolidated Windows 10/11 desktop GUI prototype.

## Features in this build
- Dashboard with Firewall, Microsoft Defender, RDP, remote-support apps and Wi-Fi status
- Firewall status and safe Enable action
- Defender status (read-only)
- RDP enable/disable with confirmation
- AnyDesk, TeamViewer, RustDesk and Chrome Remote Desktop process detection; Stop and Launch controls where known install paths are found
- Wi-Fi adapter enable/disable
- Flush DNS
- Common TCP port scan (localhost default; authorized targets only)
- IP configuration, Ping, Traceroute
- System information, running process viewer, startup item viewer
- Temporary-file cleanup with confirmation
- Activity log

## Build
On Windows 10/11, install Python 3.10+ once, extract this ZIP, then double-click:
`scripts\build_portable_windows.bat`
The portable EXE is created at `dist\CyberShieldToolkit.exe`.

## Important limitations
- This source package is not itself a compiled Windows EXE. Windows EXE compilation must run on Windows.
- Tested here for Python syntax only, not on Windows runtime.
- Defender controls are status-only. Firewall can be enabled, not disabled.
- Remote app STOP closes known running processes only. START launches from common install paths. This does not uninstall apps, disable every associated service, or guarantee all remote access is blocked.
- Wi-Fi, RDP and firewall changes require Administrator privileges. UAC is a normal Windows security prompt.
- Port scanner is limited to a short list of common TCP ports.
- Use only on computers and networks you own or are authorized to administer.

- Taskbar Apps tab: list visible application windows and request graceful close of a selected app.
- Hardware Details tab: CPU, motherboard and per-RAM-module manufacturer, part number, capacity and reported speeds.
- CAS Latency (CL) is not reliably available through standard Windows CIM/WMI; the app clearly reports this limitation rather than inventing it.
- DHCP IP refresh: release/renew all DHCP-enabled adapters, then display refreshed IP configuration (brief network interruption; Administrator required).
- Expanded hardware inventory: CPU, RAM identifiers, motherboard, BIOS, graphics and storage where Windows CIM/WMI reports them.
- RAM SPD Inspector: read-only module information. SPD writing is intentionally unavailable in this generic build because Windows CIM/WMI has no universal safe SPD write API.
