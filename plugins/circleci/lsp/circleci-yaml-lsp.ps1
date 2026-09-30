# Find the CircleCI YAML language server to run on Windows, downloading it
# first if need be, and print the binary's path. circleci-yaml-lsp.cmd runs
# this and then starts the binary.
#
# This does what circleci-yaml-lsp does on Unix: the latest version comes from
# CircleCI's tool releases API, checked at most once a day, and the binary from
# the server's GitHub release, checked against the release's checksums.txt. If
# the check or the download fails, the version already installed is used.
#
# Only the path goes to stdout; everything else goes to stderr. Written for
# Windows PowerShell 5.1, which every supported Windows has.
#
# Environment:
#   CIRCLECI_YAML_LSP_VERSION  run this version rather than the latest
#   CIRCLECI_YAML_LSP_DIR      where to install (default: the plugin's data
#                              directory, else %LOCALAPPDATA%\circleci)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

$repo = 'CircleCI-Public/circleci-yaml-language-server'
$api = 'https://circleci.com/api/v3/tool/releases?filter%5Btool%5D=circleci-yaml-language-server'

function Say([string]$message) { [Console]::Error.WriteLine("circleci-yaml-lsp: $message") }
function Die([string]$message) { Say $message; exit 1 }

$arch = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
switch ($arch) {
  'AMD64' { $arch = 'amd64' }
  'ARM64' { $arch = 'arm64' }
  default { Die "there is no release for $arch" }
}
$asset = "windows-$arch-lsp.exe"
$bin = 'circleci-yaml-lsp.exe'

$root = if ($env:CIRCLECI_YAML_LSP_DIR) { $env:CIRCLECI_YAML_LSP_DIR }
        elseif ($env:CLAUDE_PLUGIN_DATA) { $env:CLAUDE_PLUGIN_DATA }
        else { Join-Path $env:LOCALAPPDATA 'circleci' }
$dir = Join-Path $root 'yaml-language-server'
New-Item -ItemType Directory -Force -Path $dir | Out-Null

function Valid([string]$version) { $version -match '^[0-9A-Za-z._-]+$' }
function Exe([string]$version) { Join-Path (Join-Path $dir $version) $bin }

# Latest returns the version the releases API says is the latest, or ''.
function Latest {
  try {
    $response = Invoke-RestMethod -UseBasicParsing -TimeoutSec 15 -Uri $api
    return [string]$response.data[0].attributes.version
  } catch {
    return ''
  }
}

# Install downloads and verifies a version, and reports whether it worked.
function Install([string]$version) {
  $tmp = Join-Path $dir ".download.$PID"
  try {
    Remove-Item -Recurse -Force -Path $tmp -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $tmp | Out-Null
    $url = "https://github.com/$repo/releases/download/$version"
    Say "downloading $version from $url"
    Invoke-WebRequest -UseBasicParsing -Uri "$url/checksums.txt" -OutFile (Join-Path $tmp 'checksums.txt')
    Invoke-WebRequest -UseBasicParsing -Uri "$url/$asset" -OutFile (Join-Path $tmp $asset)
    $want = Get-Content (Join-Path $tmp 'checksums.txt') | ForEach-Object {
      $fields = -split $_
      if ($fields.Count -ge 2 -and ($fields[1] -eq $asset -or $fields[1] -eq "*$asset")) { $fields[0] }
    } | Select-Object -First 1
    if (-not $want) { Say "checksums.txt for $version doesn't list $asset"; return $false }
    $got = (Get-FileHash -Algorithm SHA256 -Path (Join-Path $tmp $asset)).Hash
    if ($got -ne $want) { Say "$asset for $version doesn't match checksums.txt"; return $false }
    New-Item -ItemType Directory -Force -Path (Join-Path $dir $version) | Out-Null
    Move-Item -Force -Path (Join-Path $tmp $asset) -Destination (Exe $version)
    return $true
  } catch {
    Say "$_"
    return $false
  } finally {
    Remove-Item -Recurse -Force -Path $tmp -ErrorAction SilentlyContinue
  }
}

# Use records a version as the one to start and removes the others. Windows
# won't delete a binary another session is running, so those stay until later.
function Use([string]$version) {
  Set-Content -Path (Join-Path $dir 'current') -Value $version
  Get-ChildItem -Directory -Path $dir | Where-Object { $_.Name -ne $version -and -not $_.Name.StartsWith('.') } |
    ForEach-Object { Remove-Item -Recurse -Force -Path $_.FullName -ErrorAction SilentlyContinue }
}

$currentFile = Join-Path $dir 'current'
$current = if (Test-Path $currentFile) { "$(Get-Content -TotalCount 1 -Path $currentFile)".Trim() } else { '' }
if (-not (Valid $current) -or -not (Test-Path (Exe $current))) { $current = '' }

$checked = Join-Path $dir 'checked'
if ($env:CIRCLECI_YAML_LSP_VERSION) {
  $version = $env:CIRCLECI_YAML_LSP_VERSION
  if (-not (Valid $version)) { Die "CIRCLECI_YAML_LSP_VERSION isn't a version: $version" }
} elseif ($current -and (Test-Path $checked) -and (Get-Item $checked).LastWriteTime -gt (Get-Date).AddDays(-1)) {
  $version = $current
} else {
  $version = Latest
  if (-not (Valid $version)) {
    if (-not $current) { Die "couldn't find the latest release at $api" }
    Say "couldn't check for a newer release; starting $current"
    $version = $current
  }
  Set-Content -Path $checked -Value ''
}

if (-not (Test-Path (Exe $version)) -and -not (Install $version)) {
  if (-not $current) { Die "couldn't install $version" }
  Say "couldn't install $version; starting $current"
  $version = $current
}
if (-not $env:CIRCLECI_YAML_LSP_VERSION -and $version -ne $current) {
  Use $version
}

Write-Output (Exe $version)
