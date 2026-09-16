param(
    [string]$OutputDirectory = "",
    [int]$Port = 18893
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($env:OS -ne "Windows_NT") { throw "RERC-e native acceptance requires Windows." }
$RepoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$Csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$WebView2Version = "1.0.4191.47"
$WebView2PackageSha256 = "f492bbf547d0da329553b6727435b677579b1e9f91cc9e4a1ad029366d5f23d0"
$WebView2Package = Join-Path $RepoRoot "rercie\build-cache\nuget\microsoft.web.webview2\$WebView2Version"
$WebView2Lib = Join-Path $WebView2Package "lib\net462"
$WebView2Core = Join-Path $WebView2Lib "Microsoft.Web.WebView2.Core.dll"
$WebView2WinForms = Join-Path $WebView2Lib "Microsoft.Web.WebView2.WinForms.dll"
$WebView2Loader = Join-Path $WebView2Package "runtimes\win-x64\native\WebView2Loader.dll"
$Python = Get-Command python -ErrorAction SilentlyContinue

if (-not (Test-Path -LiteralPath $Csc -PathType Leaf)) { throw "The .NET Framework C# compiler is unavailable: $Csc" }
if (-not $Python) { throw "Python is unavailable." }
$MissingWebView2 = @(@($WebView2Core, $WebView2WinForms, $WebView2Loader) | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })
if ($MissingWebView2.Count -gt 0) {
    $DotNet = Get-Command dotnet -ErrorAction SilentlyContinue
    if (-not $DotNet) { throw "The .NET SDK is required to restore the acceptance-only WebView2 test dependency." }
    $OldDotNetHome = $env:DOTNET_CLI_HOME
    try {
        $env:DOTNET_CLI_HOME = Join-Path $RepoRoot "rercie\build-cache\dotnet-home"
        & $DotNet.Source restore (Join-Path $RepoRoot "rercie\packaging\WebView2Sdk.csproj") --packages (Join-Path $RepoRoot "rercie\build-cache\nuget") --configfile (Join-Path $RepoRoot "rercie\packaging\NuGet.Config") --verbosity quiet
        if ($LASTEXITCODE -ne 0) { throw "The acceptance-only WebView2 test dependency restore failed." }
    } finally {
        $env:DOTNET_CLI_HOME = $OldDotNetHome
    }
}
$WebView2Nupkg = Join-Path $WebView2Package "microsoft.web.webview2.$WebView2Version.nupkg"
if (-not (Test-Path -LiteralPath $WebView2Nupkg -PathType Leaf) -or (Get-FileHash -LiteralPath $WebView2Nupkg -Algorithm SHA256).Hash.ToLowerInvariant() -ne $WebView2PackageSha256) {
    throw "The acceptance-only WebView2 test package failed its pinned SHA-256 check."
}
foreach ($required in @($WebView2Core, $WebView2WinForms, $WebView2Loader)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "The acceptance-only WebView2 test dependency is missing: $required" }
}

if (-not $OutputDirectory) { $OutputDirectory = Join-Path $RepoRoot "rercie\build-cache\native-acceptance" }
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (-not $OutputDirectory.StartsWith($RepoRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Native acceptance output must remain inside the repository worktree."
}
$EvidenceDirectory = Join-Path $OutputDirectory "evidence"
if (Test-Path -LiteralPath $EvidenceDirectory) { Remove-Item -LiteralPath $EvidenceDirectory -Recurse -Force }
[IO.Directory]::CreateDirectory($EvidenceDirectory) | Out-Null
[IO.Directory]::CreateDirectory((Join-Path $OutputDirectory "assets")) | Out-Null

$CompilerArguments = @(
    "/nologo", "/target:winexe", "/optimize+", "/platform:x64",
    "/define:RERC_E_ACCEPTANCE_QA;RERC_E_ACCEPTANCE_NO_ACTIVATION", "/main:RERCeDesktop.AcceptanceProgram",
    "/out:$(Join-Path $OutputDirectory 'RERC-e.exe')",
    "/win32icon:$(Join-Path $RepoRoot 'assets\rerc-e.ico')",
    "/win32manifest:$(Join-Path $RepoRoot 'rercie\packaging\RERC-e.exe.manifest')",
    "/reference:System.dll", "/reference:System.Core.dll", "/reference:System.Drawing.dll",
    "/reference:System.Windows.Forms.dll", "/reference:System.Net.Http.dll",
    "/reference:System.Web.Extensions.dll", "/reference:System.Security.dll",
    "/reference:$WebView2Core", "/reference:$WebView2WinForms",
    (Join-Path $RepoRoot "rercie\packaging\RERC-eLauncher.cs"),
    (Join-Path $RepoRoot "rercie\packaging\NativeAcceptanceHarness.cs")
)
& $Csc @CompilerArguments
if ($LASTEXITCODE -ne 0) { throw "The RERC-e native acceptance harness did not compile." }

Copy-Item -LiteralPath $WebView2Core -Destination $OutputDirectory -Force
Copy-Item -LiteralPath $WebView2WinForms -Destination $OutputDirectory -Force
Copy-Item -LiteralPath $WebView2Loader -Destination $OutputDirectory -Force
Copy-Item -LiteralPath (Join-Path $RepoRoot "rercie\packaging\RERC-e.exe.config") -Destination (Join-Path $OutputDirectory "RERC-e.exe.config") -Force
Copy-Item -LiteralPath (Join-Path $RepoRoot "assets\rerc-e-eagle.jpg") -Destination (Join-Path $OutputDirectory "assets\rerc-e-eagle.jpg") -Force

$Token = "rerc-e-native-acceptance-" + [Guid]::NewGuid().ToString("N")
$OldToken = $env:RERCIE_SESSION_TOKEN
$OldHost = $env:RERCIE_EXPECTED_HOST
$OldRoot = $env:RERCIE_APP_ROOT
$Service = $null
try {
    $env:RERCIE_SESSION_TOKEN = $Token
    $env:RERCIE_EXPECTED_HOST = "127.0.0.1:$Port"
    $env:RERCIE_APP_ROOT = Join-Path $RepoRoot "rercie"
    $ServiceLog = Join-Path $EvidenceDirectory "service-requests.log"
    $Service = Start-Process -FilePath $Python.Source -ArgumentList @("rercie.py", "--serve", "--host", "127.0.0.1", "--port", "$Port") -WorkingDirectory (Join-Path $RepoRoot "rercie") -PassThru -WindowStyle Hidden -RedirectStandardError $ServiceLog
    $Ready = $false
    foreach ($Attempt in 1..60) {
        try {
            $Health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -Headers @{ "X-RERC-e-Token" = $Token; Host = "127.0.0.1:$Port" } -TimeoutSec 1
            if ($Health.status -eq "ok") { $Ready = $true; break }
        } catch { }
        Start-Sleep -Milliseconds 250
    }
    if (-not $Ready) { throw "The local RERC-e service did not become ready for native acceptance." }

    $LaunchCodeResponse = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$Port/api/app-window-code" -Headers @{ "X-RERC-e-Token" = $Token; Host = "127.0.0.1:$Port" } -ContentType "application/json" -Body "{}" -TimeoutSec 3
    if (-not $LaunchCodeResponse.code -or $LaunchCodeResponse.expiresInSeconds -ne 60) { throw "The one-time app-window code endpoint returned an invalid response." }
    $BrowserSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $LaunchAddress = "http://127.0.0.1:$Port/app-window?code=$([Uri]::EscapeDataString([string]$LaunchCodeResponse.code))"
    $LaunchResponse = Invoke-WebRequest -UseBasicParsing -Uri $LaunchAddress -Headers @{ Host = "127.0.0.1:$Port" } -WebSession $BrowserSession -MaximumRedirection 5 -TimeoutSec 3
    $LaunchFinalUri = if ($LaunchResponse.BaseResponse.PSObject.Properties["ResponseUri"]) { $LaunchResponse.BaseResponse.ResponseUri } else { $LaunchResponse.BaseResponse.RequestMessage.RequestUri }
    if ($LaunchResponse.StatusCode -ne 200 -or $LaunchFinalUri.AbsolutePath -ne "/native") { throw "The one-time app-window code did not open the native app route." }
    $SessionCookie = $BrowserSession.Cookies.GetCookies([Uri]"http://127.0.0.1:$Port/")["RERCeSession"]
    if (-not $SessionCookie -or -not $SessionCookie.HttpOnly) { throw "The app-window session cookie is missing or is not HttpOnly." }
    $CookieHealth = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -Headers @{ Host = "127.0.0.1:$Port" } -WebSession $BrowserSession -TimeoutSec 3
    if ($CookieHealth.status -ne "ok") { throw "The app-window session cookie did not authorize the local service." }
    $ReplayStatus = 0
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $LaunchAddress -Headers @{ Host = "127.0.0.1:$Port" } -MaximumRedirection 0 -TimeoutSec 3 | Out-Null
    } catch {
        if ($_.Exception.Response) { $ReplayStatus = [int]$_.Exception.Response.StatusCode }
    }
    if ($ReplayStatus -ne 403) { throw "The one-time app-window code could be reused." }
    $AppWindowSecurity = [ordered]@{
        launch_code_ttl_seconds = [int]$LaunchCodeResponse.expiresInSeconds
        full_session_token_in_url = $false
        redirected_to_native = $true
        httponly_cookie = [bool]$SessionCookie.HttpOnly
        cookie_authorized_health = $true
        replay_status = $ReplayStatus
    }

    $App = Start-Process -FilePath (Join-Path $OutputDirectory "RERC-e.exe") -ArgumentList @("http://127.0.0.1:$Port/native#token=$Token", ('"' + $EvidenceDirectory + '"')) -PassThru -Wait
    if ($App.ExitCode -ne 0) { throw "The RERC-e native acceptance harness exited with code $($App.ExitCode)." }
    $ReportPath = Join-Path $EvidenceDirectory "native-acceptance.json"
    if (-not (Test-Path -LiteralPath $ReportPath -PathType Leaf)) { throw "The native acceptance report was not created." }
    $Report = Get-Content -LiteralPath $ReportPath -Raw | ConvertFrom-Json
    if ($Report.status -ne "PASS") { throw "RERC-e native acceptance failed. Review $ReportPath" }

    $BoundSources = [ordered]@{
        "rercie/packaging/RERC-eLauncher.cs" = (Get-FileHash -LiteralPath (Join-Path $RepoRoot "rercie\packaging\RERC-eLauncher.cs") -Algorithm SHA256).Hash.ToLowerInvariant()
        "rercie/packaging/RERC-e.exe.config" = (Get-FileHash -LiteralPath (Join-Path $RepoRoot "rercie\packaging\RERC-e.exe.config") -Algorithm SHA256).Hash.ToLowerInvariant()
        "rercie/packaging/RERC-e.exe.manifest" = (Get-FileHash -LiteralPath (Join-Path $RepoRoot "rercie\packaging\RERC-e.exe.manifest") -Algorithm SHA256).Hash.ToLowerInvariant()
        "rercie/packaging/NativeAcceptanceHarness.cs" = (Get-FileHash -LiteralPath (Join-Path $RepoRoot "rercie\packaging\NativeAcceptanceHarness.cs") -Algorithm SHA256).Hash.ToLowerInvariant()
        "rercie/rercie_core.py" = (Get-FileHash -LiteralPath (Join-Path $RepoRoot "rercie\rercie_core.py") -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $NativeEvidencePath = Join-Path $RepoRoot "rercie\packaging\NATIVE_WINDOWS_QA.json"
    $NativeEvidence = [ordered]@{
        status = "PASS"
        evidence_stage = "source"
        app = $Report.app
        app_version = $Report.version
        tested_utc = [DateTime]::UtcNow.ToString("o")
        os = $Report.os
        clr = $Report.clr
        process_dpi_awareness = $Report.process_dpi_awareness
        per_monitor_v2 = $Report.per_monitor_dpi_aware
        actual_monitor = [ordered]@{
            dpi = $Report.current.device_dpi
            scale_percent = [int][Math]::Round($Report.current.device_dpi / 96d * 100)
            layout_pass = $Report.native_layout_pass
            clipped_text = @($Report.current.clipped_text)
            outside_parent = @($Report.current.outside_parent)
            unnamed_interactive = @($Report.current.unnamed_interactive)
            download_button = $Report.current.download_button
        }
        simulated_geometry = @($Report.geometry | ForEach-Object {
            [ordered]@{
                scale = $_.scale
                evaluated_dpi = $_.evaluated_dpi
                status = if ($_.pass) { "PASS" } else { "FAIL" }
                clipped_text = @($_.clipped_text)
                outside_parent = @($_.outside_parent)
                unnamed_interactive = @($_.unnamed_interactive)
            }
        })
        app_window_host = [ordered]@{
            status = if ($Report.app_window_host.microsoft_publisher_trusted) { "PASS" } else { "FAIL" }
            mode = $Report.app_window_host.mode
            executable = $Report.app_window_host.executable
            microsoft_publisher_trusted = [bool]$Report.app_window_host.microsoft_publisher_trusted
            address_bar_visible = [bool]$Report.app_window_host.address_bar_visible
            security = $AppWindowSecurity
        }
        web_content = [ordered]@{
            status = if ($Report.web_content_pass) { "PASS" } else { "FAIL" }
            title = $Report.web_content.dom.title
            step_count = $Report.web_content.dom.stepCount
            token_stored = $Report.web_content.dom.tokenStored
            page_overflow = $Report.web_content.dom.pageOverflow
            live_content_visible = [bool]$Report.web_content_visible
            acceptance_runtime = $Report.web_content.webview_runtime
        }
        source_sha256 = $BoundSources
        evidence_files = @("native-acceptance.json", "acceptance-progress.txt", "service-requests.log", "setup-current-dpi.png", "setup-100-simulated.png", "setup-150-simulated.png", "setup-200-simulated.png", "native-shell-with-webview.png", "embedded-rerc-e.png")
        limitations = @(
            "The actual native-window run used this computer's 150% display scale.",
            "The 100% and 200% results are off-monitor geometry and font simulations; final release acceptance still requires clean Windows 10 and Windows 11 machines.",
            "The browser-content capture uses an off-screen WebView2 acceptance control; the shipped launcher uses the signed Microsoft Edge app-window host recorded above.",
            "The source-built executable is unsigned and is not a public release candidate."
        )
    }
    [IO.File]::WriteAllText($NativeEvidencePath, ($NativeEvidence | ConvertTo-Json -Depth 9), [Text.UTF8Encoding]::new($false))

    [ordered]@{
        status = $Report.status
        app = $Report.app
        version = $Report.version
        report = $ReportPath
        source_evidence = $NativeEvidencePath
        actual_dpi = $Report.current.device_dpi
        per_monitor_v2 = $Report.per_monitor_dpi_aware
        native_layout = $Report.native_layout_pass
        simulated_geometry = $Report.simulated_geometry_pass
        app_window_host = $Report.app_window_host.microsoft_publisher_trusted
        app_window_security = ($ReplayStatus -eq 403 -and [bool]$SessionCookie.HttpOnly)
        web_content = $Report.web_content_pass
        acceptance_runtime = $Report.web_content.webview_runtime
    } | ConvertTo-Json -Depth 4
} finally {
    if ($Service -and -not $Service.HasExited) {
        Stop-Process -Id $Service.Id -Force -ErrorAction SilentlyContinue
        $Service.WaitForExit(10000) | Out-Null
    }
    $env:RERCIE_SESSION_TOKEN = $OldToken
    $env:RERCIE_EXPECTED_HOST = $OldHost
    $env:RERCIE_APP_ROOT = $OldRoot
}
