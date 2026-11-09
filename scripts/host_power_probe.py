"""READ-ONLY host power/affinity probe (no setting is changed). Writes outputs/host_power_probe.json."""
import json, subprocess, os, ctypes, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
res = {}
def ps(cmd, t=30):
    try:
        return subprocess.run(['powershell', '-NoProfile', '-Command', cmd], capture_output=True, text=True, timeout=t).stdout.strip()
    except Exception as ex:
        return 'ERR %r' % (ex,)
res['powercfg_active'] = subprocess.run(['powercfg', '/getactivescheme'], capture_output=True, text=True).stdout.strip()
res['battery'] = ps('Get-CimInstance Win32_Battery | Select-Object BatteryStatus,EstimatedChargeRemaining,EstimatedRunTime | ConvertTo-Json -Compress')
res['power_status_kernel32'] = None
class SPS(ctypes.Structure):
    _fields_ = [('ACLineStatus', ctypes.c_ubyte), ('BatteryFlag', ctypes.c_ubyte), ('BatteryLifePercent', ctypes.c_ubyte), ('SystemStatusFlag', ctypes.c_ubyte), ('BatteryLifeTime', ctypes.c_ulong), ('BatteryFullLifeTime', ctypes.c_ulong)]
s = SPS(); ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))
res['power_status_kernel32'] = dict(ACLineStatus=s.ACLineStatus, BatteryFlag=s.BatteryFlag, BatteryLifePercent=s.BatteryLifePercent, SystemStatusFlag=s.SystemStatusFlag)
res['processor'] = ps('Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,CurrentClockSpeed,MaxClockSpeed | ConvertTo-Json -Compress')
res['power_mode_overlay'] = ps("(Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Power\\User\\PowerSchemes' -ErrorAction SilentlyContinue | Select-Object ActiveOverlayAcPowerScheme,ActiveOverlayDcPowerScheme | ConvertTo-Json -Compress)")
res['proc_throttle_max_ac_dc'] = ps("powercfg /q SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX | Out-String")[-400:]
res['proc_boost_mode'] = ps("powercfg /q SCHEME_CURRENT SUB_PROCESSOR PERFBOOSTMODE | Out-String")[-400:]
k = ctypes.windll.kernel32; h = k.GetCurrentProcess()
res['priority_class_hex'] = hex(k.GetPriorityClass(h))
pm = ctypes.c_size_t(); sm = ctypes.c_size_t(); k.GetProcessAffinityMask(h, ctypes.byref(pm), ctypes.byref(sm))
res['affinity_mask'] = bin(pm.value); res['system_mask'] = bin(sm.value)
class PT(ctypes.Structure):
    _fields_ = [('Version', ctypes.c_ulong), ('ControlMask', ctypes.c_ulong), ('StateMask', ctypes.c_ulong)]
pt = PT(); pt.Version = 1
ok = k.GetProcessInformation(h, 4, ctypes.byref(pt), ctypes.sizeof(pt))   # ProcessPowerThrottling = 4
res['power_throttling_query'] = dict(ok=int(ok), Control=pt.ControlMask, State=pt.StateMask)
Path(ROOT, 'outputs', 'host_power_probe.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
print(json.dumps(res, indent=1))
