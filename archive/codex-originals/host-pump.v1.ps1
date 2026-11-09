# host-pump.ps1 -- Windows-host job pump for the Gaussian file queue (ASCII only, PS 5.1 + 7 compatible).
# Start once by double-clicking scripts\start-pump.cmd. Executes ONLY whitelisted job types found in queue\inbox\*.json.
# Job JSON: {"job_id":"x","type":"hostinfo|slotprobe|contention|worker","role":"...","task_file":"tasks\\000-smoke.md","run_id":"..."}
# Results: queue\done\<job_id>.result.json ; heartbeat: runs\pump\heartbeat.json ; log: runs\pump\pump.log
# Stop: create file queue\STOP (pump exits after active jobs finish).
param([int]$MaxConcurrent = 2, [int]$PollSeconds = 3)
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$q = Join-Path $root 'queue'
foreach ($d in 'inbox', 'running', 'done') { New-Item -ItemType Directory -Force -Path (Join-Path $q $d) | Out-Null }
$pumpDir = Join-Path $root 'runs\pump'
New-Item -ItemType Directory -Force -Path $pumpDir | Out-Null
$logFile = Join-Path $pumpDir 'pump.log'
if ($MaxConcurrent -lt 1 -or $MaxConcurrent -gt 5) { throw 'MaxConcurrent must be 1..5' }
$runWorker = Join-Path $PSScriptRoot 'run-worker.ps1'
$validRoles = 'literature-scout', 'code-mapper', 'repro-engineer', 'result-auditor'

function Log([string]$m) { Add-Content -LiteralPath $logFile -Value ('{0} {1}' -f [DateTime]::UtcNow.ToString('o'), $m) -Encoding UTF8 }
function WriteJson([string]$path, $obj) { ($obj | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $path -Encoding UTF8 }
function PsExe { if ($PSVersionTable.PSEdition -eq 'Core') { (Get-Process -Id $PID).Path } else { 'powershell.exe' } }

# single pump per user session
$pumpMutex = New-Object Threading.Mutex($false, 'Local\Gaussian_HostPump')
$got = $false
try { $got = $pumpMutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $got = $true }
if (-not $got) { Write-Output 'Another Gaussian pump is already running.'; return }

function Get-HostInfo {
    $o = [ordered]@{}
    $o.utc = [DateTime]::UtcNow.ToString('o')
    $o.ps_version = $PSVersionTable.PSVersion.ToString()
    $o.ps_edition = $PSVersionTable.PSEdition
    $o.os = [Environment]::OSVersion.VersionString
    $o.logical_cpus = [Environment]::ProcessorCount
    try { $o.ram_gb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1) } catch { $o.ram_gb = 'err' }
    try { $o.cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name } catch { $o.cpu = 'err' }
    try { $o.d_free_gb = [math]::Round((Get-PSDrive -Name D).Free / 1GB, 1) } catch { $o.d_free_gb = 'err' }
    $o.opencode_cmd_exists = Test-Path -LiteralPath 'C:\Users\USER\AppData\Local\Programs\node-v24.21.0\opencode.cmd'
    $o.credential_file_exists = Test-Path -LiteralPath (Join-Path $env:USERPROFILE '.codex\local-credentials\opencode-go-key.dpapi')
    $smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if ($smi) {
        try { $o.nvidia_smi = ((& nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu,driver_version --format=csv,noheader 2>&1) | Out-String).Trim() } catch { $o.nvidia_smi = 'err' }
        try { $o.gpu_compute_procs = ((& nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader 2>&1) | Out-String).Trim() } catch { $o.gpu_compute_procs = 'err' }
    } else { $o.nvidia_smi = 'nvidia-smi not found' }
    $py = Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($py) { $o.python = $py.Source } else { $o.python = 'not on PATH' }
    $o.related_procs = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match 'python|opencode|node|ollama' } | ForEach-Object { '{0}:{1}' -f $_.ProcessName, $_.Id })
    return $o
}

function Start-WorkerProc([string]$taskFull, [string]$role, [string]$outF, [string]$errF, [switch]$Probe, [int]$Hold = 0) {
    $args2 = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $runWorker + '"'), '-TaskFile', ('"' + $taskFull + '"'), '-Role', $role)
    if ($Probe) { $args2 += '-SlotProbe'; if ($Hold -gt 0) { $args2 += @('-SlotHoldSeconds', "$Hold") } }
    return Start-Process -FilePath (PsExe) -ArgumentList $args2 -PassThru -WindowStyle Hidden -RedirectStandardOutput $outF -RedirectStandardError $errF
}

$active = @{}
Log ('pump start pid={0} max={1} ps={2} root={3}' -f $PID, $MaxConcurrent, $PSVersionTable.PSVersion, $root)
Write-Output ('Gaussian host pump running (max {0}). Create queue\STOP to stop.' -f $MaxConcurrent)
while ($true) {
    WriteJson (Join-Path $pumpDir 'heartbeat.json') @{ pid = $PID; utc = [DateTime]::UtcNow.ToString('o'); active = @($active.Keys); max_concurrent = $MaxConcurrent; ps = $PSVersionTable.PSVersion.ToString() }
    foreach ($id in @($active.Keys)) {
        $a = $active[$id]
        if ($a.proc.HasExited) {
            $code = $a.proc.ExitCode
            WriteJson (Join-Path $q ("done\" + $id + '.result.json')) @{ job_id = $id; type = $a.type; exit_code = $code; stdout = $a.out; stderr = $a.err; started_utc = $a.started; finished_utc = [DateTime]::UtcNow.ToString('o') }
            Remove-Item -LiteralPath (Join-Path $q ("running\" + $id + '.json')) -ErrorAction SilentlyContinue
            $active.Remove($id)
            Log ('job {0} finished exit={1}' -f $id, $code)
        }
    }
    if (Test-Path -LiteralPath (Join-Path $q 'STOP')) {
        if ($active.Count -eq 0) { Log 'STOP seen, exiting'; break }
    } else {
        foreach ($f in (Get-ChildItem -LiteralPath (Join-Path $q 'inbox') -Filter *.json -ErrorAction SilentlyContinue | Sort-Object Name)) {
            try {
                $job = Get-Content -LiteralPath $f.FullName -Raw | ConvertFrom-Json
                $id = [string]$job.job_id
                if ($id -notmatch '^[A-Za-z0-9_\-]+$') { throw 'bad job_id' }
                $type = [string]$job.type
                $resPath = Join-Path $q ("done\" + $id + '.result.json')
                $runDir = Join-Path $pumpDir $id
                if ($type -eq 'hostinfo') {
                    Move-Item -LiteralPath $f.FullName -Destination (Join-Path $q ("running\" + $id + '.json')) -Force
                    WriteJson $resPath @{ job_id = $id; type = $type; exit_code = 0; info = (Get-HostInfo) }
                    Remove-Item -LiteralPath (Join-Path $q ("running\" + $id + '.json')) -ErrorAction SilentlyContinue
                    Log "job $id hostinfo done"
                    continue
                }
                if ($active.Count -ge $MaxConcurrent -and $type -ne 'contention') { continue }
                New-Item -ItemType Directory -Force -Path $runDir | Out-Null
                $role = if ($job.role) { [string]$job.role } else { 'literature-scout' }
                if ($validRoles -notcontains $role) { throw 'bad role' }
                $taskRel = if ($job.task_file) { [string]$job.task_file } else { 'tasks\000-smoke.md' }
                $taskFull = (Resolve-Path -LiteralPath (Join-Path $root $taskRel)).Path
                if (-not $taskFull.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'task outside root' }
                Move-Item -LiteralPath $f.FullName -Destination (Join-Path $q ("running\" + $id + '.json')) -Force
                $started = [DateTime]::UtcNow.ToString('o')
                if ($type -eq 'worker') {
                    $o = Join-Path $runDir 'stdout.log'; $e = Join-Path $runDir 'stderr.log'
                    $p = Start-WorkerProc $taskFull $role $o $e
                    $null = $p.Handle
                    $active[$id] = @{ proc = $p; type = $type; out = $o; err = $e; started = $started }
                    Log "job $id worker role=$role started pid=$($p.Id)"
                } elseif ($type -eq 'slotprobe') {
                    $o = Join-Path $runDir 'stdout.log'; $e = Join-Path $runDir 'stderr.log'
                    $p = Start-WorkerProc $taskFull $role $o $e -Probe
                    $null = $p.Handle
                    $active[$id] = @{ proc = $p; type = $type; out = $o; err = $e; started = $started }
                    Log "job $id slotprobe started"
                } elseif ($type -eq 'contention') {
                    # launch N (default 6) slot-holding probes at once; with a 5-slot mutex expect exactly 5 success + (N-5) rejected
                    $n = if ($job.n) { [int]$job.n } else { 6 }
                    if ($n -lt 2 -or $n -gt 8) { throw 'n out of range' }
                    $hold = if ($job.hold_seconds) { [int]$job.hold_seconds } else { 25 }
                    $procs = @()
                    for ($k = 0; $k -lt $n; $k++) {
                        $o = Join-Path $runDir ("p$k.out"); $e = Join-Path $runDir ("p$k.err")
                        $p = Start-WorkerProc $taskFull $role $o $e -Probe -Hold $hold
                        $null = $p.Handle
                        $procs += @{ k = $k; proc = $p; out = $o; err = $e }
                    }
                    $deadline = (Get-Date).AddSeconds($hold + 40)
                    while (((Get-Date) -lt $deadline) -and (@($procs | Where-Object { -not $_.proc.HasExited }).Count -gt 0)) { Start-Sleep -Milliseconds 500; WriteJson (Join-Path $pumpDir 'heartbeat.json') @{ pid = $PID; utc = [DateTime]::UtcNow.ToString('o'); active = @($active.Keys); note = 'contention test running' } }
                    $rows = @()
                    foreach ($pp in $procs) {
                        $so = if (Test-Path -LiteralPath $pp.out) { (Get-Content -LiteralPath $pp.out -Raw) } else { '' }
                        $se = if (Test-Path -LiteralPath $pp.err) { (Get-Content -LiteralPath $pp.err -Raw) } else { '' }
                        $ec = if ($pp.proc.HasExited) { $pp.proc.ExitCode } else { 'still-running' }
                        $rows += @{ k = $pp.k; exit_code = $ec; stdout = "$so".Trim(); stderr_head = ("$se".Trim() -replace '\s+', ' ') }
                    }
                    WriteJson $resPath @{ job_id = $id; type = $type; n = $n; hold_seconds = $hold; started_utc = $started; finished_utc = [DateTime]::UtcNow.ToString('o'); processes = $rows }
                    Remove-Item -LiteralPath (Join-Path $q ("running\" + $id + '.json')) -ErrorAction SilentlyContinue
                    Log "job $id contention done"
                } else { throw "unsupported job type: $type" }
            } catch {
                $msg = $_.Exception.Message
                Log ("job file {0} rejected: {1}" -f $f.Name, $msg)
                $idr = [IO.Path]::GetFileNameWithoutExtension($f.Name)
                WriteJson (Join-Path $q ("done\" + $idr + '.result.json')) @{ job_id = $idr; exit_code = -1; error = $msg }
                Remove-Item -LiteralPath $f.FullName -ErrorAction SilentlyContinue
            }
        }
    }
    Start-Sleep -Seconds $PollSeconds
}
$pumpMutex.ReleaseMutex(); $pumpMutex.Dispose()
