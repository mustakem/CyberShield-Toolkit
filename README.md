# CyberShield Toolkit

[![Windows Build](https://github.com/mustakem/CyberShield-Toolkit/actions/workflows/windows-build.yml/badge.svg)](https://github.com/mustakem/CyberShield-Toolkit/actions/workflows/windows-build.yml)

**CyberShield Toolkit v1.0.0** is a Windows 10/11 desktop utility for network diagnostics, system maintenance, and hardware inventory.

## Download for Windows

**[Download CyberShieldToolkit.exe](https://github.com/mustakem/CyberShield-Toolkit/releases/download/v1.0.0/CyberShieldToolkit.exe)**

The EXE will appear in the v1.0.0 Release assets after the Windows build finishes. No Python installation is required for end users.

[View all Releases](https://github.com/mustakem/CyberShield-Toolkit/releases)

## Features

- Network diagnostics, common TCP port scanner, ping and traceroute
- DHCP IP release/renew, IP configuration, Wi-Fi and DNS tools
- Windows Firewall status and enable control
- Microsoft Defender status (read-only)
- Remote Desktop controls
- Remote-support app detection and process controls
- Visible application window list and graceful close request
- PC maintenance and hardware inventory
- Read-only RAM SPD information

## Build

The GitHub Actions workflow builds a single-file, windowed Windows executable from:
`CyberShield_Complete_Portable/src/cybershield_toolkit.py`

## Important limitations

- Windows 10/11 only.
- Defender is read-only; Firewall control is enable-only.
- DHCP renew may briefly interrupt connectivity and does not guarantee a public IP change.
- Remote-support process termination does not guarantee all remote access paths are disabled.
- RAM SPD inspection is read-only. SPD EEPROM writing is not implemented.
- Temperature, fan speed, voltage, and other live sensors are not available on every PC through standard Windows interfaces.
- Scan only systems you own or are authorized to test.
- This is an initial release; test before production use.

See [Bangla guide](CyberShield_Complete_Portable/EXPLANATION_BN.md) for usage details and [MIT License](LICENSE).
