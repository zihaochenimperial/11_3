param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $OpenCodeArgs
)

$ErrorActionPreference = 'Stop'
$credentialPath = Join-Path $env:USERPROFILE '.codex\local-credentials\opencode-go-key.dpapi'
if (-not (Test-Path -LiteralPath $credentialPath)) {
    throw 'OpenCode Go key is missing. Run .\connect-opencode-go.cmd in your own PowerShell window first.'
}

$protectedHex = (Get-Content -LiteralPath $credentialPath -Raw).Trim()
if ($protectedHex -notmatch '\A(?:[0-9a-fA-F]{2})+\z') { throw 'Invalid OpenCode Go credential format.' }
$protectedBytes = New-Object byte[] ($protectedHex.Length / 2)
for ($i = 0; $i -lt $protectedBytes.Length; $i++) {
    $protectedBytes[$i] = [Convert]::ToByte($protectedHex.Substring($i * 2, 2), 16)
}
$plainBytes = [System.Security.Cryptography.ProtectedData]::Unprotect(
    $protectedBytes, $null, [System.Security.Cryptography.DataProtectionScope]::CurrentUser
)
try {
    $env:OPENCODE_API_KEY = [Text.Encoding]::Unicode.GetString($plainBytes)
} finally {
    [Array]::Clear($plainBytes, 0, $plainBytes.Length)
}

$researchRoot = Split-Path -Parent $PSScriptRoot
try {
    Push-Location -LiteralPath $researchRoot
    try {
        & 'C:\Users\USER\AppData\Local\Programs\node-v24.21.0\opencode.cmd' --standalone @OpenCodeArgs
        $openCodeExitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
} finally {
    Remove-Item Env:OPENCODE_API_KEY -ErrorAction SilentlyContinue
}
if ($openCodeExitCode -ne 0) { throw "OpenCode exited with code $openCodeExitCode." }


