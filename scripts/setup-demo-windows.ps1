Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")

function Test-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Install-WithWinget {
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if (-not (Test-Command winget)) {
        throw "winget is required. Install App Installer from Microsoft Store, then rerun this script."
    }

    Write-Host "[setup] installing $Name"
    winget install --id $Id --exact --accept-package-agreements --accept-source-agreements
}

function Install-Uv {
    if (Test-Command uv) {
        return
    }

    Write-Host "[setup] installing uv"
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

function Install-Quarto {
    if (Test-Command quarto) {
        return
    }
    Install-WithWinget -Id "Posit.Quarto" -Name "Quarto CLI"
}

function Install-Typst {
    if (Test-Command typst) {
        return
    }
    Install-WithWinget -Id "Typst.Typst" -Name "Typst CLI"
}

function New-DemoEnv {
    $EnvPath = Join-Path $RootDir "demos\.env"
    $ExamplePath = Join-Path $RootDir "demos\.env.example"
    if (-not (Test-Path $EnvPath)) {
        Copy-Item $ExamplePath $EnvPath
        Write-Host "[setup] created demos\.env from demos\.env.example"
        Write-Host "[setup] edit demos\.env and set API_KEY before running LLM demos"
    }
}

function Show-Versions {
    Write-Host "[setup] versions"
    uv --version
    uv run python --version
    quarto --version
    typst --version
}

Install-Uv
Install-Quarto
Install-Typst

Set-Location $RootDir
uv sync
New-DemoEnv
Show-Versions

Write-Host "[setup] done"
Write-Host "[setup] next: edit demos\.env, then run demos\03-documeta-completion and demos\04-build-writing"
