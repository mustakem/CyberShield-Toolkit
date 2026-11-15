# CyberShield Toolkit: বাংলায় ব্যবহার ও ব্যাখ্যা

## এই build-এ কী আছে
1. **Firewall:** Domain, Private, Public profile-এর status দেখায়। `ENABLE` চাপলে Firewall চালু করে। নিরাপত্তার জন্য Firewall OFF button রাখা হয়নি।
2. **Microsoft Defender:** Antivirus, Real-time Protection ও AM Service-এর status দেখায়। এখানে Defender বন্ধ করার control নেই।
3. **Remote Desktop (RDP):** `TOGGLE` দিয়ে ON/OFF করা যায়। পরিবর্তনের আগে confirmation আসে।
4. **AnyDesk / TeamViewer / RustDesk / Chrome Remote Desktop:** পরিচিত process চলছে কি না দেখায়। `OFF / STOP` process বন্ধ করার চেষ্টা করে। `ON / START` common install location-এ executable পেলে চালু করে।
5. **Wi-Fi:** প্রথম detect হওয়া wireless adapter ON/OFF করে।
6. **Flush DNS:** Windows DNS cache পরিষ্কার করে।
7. **Port Scanner:** localhost default; common TCP port scan করে। অন্য host হলে কেবল অনুমোদিত host ব্যবহার করবে।
8. **Network Tools:** IP configuration, ping, traceroute।
9. **PC Maintenance:** System information, running processes, startup items, temporary folder cleanup।
10. **Activity Log:** কাজের history `%LOCALAPPDATA%\\CyberShieldToolkit\\activity.log`-এ।

## চালানো
Windows 10/11-এ Python 3.10+ ইনস্টল করা থাকলে ZIP extract করে `scripts\\build_portable_windows.bat`-এ double-click করো। Build সফল হলে `dist\\CyberShieldToolkit.exe` হবে।

## PowerShell window
PowerShell, ipconfig, ping ও tracert subprocess hidden/no-console mode-এ চালু হয়। তাই কালো console window সামনে আসার কথা নয়। UAC prompt আলাদা Windows security prompt; system-level পরিবর্তনে এটি স্বাভাবিক।

## গুরুত্বপূর্ণ সীমাবদ্ধতা
- ZIP-এর মধ্যে source code আছে, compiled EXE নেই। Windows EXE build Windows-এ চালাতে হবে।
- এখানে Python syntax পরীক্ষা করা যায়, কিন্তু Windows machine-এ বাস্তব পরীক্ষা করা হয়নি।
- Remote app STOP শুধু পরিচিত process বন্ধ করে। Service, scheduled task, portable copy, alternate remote tool বা malware access শতভাগ বন্ধ করার নিশ্চয়তা দেয় না।
- Defender status-only; Firewall enable-only।
- Admin permission ছাড়া RDP, Wi-Fi ও Firewall system changes করা যাবে না।
- প্রথমে test PC-তে পরীক্ষা করো।


## নতুন: Taskbar Apps
- `Taskbar Apps` tab-এ Windows-এর visible top-level app window-গুলো title ও PID-সহ দেখায়।
- `REFRESH WINDOWS` তালিকা নতুন করে আনে।
- কোনো app select করে `CLOSE SELECTED APP` চাপলে graceful close request পাঠায়। আগে unsaved কাজ save করতে হবে।
- এটা Windows-এর আসল taskbar-এর replacement নয়; visible window list। System/shell process বন্ধ করার চেষ্টা block করা হয়েছে।

## নতুন: Hardware Details
- `SCAN HARDWARE` চাপলে CPU model, manufacturer, core/thread count, clock speed, system/motherboard info এবং প্রতিটি RAM module-এর slot, manufacturer, part number, capacity, reported speed, configured speed দেখায়।
- RAM CL (CAS Latency) সাধারণ Windows CIM/WMI query-তে নির্ভরযোগ্যভাবে পাওয়া যায় না। তাই এখানে CL-এর জায়গায় limitation দেখানো হয়, ভুল CL বানিয়ে দেখানো হয় না। CL বের করতে compatible SPD reader / vendor tool / BIOS data লাগতে পারে।

## নতুন: IP Refresh / Renew
- `Network Tools` tab-এ `REFRESH / RENEW IP` button DHCP IP release করে আবার renew করে।
- কাজের সময় কয়েক মুহূর্তের জন্য network disconnect হতে পারে এবং Administrator permission লাগে।
- এটি DHCP থেকে পাওয়া Local IP renew করে। Public IP পরিবর্তন নিশ্চিত করে না; ISP/router-এর public IP আলাদা বিষয়।

## HWiNFO-এর মতো Hardware Inventory
- `Hardware Details` tab-এ CPU, RAM module, motherboard, BIOS, graphics adapter এবং storage model/capacity দেখায়, Windows CIM/WMI যতটুকু তথ্য দেয়।
- Live temperature, fan RPM, voltage এবং সব sensor-এর তথ্য standard Windows interface থেকে সব PC-তে পাওয়া যায় না। তাই HWiNFO-এর সম্পূর্ণ sensor panel-এর সমতুল্য নয়।

## RAM SPD Inspector
- `RAM SPD` tab RAM-এর manufacturer, part number, serial, capacity, reported speed, configured speed, form factor ইত্যাদি read-only দেখায়।
- Part Number field-টি display/notes-এর জন্য; এখানে edit করলে RAM-এর SPD chip পরিবর্তন হয় না।
- `WRITE TO SPD` disabled রাখা হয়েছে। Generic Windows CIM/WMI দিয়ে নিরাপদে SPD EEPROM লেখা যায় না; motherboard, memory controller, SPD hub/chip এবং module-specific support যাচাই ছাড়া write করলে RAM boot failure হতে পারে। Write-protection bypass বা blind write এই build-এ নেই।
