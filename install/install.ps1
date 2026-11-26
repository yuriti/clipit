# SMTV installer for Windows: uv (the official way), then SMTV with its tools, then the SMTV icon.
#
#   powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
#
# Everything goes into your own user folder: no administrator rights. Read it before running it - it is short.
#
# Options through the environment (set before the line above):
#   $env:SMTV_DRY_RUN = "1"    print what would run, change nothing
#   $env:SMTV_NO_START = "1"   do not open SMTV at the end
#   $env:SMTV_TOOLS = "vodcut" which tools, comma-separated (default: vodcut)
#   $env:SMTV_LANG = "en"      the language of these messages: en or ru (default: the system's)
#
# Smart App Control (Windows 11) blocks programs that are not signed, such as smtv.exe, which uv makes, and the Python
# builds uv downloads. So this script never starts smtv.exe: it runs SMTV through Python itself (`python -m smtv`), the
# SMTV icon starts pythonw.exe, and with Smart App Control on SMTV is installed only on python.org's signed Python
# (installed from winget for this user when missing).

$ErrorActionPreference = "Stop"
$UvInstaller = "https://astral.sh/uv/install.ps1"   # uv's official installer (Astral)
# pythonnet, which draws SMTV's window on Windows, is tested up to Python 3.13; uv picks an installed one that fits.
$PythonVersion = ">=3.10,<3.14"
$SignedPython = "Python.Python.3.13"                # winget id of python.org's Python, signed by the Python Software Foundation
$Tools = if ($env:SMTV_TOOLS) { $env:SMTV_TOOLS } else { "vodcut" }
$DryRun = $env:SMTV_DRY_RUN -eq "1"
$NoStart = $env:SMTV_NO_START -eq "1"

$Lang = if ($env:SMTV_LANG) { $env:SMTV_LANG } else { (Get-UICulture).TwoLetterISOLanguageName }
$Ru = $Lang -like "ru*"

function Say([string]$En, [string]$RuText) {
    if ($Ru) { Write-Host $RuText } else { Write-Host $En }
}

function Stop-Install([string]$En, [string]$RuText) {
    if ($Ru) { Write-Host $RuText -ForegroundColor Red } else { Write-Host $En -ForegroundColor Red }
    # `irm | iex` runs inside the person's own PowerShell window: throw, never exit, so the window stays open.
    throw "SMTV install stopped"
}

function Invoke-Step([string]$Exe, [string[]]$Arguments) {
    Write-Host ("  > " + $Exe + " " + ($Arguments -join " ")) -ForegroundColor DarkGray
    if ($DryRun) { return $true }
    $ErrorActionPreference = "Continue"   # here only: Windows PowerShell turns a program's progress on stderr into errors
    & $Exe @Arguments | Out-Host          # to the screen, not into this function's result
    return ($LASTEXITCODE -eq 0)
}

function Test-SmartAppControl {
    # 1: on, 2: evaluation (it may switch itself on), 0 or missing: off
    $state = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy" -ErrorAction SilentlyContinue).VerifiedAndReputablePolicyState
    return ($state -eq 1 -or $state -eq 2)
}

if ($Tools -notmatch '^[a-z0-9-]+(,[a-z0-9-]+)*$') {
    Stop-Install "SMTV_TOOLS: only names like vodcut or vodcut,livecut" "SMTV_TOOLS: только имена вида vodcut или vodcut,livecut"
}

# --- this computer -----------------------------------------------------------------------------------------------------
$Build = [Environment]::OSVersion.Version.Build
if ($Build -lt 17763) {
    Stop-Install "SMTV needs Windows 10 version 1809 or newer. Update Windows, then run this again." `
                 "SMTV нужна Windows 10 версии 1809 или новее. Обновите Windows и запустите установку снова."
}
if (-not [Environment]::Is64BitOperatingSystem) {
    Stop-Install "SMTV needs 64-bit Windows." "SMTV нужна 64-битная Windows."
}

Say "Installing SMTV - clips and a recap from stream recordings." "Устанавливаю SMTV - клипы и пересказ из записи стрима."
if ($DryRun) { Say "(dry run: nothing is changed)" "(проверка: ничего не меняется)" }

# --- 1. uv -------------------------------------------------------------------------------------------------------------
function Find-Uv {
    $cmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($dir in @($env:UV_INSTALL_DIR, $env:XDG_BIN_HOME, (Join-Path $HOME ".local\bin"), (Join-Path $HOME ".cargo\bin"))) {
        if ($dir -and (Test-Path (Join-Path $dir "uv.exe"))) { return (Join-Path $dir "uv.exe") }
    }
    return $null
}

$Uv = Find-Uv
if ($Uv) {
    Say "1/3 uv is already here: $Uv" "1/3 uv уже есть: $Uv"
} else {
    Say "1/3 Installing uv, the Python package manager (from astral.sh, its official installer)..." `
        "1/3 Ставлю uv - менеджер пакетов Python (с astral.sh, официальный установщик)..."
    Write-Host "  > irm $UvInstaller | iex" -ForegroundColor DarkGray
    if (-not $DryRun) {
        try {
            powershell -NoProfile -ExecutionPolicy ByPass -Command "irm $UvInstaller | iex"
        } catch {
            Stop-Install "Could not install uv: $($_.Exception.Message). Check the internet connection and run this again." `
                         "Не удалось поставить uv: $($_.Exception.Message). Проверьте интернет и запустите установку снова."
        }
    }
    $Uv = Find-Uv
    if (-not $Uv) {
        if ($DryRun) { $Uv = Join-Path $HOME ".local\bin\uv.exe" } else {
            Stop-Install "uv was installed but cannot be found. Open a new PowerShell window and run this installer again." `
                         "uv установлен, но не найден. Откройте новое окно PowerShell и запустите установку снова."
        }
    }
}

# --- 2. SMTV -----------------------------------------------------------------------------------------------------------
$Spec = "smtv[$Tools]"
$InstallArgs = @("tool", "install", "--upgrade", "--python", $PythonVersion)
if (Test-SmartAppControl) {
    Say "Smart App Control is on: SMTV goes on python.org's signed Python." `
        "Включён Smart App Control: SMTV ставится на подписанный Python с python.org."
    $InstallArgs += "--no-managed-python"
    $found = $false
    if (-not ($DryRun -and -not (Test-Path $Uv))) {
        $ErrorActionPreference = "Continue"
        & $Uv python find --no-managed-python $PythonVersion 2>$null | Out-Null
        $found = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = "Stop"
    }
    if (-not $found) {
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
            Stop-Install "Install Python 3.13 from python.org (or from the Microsoft Store: App Installer gives winget), then run this again." `
                         "Поставьте Python 3.13 с python.org (или «Установщик приложений» из Microsoft Store, он даёт winget) и запустите установку снова."
        }
        Say "Installing Python 3.13 from winget for this user. You accept the terms of Microsoft and of the package's author (the Python Software Foundation)." `
            "Ставлю Python 3.13 из winget для этого пользователя. Вы принимаете условия Microsoft и автора пакета (Python Software Foundation)."
        if (-not (Invoke-Step "winget" @("install", "--id", $SignedPython, "--exact", "--scope", "user", "--silent", "--accept-package-agreements", "--accept-source-agreements"))) {
            Stop-Install "Could not install Python. Install Python 3.13 from python.org, then run this again." `
                         "Не удалось поставить Python. Поставьте Python 3.13 с python.org и запустите установку снова."
        }
    }
}
$InstallArgs += $Spec
Say "2/3 Installing $Spec (a few minutes the first time: about 0.7 GB to download)..." `
    "2/3 Ставлю $Spec (в первый раз несколько минут: скачивается около 0,7 ГБ)..."
if (-not (Invoke-Step $Uv $InstallArgs)) {
    Stop-Install "Could not install SMTV. Check the internet connection and run this again; if it fails again, copy the text above into a problem report: https://github.com/yuriti/clipit/issues/new?template=bug.yml" `
                 "Не удалось установить SMTV. Проверьте интернет и запустите установку снова; если не выйдет - скопируйте текст выше в сообщение о проблеме: https://github.com/yuriti/clipit/issues/new?template=bug.yml"
}
# Where uv puts commands goes on PATH for new windows; harmless when it already is.
$null = Invoke-Step $Uv @("tool", "update-shell")

# --- 3. the SMTV icon, through uv's Python (signed), never smtv.exe ------------------------------------------------------
$ToolDir = if ($DryRun -and -not (Test-Path $Uv)) { Join-Path $env:APPDATA "uv\tools" } else { (& $Uv tool dir).Trim() }
$Python = Join-Path $ToolDir "smtv\Scripts\python.exe"
$Pythonw = Join-Path $ToolDir "smtv\Scripts\pythonw.exe"
Say "3/3 Making the SMTV icon (desktop and Start menu)..." "3/3 Создаю значок SMTV (рабочий стол и «Пуск»)..."
$Icon = Invoke-Step $Python @("-m", "smtv", "shortcut")
if (-not $Icon) {
    Say "The icon could not be made. Start SMTV with: `"$Python`" -m smtv app" `
        "Значок создать не удалось. Запускайте SMTV так: `"$Python`" -m smtv app"
}

Write-Host ""
Say "SMTV is installed. Start it from the Start menu or the desktop: SMTV." "SMTV установлен. Запускайте из «Пуска» или с рабочего стола: SMTV."
Say "In SMTV: choose an AI, paste a link to a stream recording, wait for the clips. Settings > Computer check finds and fixes what is missing (ffmpeg, for example)." `
    "В SMTV: выберите нейросеть, вставьте ссылку на запись стрима, дождитесь клипов. «Настройки → Проверка компьютера» найдёт и поставит недостающее (например, ffmpeg)."
Say "If Windows blocks smtv in a terminal (Smart App Control), run it through Python instead: `"$Python`" -m smtv - the icon is not affected." `
    "Если Windows блокирует smtv в терминале (Smart App Control), запускайте через Python: `"$Python`" -m smtv - значка это не касается."

if ($Icon -and -not $NoStart) {
    Write-Host "  > $Pythonw -m smtv app" -ForegroundColor DarkGray
    if (-not $DryRun) { Start-Process -FilePath $Pythonw -ArgumentList @("-m", "smtv", "app") }
}
