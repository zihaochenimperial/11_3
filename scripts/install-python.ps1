# install-python.ps1 -- ASCII only, PS 5.1 compatible. Run ONLY via host-pump job type 'pyinstall'.
# Downloads the official python.org Windows installer, verifies its Authenticode signature (Python Software Foundation),
# installs per-user into D:\Gaussian\.tools\python312 (no PATH change, no py launcher, no file associations, no shortcuts).
param([Parameter(Mandatory = $true)][string]$Version)
$ErrorActionPreference = 'Stop'
if ($Version -notmatch '^3\.12\.[0-9]{1,2}$') { throw 'version not allowed' }
$root = Split-Path -Parent $PSScriptRoot
$target = Join-Path $root '.tools\python312'
$instDir = Join-Path $root '.cache\installers'
New-Item -ItemType Directory -Force -Path $instDir | Out-Null
$exe = Join-Path $instDir ('python-' + $Version + '-amd64.exe')
$url = 'https://www.python.org/ftp/python/' + $Version + '/python-' + $Version + '-amd64.exe'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if (-not (Test-Path -LiteralPath $exe)) { Invoke-WebRequest -Uri $url -OutFile $exe -UseBasicParsing }
$sig = Get-AuthenticodeSignature -FilePath $exe
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash
$size = (Get-Item -LiteralPath $exe).Length
$signer = ''
if ($sig.SignerCertificate) { $signer = $sig.SignerCertificate.Subject }
Write-Output ('downloaded url=' + $url + ' bytes=' + $size + ' sha256=' + $hash + ' signature=' + $sig.Status + ' signer=' + $signer)
if (($sig.Status -ne 'Valid') -or ($signer -notmatch 'Python Software Foundation')) { throw 'signature check failed; not installing' }
$ia = @('/quiet', ('TargetDir=' + $target), 'InstallAllUsers=0', 'PrependPath=0', 'Include_launcher=0', 'InstallLauncherAllUsers=0', 'AssociateFiles=0', 'Shortcuts=0', 'Include_test=0', 'Include_doc=0', 'Include_pip=1', 'Include_tcltk=0')
$p = Start-Process -FilePath $exe -ArgumentList $ia -Wait -PassThru
Write-Output ('installer exit=' + $p.ExitCode)
$py = Join-Path $target 'python.exe'
if (-not (Test-Path -LiteralPath $py)) { throw 'python.exe missing after install' }
& $py --version
& $py -m pip --version
& $py -c "import venv, ssl, sys; print(sys.version)"
Write-Output ('python=' + $py)
