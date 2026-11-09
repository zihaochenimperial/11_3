param([Parameter(Mandatory=$true)][string]$TaskFile,[ValidateSet('literature-scout','code-mapper','repro-engineer','result-auditor')][string]$Role='literature-scout',[switch]$SlotProbe,[int]$SlotHoldSeconds=0)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$taskPath=(Resolve-Path -LiteralPath $TaskFile).Path
if(-not $taskPath.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Task file must be inside Gaussian.'}
$slot=$null
for($i=0;$i -lt 5;$i++){
  $candidate=New-Object Threading.Mutex($false,('Local\Gaussian_OpenCode_Worker_'+$i))
  try{$taken=$candidate.WaitOne(0)}catch [Threading.AbandonedMutexException]{$taken=$true}
  if($taken){$slot=$candidate;break};$candidate.Dispose()
}
if($null -eq $slot){throw 'All five Gaussian worker slots occupied; queue this task and retry after a worker completes.'}
try{
  if($SlotProbe){if($SlotHoldSeconds -gt 0){Start-Sleep -Seconds $SlotHoldSeconds};Write-Output ('Slot available: '+$i);return}
  $prompt=Get-Content -LiteralPath $taskPath -Raw
  $prompt='Read D:/Gaussian/AGENTS.md. Do not spawn agents or child OpenCode processes. Work only on assigned files. Return concise evidence, actual outputs and blockers. '+($prompt -replace '\r?\n',' ')
  $run=Join-Path $root ('runs\worker-'+[guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory -Path $run | Out-Null
  @{role=$Role;task=$taskPath;slot=$i;status='running';started_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $run 'status.json')
  Push-Location $root
  $workerSuccess=$false; try{ & (Join-Path $PSScriptRoot 'opencode-provider.ps1') run --agent $Role --format json $prompt 1> (Join-Path $run 'output.jsonl') 2> (Join-Path $run 'stderr.log'); $workerSuccess=$? }catch{ ($_ | Out-String) | Add-Content -LiteralPath (Join-Path $run 'stderr.log') -Encoding UTF8; $workerSuccess=$false }finally{Pop-Location}
  if(-not $workerSuccess){@{role=$Role;task=$taskPath;slot=$i;status='failed';finished_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $run 'status.json');throw 'Worker failed; inspect run logs: '+$run}
  @{role=$Role;task=$taskPath;slot=$i;status='complete-unreviewed';finished_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $run 'status.json')
  Write-Output $run
}finally{$slot.ReleaseMutex();$slot.Dispose()}
