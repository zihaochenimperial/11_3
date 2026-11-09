# host-pump.ps1 v3 -- Windows-host job pump for the Gaussian file queue (ASCII only, PS 5.1 + 7 compatible).
# Start via scripts\start-pump-loop.cmd. Executes ONLY whitelisted job types found in queue\inbox\*.json.
# Types: hostinfo | gpuinfo | slotprobe | contention | worker | pyinstall | venv | pip | py
# Results: queue\done\<job_id>.result.json ; heartbeat: runs\pump\heartbeat.json ; log: runs\pump\pump.log
# Stop: file queue\STOP.  Restart with new code: file queue\RESTART (start-pump-loop.cmd relaunches).
param([int]$MaxConcurrent = 2, [int]$PollSeconds = 3)
$ErrorActionPreference = 'Continue'
$PumpVersion = 'v3'
$root = Split-Path -Parent $PSScriptRoot
$q = Join-Path $root 'queue'
foreach ($d in 'inbox', 'running', 'done') { New-Item -ItemType Directory -Force -Path (Join-Path $q $d) | Out-Null }
$pumpDir = Join-Path $root 'runs\pump'
New-Item -ItemType Directory -Force -Path $pumpDir | Out-Null
$tmpDir = Join-Path $root '.tmp'; $cacheDir = Join-Path $root '.cache'; $pipCache = Join-Path $root '.pipcache'
foreach ($d in $tmpDir, $cacheDir, $pipCache) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
$env:TEMP = $tmpDir; $env:TMP = $tmpDir; $env:PIP_CACHE_DIR = $pipCache
$env:TORCH_HOME = (Join-Path $cacheDir 'torch'); $env:HF_HOME = (Join-Path $cacheDir 'hf'); $env:PYTHONDONTWRITEBYTECODE = '1'
$logFile = Join-Path $pumpDir 'pump.log'
if ($MaxConcurrent -lt 1 -or $MaxConcurrent -gt 5) { throw 'MaxConcurrent must be 1..5' }
$runWorker = Join-Path $PSScriptRoot 'run-worker.ps1'
$venvPy = Join-Path $root '.venv\Scripts\python.exe'
$validRoles = 'literature-scout', 'code-mapper', 'repro-engineer', 'result-auditor'
$argPattern = '^[A-Za-z0-9_.:=,\\/\-\+]+$'
$allowedPkgs = 'numpy', 'scipy', 'torch', 'torchvision', 'pillow', 'matplotlib', 'pandas', 'pytest', 'scikit-image', 'tqdm', 'imageio', 'opencv-python-headless', 'scikit-learn'
$allowedIndex = 'https://download.pytorch.org/whl/cu121', 'https://download.pytorch.org/whl/cpu', 'https://pypi.org/simple'

function Log([string]$m) { Add-Content -LiteralPath $logFile -Value ('{0} {1}' -f [DateTime]::UtcNow.ToString('o'), $m) -Encoding UTF8 }
function WriteJson([string]$path, $obj) { ($obj | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $path -Encoding UTF8 }
function PsExe { if ($PSVersionTable.PSEdition -eq 'Core') { (Get-Process -Id $PID).Path } else { 'powershell.exe' } }
function Start-Proc([string]$exe, [string[]]$argList, [string]$outF, [string]$errF) {
    return Start-Process -FilePath $exe -ArgumentList $argList -PassThru -WindowStyle Hidden -RedirectStandardOutput $outF -RedirectStandardError $errF -WorkingDirectory $root
}

$pumpMutex = New-Object Threading.Mutex($false, 'Local\Gaussian_HostPump')
$got = $false
try { $got = $pumpMutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $got = $true }
if (-not $got) { Write-Output 'Another Gaussian pump is already running.'; return }
Remove-Item -LiteralPath (Join-Path $q 'STOP') -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $q 'RESTART') -ErrorAction SilentlyContinue

function Get-GpuInfo {
    $o = [ordered]@{}
    $smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if ($smi) {
        try { $o.gpu = ((& nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,driver_version --format=csv,noheader 2>&1) | Out-String).Trim() } catch { $o.gpu = 'err' }
        try { $o.gpu_process_count = @(((& nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>&1) | Out-String).Trim() -split "`n" | Where-Object { $_.Trim() }).Count } catch { $o.gpu_process_count = 'err' }
    } else { $o.gpu = 'nvidia-smi not found' }
    $o.ml_procs = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match 'python|torch|ollama|opencode' } | ForEach-Object { '{0}:{1}' -f $_.ProcessName, $_.Id })
    return $o
}

function Get-HostInfo {
    $o = [ordered]@{}
    $o.utc = [DateTime]::UtcNow.ToString('o')
    $o.pump_version = $PumpVersion
    $o.ps_version = $PSVersionTable.PSVersion.ToString()
    $o.os = [Environment]::OSVersion.VersionString
    $o.logical_cpus = [Environment]::ProcessorCount
    try { $o.ram_gb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1) } catch { $o.ram_gb = 'err' }
    try { $o.d_free_gb = [math]::Round((Get-PSDrive -Name D).Free / 1GB, 1) } catch { $o.d_free_gb = 'err' }
    $o.opencode_cmd_exists = Test-Path -LiteralPath 'C:\Users\USER\AppData\Local\Programs\node-v24.21.0\opencode.cmd'
    $o.credential_file_exists = Test-Path -LiteralPath (Join-Path $env:USERPROFILE '.codex\local-credentials\opencode-go-key.dpapi')
    $o.venv_exists = Test-Path -LiteralPath $venvPy
    $g = Get-GpuInfo
    foreach ($k in $g.Keys) { $o[$k] = $g[$k] }
    $pc = Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pc) { $o.python_on_path = $pc.Source } else { $o.python_on_path = 'none' }
    if (Get-Command py -ErrorAction SilentlyContinue) { try { $o.py_launcher = ((& py -0p 2>&1) | Out-String).Trim() } catch { $o.py_launcher = 'err' } } else { $o.py_launcher = 'py launcher not found' }
    $cands = @()
    foreach ($pat in (Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python3*\python.exe'), 'C:\Program Files\Python3*\python.exe', 'C:\Python3*\python.exe', (Join-Path $root '.tools\python3*\python.exe'), (Join-Path $env:USERPROFILE 'miniconda3\python.exe'), (Join-Path $env:USERPROFILE 'anaconda3\python.exe')) {
        $cands += @(Get-ChildItem -Path $pat -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
    }
    $o.python_candidates = $cands
    try { $o.appx_python = @(Get-AppxPackage -Name '*Python*' -ErrorAction SilentlyContinue | ForEach-Object { $_.PackageFullName }) } catch { $o.appx_python = 'err' }
    return $o
}

function Resolve-TaskJob($job) {
    $role = if ($job.role) { [string]$job.role } else { 'literature-scout' }
    if ($validRoles -notcontains $role) { throw 'bad role' }
    $taskRel = if ($job.task_file) { [string]$job.task_file } else { 'tasks\000-smoke.md' }
    $taskFull = (Resolve-Path -LiteralPath (Join-Path $root $taskRel)).Path
    if (-not $taskFull.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'task outside root' }
    return @{ role = $role; task = $taskFull }
}
function Start-WorkerProc([string]$taskFull, [string]$role, [string]$outF, [string]$errF, [switch]$Probe, [int]$Hold = 0) {
    $a2 = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $runWorker + '"'), '-TaskFile', ('"' + $taskFull + '"'), '-Role', $role)
    if ($Probe) { $a2 += '-SlotProbe'; if ($Hold -gt 0) { $a2 += @('-SlotHoldSeconds', "$Hold") } }
    return Start-Proc (PsExe) $a2 $outF $errF
}

$active = @{}
Log ('pump {0} start pid={1} max={2} ps={3} root={4}' -f $PumpVersion, $PID, $MaxConcurrent, $PSVersionTable.PSVersion, $root)
Write-Output ('Gaussian host pump {0} running (max {1}). queue\STOP stops, queue\RESTART restarts.' -f $PumpVersion, $MaxConcurrent)
while ($true) {
    WriteJson (Join-Path $pumpDir 'heartbeat.json') @{ version = $PumpVersion; pid = $PID; utc = [DateTime]::UtcNow.ToString('o'); active = @($active.Keys); max_concurrent = $MaxConcurrent; ps = $PSVersionTable.PSVersion.ToString() }
    foreach ($id in @($active.Keys)) {
        $a = $active[$id]
        if ((-not $a.proc.HasExited) -and $a.deadline -and ([DateTime]::UtcNow -gt $a.deadline)) {
            $a.timed_out = $true
            & taskkill.exe /PID $a.proc.Id /T /F | Out-Null
            Log ('job {0} exceeded max_seconds, killed' -f $id)
            Start-Sleep -Milliseconds 700
        }
        if ($a.proc.HasExited) {
            $code = $a.proc.ExitCode
            WriteJson (Join-Path $q ("done\" + $id + '.result.json')) @{ job_id = $id; type = $a.type; exit_code = $code; timed_out = $a.timed_out; stdout = $a.out; stderr = $a.err; started_utc = $a.started; finished_utc = [DateTime]::UtcNow.ToString('o') }
            Remove-Item -LiteralPath (Join-Path $q ("running\" + $id + '.json')) -ErrorAction SilentlyContinue
            $active.Remove($id)
            Log ('job {0} finished exit={1} timed_out={2}' -f $id, $code, $a.timed_out)
        }
    }
    $stopping = (Test-Path -LiteralPath (Join-Path $q 'STOP')) -or (Test-Path -LiteralPath (Join-Path $q 'RESTART'))
    if ($stopping) {
        if ($active.Count -eq 0) { Log 'STOP/RESTART seen, exiting'; break }
    } else {
        foreach ($f in (Get-ChildItem -LiteralPath (Join-Path $q 'inbox') -Filter *.json -ErrorAction SilentlyContinue | Sort-Object Name)) {
            try {
                $job = Get-Content -LiteralPath $f.FullName -Raw | ConvertFrom-Json
                $id = [string]$job.job_id
                if ($id -notmatch '^[A-Za-z0-9_\-]+$') { throw 'bad job_id' }
                $type = [string]$job.type
                $resPath = Join-Path $q ("done\" + $id + '.result.json')
                $runDir = Join-Path $pumpDir $id
                $claim = Join-Path $q ("running\" + $id + '.json')
                if ($type -eq 'hostinfo' -or $type -eq 'gpuinfo') {
                    Move-Item -LiteralPath $f.FullName -Destination $claim -Force
                    $inf = if ($type -eq 'hostinfo') { Get-HostInfo } else { Get-GpuInfo }
                    WriteJson $resPath @{ job_id = $id; type = $type; exit_code = 0; info = $inf }
                    Remove-Item -LiteralPath $claim -ErrorAction SilentlyContinue
                    Log "job $id $type done"
                    continue
                }
                if ($active.Count -ge $MaxConcurrent -and $type -ne 'contention') { continue }
                $started = [DateTime]::UtcNow.ToString('o')
                if ($type -eq 'worker' -or $type -eq 'slotprobe') {
                    $tj = Resolve-TaskJob $job
                    New-Item -ItemType Directory -Force -Path $runDir | Out-Null
                    Move-Item -LiteralPath $f.FullName -Destination $claim -Force
                    $o = Join-Path $runDir 'stdout.log'; $e = Join-Path $runDir 'stderr.log'
                    if ($type -eq 'worker') { $p = Start-WorkerProc $tj.task $tj.role $o $e } else { $p = Start-WorkerProc $tj.task $tj.role $o $e -Probe }
                    $null = $p.Handle
                    $active[$id] = @{ proc = $p; type = $type; out = $o; err = $e; started = $started; deadline = $null; gpu = $false; timed_out = $false }
                    Log ('job {0} {1} role={2} started pid={3}' -f $id, $type, $tj.role, $p.Id)
                } elseif ($type -eq 'contention') {
                    $tj = Resolve-TaskJob $job
                    $n = if ($job.n) { [int]$job.n } else { 6 }
                    if ($n -lt 2 -or $n -gt 8) { throw 'n out of range' }
                    $hold = if ($job.hold_seconds) { [int]$job.hold_seconds } else { 25 }
                    New-Item -ItemType Directory -Force -Path $runDir | Out-Null
                    Move-Item -LiteralPath $f.FullName -Destination $claim -Force
                    $procs = @()
                    for ($k = 0; $k -lt $n; $k++) {
                        $o = Join-Path $runDir ("p$k.out"); $e = Join-Path $runDir ("p$k.err")
                        $p = Start-WorkerProc $tj.task $tj.role $o $e -Probe -Hold $hold
                        $null = $p.Handle
                        $procs += @{ k = $k; proc = $p; out = $o; err = $e }
                    }
                    $deadline = (Get-Date).AddSeconds($hold + 40)
                    while (((Get-Date) -lt $deadline) -and (@($procs | Where-Object { -not $_.proc.HasExited }).Count -gt 0)) {
                        Start-Sleep -Milliseconds 500
                        WriteJson (Join-Path $pumpDir 'heartbeat.json') @{ version = $PumpVersion; pid = $PID; utc = [DateTime]::UtcNow.ToString('o'); active = @($active.Keys); note = 'contention test running' }
                    }
                    $rows = @()
                    foreach ($pp in $procs) {
                        $so = if (Test-Path -LiteralPath $pp.out) { (Get-Content -LiteralPath $pp.out -Raw) } else { '' }
                        $se = if (Test-Path -LiteralPath $pp.err) { (Get-Content -LiteralPath $pp.err -Raw) } else { '' }
                        $ec = if ($pp.proc.HasExited) { $pp.proc.ExitCode } else { 'still-running' }
                        $rows += @{ k = $pp.k; exit_code = $ec; stdout = "$so".Trim(); stderr_head = ("$se".Trim() -replace '\s+', ' ') }
                    }
                    WriteJson $resPath @{ job_id = $id; type = $type; n = $n; hold_seconds = $hold; started_utc = $started; finished_utc = [DateTime]::UtcNow.ToString('o'); processes = $rows }
                    Remove-Item -LiteralPath $claim -ErrorAction SilentlyContinue
                    Log "job $id contention done"
                } elseif ($type -eq 'venv') {
                    $base = [string]$job.base_python
                    if ((-not (Test-Path -LiteralPath $base)) -or ($base -notmatch 'python\.exe$') -or ($base -match 'WindowsApps')) { throw 'bad base_python (must exist, be python.exe, not a WindowsApps stub)' }
                    New-Item -ItemType Directory -Force -Path $runDir | Out-Null
                    Move-Item -LiteralPath $f.FullName -Destination $claim -Force
                    $o = Join-Path $runDir 'stdout.log'; $e = Join-Path $runDir 'stderr.log'
                    $p = Start-Proc $base @('-m', 'venv', ('"' + (Join-Path $root '.venv') + '"')) $o $e
                    $null = $p.Handle
                    $active[$id] = @{ proc = $p; type = $type; out = $o; err = $e; started = $started; deadline = [DateTime]::UtcNow.AddSeconds(900); gpu = $false; timed_out = $false }
                    Log ('job {0} venv started base={1}' -f $id, $base)
                } elseif ($type -eq 'pyinstall') {
                    $ver = [string]$job.version
                    if ($ver -notmatch '^3\.12\.[0-9]{1,2}$') { throw 'python version not allowed (3.12.x only)' }
                    $instScript = Join-Path $PSScriptRoot 'install-python.ps1'
                    if (-not (Test-Path -LiteralPath $instScript)) { throw 'install-python.ps1 missing' }
                    New-Item -ItemType Directory -Force -Path $runDir | Out-Null
                    Move-Item -LiteralPath $f.FullName -Destination $claim -Force
                    $o = Join-Path $runDir 'stdout.log'; $e = Join-Path $runDir 'stderr.log'
                    $p = Start-Proc (PsExe) @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $instScript + '"'), '-Version', $ver) $o $e
                    $null = $p.Handle
                    $active[$id] = @{ proc = $p; type = $type; out = $o; err = $e; started = $started; deadline = [DateTime]::UtcNow.AddSeconds(1200); gpu = $false; timed_out = $false }
                    Log ('job {0} pyinstall started version={1}' -f $id, $ver)
                } elseif ($type -eq 'pip') {
                    if (-not (Test-Path -LiteralPath $venvPy)) { throw 'venv python missing; run a venv job first' }
                    $pk = @()
                    foreach ($x in @($job.packages)) {
                        $sx = [string]$x
                        if ($sx -notmatch '^([A-Za-z0-9_.\-]+)(==[0-9][0-9A-Za-z.+]*)?$') { throw ('bad package spec: ' + $sx) }
                        $nm = ([regex]::Match($sx, '^([A-Za-z0-9_.\-]+)')).Groups[1].Value.ToLower()
                        if ($allowedPkgs -notcontains $nm) { throw ('package not allowlisted: ' + $nm) }
                        $pk += $sx
                    }
                    if ($pk.Count -lt 1) { throw 'no packages' }
                    $pa = @('-m', 'pip', 'install', '--no-input', '--disable-pip-version-check')
                    if ($job.index_url) {
                        if ($allowedIndex -notcontains [string]$job.index_url) { throw 'index_url not allowlisted' }
                        $pa += @('--index-url', [string]$job.index_url)
                    }
                    $pa += $pk
                    New-Item -ItemType Directory -Force -Path $runDir | Out-Null
                    Move-Item -LiteralPath $f.FullName -Destination $claim -Force
                    $o = Join-Path $runDir 'stdout.log'; $e = Join-Path $runDir 'stderr.log'
                    $p = Start-Proc $venvPy $pa $o $e
                    $null = $p.Handle
                    $active[$id] = @{ proc = $p; type = $type; out = $o; err = $e; started = $started; deadline = [DateTime]::UtcNow.AddSeconds(3600); gpu = $false; timed_out = $false }
                    Log ('job {0} pip started: {1}' -f $id, ($pk -join ' '))
                } elseif ($type -eq 'py') {
                    if (-not (Test-Path -LiteralPath $venvPy)) { throw 'venv python missing; run a venv job first' }
                    $scriptFull = (Resolve-Path -LiteralPath (Join-Path $root ([string]$job.script))).Path
                    $okDir = $false
                    foreach ($sd in 'src\', 'experiments\', 'tests\', 'scripts\') { if ($scriptFull.StartsWith((Join-Path $root $sd), [StringComparison]::OrdinalIgnoreCase)) { $okDir = $true } }
                    if ((-not $okDir) -or ($scriptFull -notmatch '\.py$')) { throw 'script not allowed (must be .py under src/experiments/tests/scripts)' }
                    $argv = @()
                    if ($job.args) { foreach ($x in @($job.args)) { $sx = [string]$x; if ($sx -notmatch $argPattern) { throw ('bad arg: ' + $sx) }; $argv += $sx } }
                    $maxSec = if ($job.max_seconds) { [int]$job.max_seconds } else { 1800 }
                    if ($maxSec -lt 1 -or $maxSec -gt 14400) { throw 'max_seconds out of range' }
                    $isGpu = [bool]$job.gpu
                    if ($isGpu -and (@($active.Values | Where-Object { $_.gpu }).Count -gt 0)) { continue }
                    New-Item -ItemType Directory -Force -Path $runDir | Out-Null
                    if ($isGpu) { try { ((& nvidia-smi 2>&1) | Out-String) | Set-Content -LiteralPath (Join-Path $runDir 'nvidia_smi_before.txt') -Encoding UTF8 } catch {} }
                    Move-Item -LiteralPath $f.FullName -Destination $claim -Force
                    $o = Join-Path $runDir 'stdout.log'; $e = Join-Path $runDir 'stderr.log'
                    $p = Start-Proc $venvPy (@('-u', ('"' + $scriptFull + '"')) + $argv) $o $e
                    $null = $p.Handle
                    $active[$id] = @{ proc = $p; type = $type; out = $o; err = $e; started = $started; deadline = [DateTime]::UtcNow.AddSeconds($maxSec); gpu = $isGpu; timed_out = $false }
                    Log ('job {0} py {1} gpu={2} max_s={3} pid={4}' -f $id, $scriptFull, $isGpu, $maxSec, $p.Id)
                } else { throw "unsupported job type: $type" }
            } catch {
                $msg = $_.Exception.Message
                $idr = [IO.Path]::GetFileNameWithoutExtension($f.Name)
                Log ('job file {0} rejected: {1}' -f $f.Name, $msg)
                WriteJson (Join-Path $q ("done\" + $idr + '.result.json')) @{ job_id = $idr; exit_code = -1; error = $msg }
                Remove-Item -LiteralPath $f.FullName -ErrorAction SilentlyContinue
                Remove-Item -LiteralPath (Join-Path $q ("running\" + $idr + '.json')) -ErrorAction SilentlyContinue
            }
        }
    }
    Start-Sleep -Seconds $PollSeconds
}
$pumpMutex.ReleaseMutex(); $pumpMutex.Dispose()
