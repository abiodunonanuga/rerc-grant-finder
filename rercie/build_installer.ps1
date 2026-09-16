param(
    [switch]$AcceptRuntimeDownload,
    [string]$OutputDirectory = "",
    [string]$InnoCompiler = "",
    [string]$CodeSigningThumbprint = "",
    [string]$ArtifactSigningDlib = "",
    [string]$ArtifactSigningMetadata = "",
    [string]$PublisherLegalName = "",
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [string]$ArtifactTimestampUrl = "http://timestamp.acs.microsoft.com",
    [switch]$RequireCodeSignature,
    [switch]$AllowUnsignedQaBuild
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $Here
$AssetRoot = Join-Path $RepoRoot "assets"
if (-not (Test-Path -LiteralPath $AssetRoot -PathType Container)) { $AssetRoot = Join-Path $RepoRoot "site-src\assets" }
Set-Location -LiteralPath $Here
$Version = "0.5.2"
$RuntimeName = "llama-b9987-bin-win-cpu-x64.zip"
$RuntimeUrl = "https://github.com/ggerganov/llama.cpp/releases/download/b9987/$RuntimeName"
$RuntimeSha256 = "6847d537b3cd5099051989d08c7eca4296e7a0f1755dbf0540c82e37768320f3"
$LicenseUrl = "https://raw.githubusercontent.com/ggml-org/llama.cpp/b9987/LICENSE"
$BuildRoot = Join-Path $Here "build\installer-$Version"
$CacheDir = Join-Path $Here "build-cache"
$ArchivePath = Join-Path $CacheDir $RuntimeName
$Extracted = Join-Path $BuildRoot "llama-extracted"
$PyInstallerRoot = Join-Path $BuildRoot "pyinstaller"
$PackageRoot = Join-Path $BuildRoot "RERC-e"
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $Here "dist" }
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
$InstallerPath = Join-Path $OutputDirectory "RERC-e-Setup.exe"
$Csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$FrameworkReferences = "C:\Program Files (x86)\Reference Assemblies\Microsoft\Framework\.NETFramework\v4.7.2"
$WebView2Version = "1.0.4191.47"
$WebView2PackageSha256 = "f492bbf547d0da329553b6727435b677579b1e9f91cc9e4a1ad029366d5f23d0"
$WebView2Package = Join-Path $CacheDir "nuget\microsoft.web.webview2\$WebView2Version"
$WebView2Lib = Join-Path $WebView2Package "lib\net462"
$WebView2Core = Join-Path $WebView2Lib "Microsoft.Web.WebView2.Core.dll"
$WebView2Wpf = Join-Path $WebView2Lib "Microsoft.Web.WebView2.Wpf.dll"
$WebView2Loader = Join-Path $WebView2Package "runtimes\win-x64\native\WebView2Loader.dll"
if (-not $InnoCompiler) { $InnoCompiler = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe" }
$ArtifactSigningRequested = [bool]($ArtifactSigningDlib -or $ArtifactSigningMetadata)
$PublisherSignatureRequested = [bool]($CodeSigningThumbprint -or $ArtifactSigningRequested)
if ($RequireCodeSignature -and $AllowUnsignedQaBuild) { throw "Choose a signed release build or an unsigned QA-only build, not both." }
if ($CodeSigningThumbprint -and $ArtifactSigningRequested) { throw "Choose either a local certificate thumbprint or Azure Artifact Signing, not both." }
if ([bool]$ArtifactSigningDlib -ne [bool]$ArtifactSigningMetadata) { throw "Azure Artifact Signing requires both -ArtifactSigningDlib and -ArtifactSigningMetadata." }
if ($ArtifactSigningRequested -and -not $PublisherLegalName) { throw "Azure Artifact Signing requires -PublisherLegalName to match the validated public certificate identity." }
if (-not $PublisherSignatureRequested -and -not $AllowUnsignedQaBuild) {
    throw "Public RERC-e installers require an authorized, trusted publisher signature. Supply -CodeSigningThumbprint or the Azure Artifact Signing parameters, or use -AllowUnsignedQaBuild only for local QA."
}

function Get-Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-SignToolPath {
    $root = "C:\Program Files (x86)\Windows Kits\10\bin"
    $candidates = @()
    if (Test-Path -LiteralPath $root -PathType Container) {
        $versions = Get-ChildItem -LiteralPath $root -Directory | Sort-Object Name -Descending
        foreach ($version in $versions) {
            $candidates += Join-Path $version.FullName "x64\signtool.exe"
            $candidates += Join-Path $version.FullName "x86\signtool.exe"
        }
    }
    return $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}

function Sign-RercBinary([string]$Path) {
    if (-not $PublisherSignatureRequested) {
        if ($RequireCodeSignature) { throw "An authorized EPR, P.C. or Timberwing Systems code-signing certificate thumbprint is required." }
        return "NotSigned"
    }
    $signTool = Get-SignToolPath
    if (-not $signTool) { throw "SignTool was not found." }
    if ($ArtifactSigningRequested) {
        & $signTool sign /v /fd SHA256 /tr $ArtifactTimestampUrl /td SHA256 /dlib $ArtifactSigningDlib /dmdf $ArtifactSigningMetadata $Path
    } else {
        $certificate = Get-ChildItem -LiteralPath "Cert:\CurrentUser\My\$CodeSigningThumbprint" -ErrorAction SilentlyContinue
        if (-not $certificate -or -not $certificate.HasPrivateKey) { throw "The requested code-signing certificate is unavailable or has no private key." }
        if ($certificate.Subject -notmatch "Timberwing Systems|EPR, P[.]C[.]") { throw "The code-signing certificate identity does not name the authorized RERC-e publisher." }
        if ($certificate.NotBefore -gt (Get-Date) -or $certificate.NotAfter -lt (Get-Date)) { throw "The code-signing certificate is outside its valid date range." }
        $eku = $certificate.Extensions | Where-Object { $_.Oid.Value -eq "2.5.29.37" } | Select-Object -First 1
        if (-not $eku -or -not ($eku.EnhancedKeyUsages | Where-Object { $_.Value -eq "1.3.6.1.5.5.7.3.3" })) {
            throw "The certificate is not authorized for code signing."
        }
        & $signTool sign /sha1 $CodeSigningThumbprint /fd SHA256 /tr $TimestampUrl /td SHA256 $Path
    }
    if ($LASTEXITCODE -ne 0) { throw "Authenticode signing failed for $Path." }
    & $signTool verify /pa /v $Path
    if ($LASTEXITCODE -ne 0) { throw "Authenticode verification failed for $Path." }
    $status = Get-AuthenticodeSignature -LiteralPath $Path
    if ($status.Status -ne "Valid") { throw "The Authenticode signature is not valid for ${Path}: $($status.Status)." }
    if (-not $status.SignerCertificate) { throw "The signed file does not expose a publisher certificate: $Path" }
    $signedPublisher = $status.SignerCertificate.GetNameInfo([Security.Cryptography.X509Certificates.X509NameType]::SimpleName, $false)
    if ($PublisherLegalName -and $signedPublisher -ne $PublisherLegalName) {
        throw "The signed publisher '$signedPublisher' does not match -PublisherLegalName '$PublisherLegalName'."
    }
    return [string]$status.Status
}

if ($ArtifactSigningRequested) {
    if (-not (Test-Path -LiteralPath $ArtifactSigningDlib -PathType Leaf)) { throw "The Azure Artifact Signing dlib was not found: $ArtifactSigningDlib" }
    if (-not (Test-Path -LiteralPath $ArtifactSigningMetadata -PathType Leaf)) { throw "The Azure Artifact Signing metadata file was not found: $ArtifactSigningMetadata" }
    $artifactMetadata = Get-Content -LiteralPath $ArtifactSigningMetadata -Raw | ConvertFrom-Json
    foreach ($name in @("Endpoint", "CodeSigningAccountName", "CertificateProfileName")) {
        if (-not $artifactMetadata.PSObject.Properties[$name] -or -not $artifactMetadata.$name) { throw "The Azure Artifact Signing metadata is missing $name." }
    }
    if (-not (Get-SignToolPath)) { throw "SignTool is required for an Azure Artifact Signing release build." }
} elseif ($CodeSigningThumbprint) {
    $publisherCertificate = Get-ChildItem -LiteralPath "Cert:\CurrentUser\My\$CodeSigningThumbprint" -ErrorAction SilentlyContinue
    if (-not $publisherCertificate -or -not $publisherCertificate.HasPrivateKey) {
        throw "The authorized RERC-e publisher certificate is unavailable or has no private key."
    }
    if (-not (Get-SignToolPath)) { throw "SignTool is required for a signed RERC-e release build." }
}

$sourceQaPath = Join-Path $Here "packaging\QA_EVIDENCE.json"
$sourceQa = Get-Content -LiteralPath $sourceQaPath -Raw | ConvertFrom-Json
if ($sourceQa.status -ne "SOURCE_PASS") { throw "QA_EVIDENCE.json status is $($sourceQa.status). Complete and review RERC-e $Version source QA before building." }
if ($sourceQa.app_version -ne $Version) { throw "QA_EVIDENCE.json is for version $($sourceQa.app_version), not release $Version. Run and review current source QA before building." }
if ($sourceQa.checks.local_generation.source_normalized_sha256 -ne (Get-Sha256 (Join-Path $Here "rercie_core.py"))) {
    throw "QA_EVIDENCE.json local-generation evidence does not bind to the current RERC-e source."
}
if ($sourceQa.PSObject.Properties["historical"] -and $sourceQa.historical) { throw "Historical QA evidence cannot authorize a current release build." }
if ($sourceQa.evidence_stage -ne "source") { throw "QA_EVIDENCE.json must be current source-stage evidence." }
$requiredQaChecks = @("source_smoke", "native_launcher", "display_scaling", "live_catalog", "community_lookup", "local_generation", "docx_export", "api_privacy_regression", "service_identity_checks", "licensing_and_runtime")
foreach ($checkName in $requiredQaChecks) {
    $check = $sourceQa.checks.PSObject.Properties[$checkName]
    if (-not $check -or $check.Value.status -ne "PASS") { throw "Required QA check is not PASS: $checkName" }
}

$localQaPath = Join-Path $Here "packaging\LOCAL_GEMMA_QA.json"
$localQa = Get-Content -LiteralPath $localQaPath -Raw | ConvertFrom-Json
if ($localQa.status -ne "PASS" -or $localQa.app_version -ne $Version) { throw "LOCAL_GEMMA_QA.json must contain a current PASS for RERC-e $Version." }
if ($localQa.PSObject.Properties["historical"] -and $localQa.historical) { throw "Historical local Gemma evidence cannot authorize a current release build." }
if ($localQa.model -ne "gemma-3-4b-it-Q4_K_M.gguf") { throw "LOCAL_GEMMA_QA.json does not identify the approved Gemma model." }
if ($localQa.source_sha256 -ne (Get-Sha256 (Join-Path $Here "rercie_core.py"))) { throw "LOCAL_GEMMA_QA.json does not match the current RERC-e source." }

$licensePath = Join-Path $Here "RERC-e-LICENSE.txt"
$licenseManifestPath = Join-Path $Here "packaging\RERC-e-LICENSE-MANIFEST.json"
$licenseManifest = Get-Content -LiteralPath $licenseManifestPath -Raw | ConvertFrom-Json
if ($licenseManifest.version -ne $Version) { throw "The Timberwing license manifest is not for RERC-e $Version." }
if ($licenseManifest.license_sha256 -ne (Get-Sha256 $licensePath)) { throw "The Timberwing license manifest hash does not match RERC-e-LICENSE.txt." }

$sourceInstallerManifestPath = Join-Path $Here "packaging\installer_manifest.json"
$sourceInstallerManifest = Get-Content -LiteralPath $sourceInstallerManifestPath -Raw | ConvertFrom-Json
if ($sourceInstallerManifest.package.version -ne $Version) { throw "installer_manifest.json must identify RERC-e $Version." }

$bannedModelPattern = ("qw" + "en|qw" + "en2[.]5|LICENSE-" + "QW" + "EN")
$bannedModelReferences = @(& git -C $RepoRoot grep -I -n -i -E $bannedModelPattern -- README.md index.html rercie)
if ($LASTEXITCODE -eq 0 -or $bannedModelReferences.Count -gt 0) { throw "The release source contains a prohibited model-family reference: $($bannedModelReferences -join '; ')" }
if ($LASTEXITCODE -gt 1) { throw "The prohibited-model source scan failed." }
python .\rercie.py --smoke
if ($LASTEXITCODE -ne 0) { throw "The RERC-e source smoke test failed." }
python ..\scripts\qa_release.py
if ($LASTEXITCODE -ne 0) { throw "The executable RERC-e release QA failed." }

$dirty = @(& git -C $RepoRoot status --porcelain)
if ($LASTEXITCODE -ne 0) { throw "Git status failed." }
if ($dirty.Count -gt 0) {
    throw "The release build requires a clean Git worktree. Commit the reviewed source, then build again."
}

if (Test-Path -LiteralPath $BuildRoot) { Remove-Item -LiteralPath $BuildRoot -Recurse -Force }
[IO.Directory]::CreateDirectory($BuildRoot) | Out-Null
[IO.Directory]::CreateDirectory($CacheDir) | Out-Null
[IO.Directory]::CreateDirectory($OutputDirectory) | Out-Null
[IO.Directory]::CreateDirectory($PackageRoot) | Out-Null

python -m PyInstaller --noconfirm --clean --distpath (Join-Path $PyInstallerRoot "dist") --workpath (Join-Path $PyInstallerRoot "work") .\RERC-eService.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf) -or (Get-Sha256 $ArchivePath) -ne $RuntimeSha256) {
    if (-not $AcceptRuntimeDownload) {
        throw "The pinned llama.cpp runtime is not cached. Build again with -AcceptRuntimeDownload."
    }
    curl.exe -L --fail --retry 3 --output $ArchivePath $RuntimeUrl
    if ($LASTEXITCODE -ne 0) { throw "The llama.cpp runtime download failed." }
}
if ((Get-Sha256 $ArchivePath) -ne $RuntimeSha256) { throw "The llama.cpp runtime archive failed its SHA-256 check." }

[IO.Directory]::CreateDirectory($Extracted) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::ExtractToDirectory($ArchivePath, $Extracted)
[IO.Directory]::CreateDirectory((Join-Path $PackageRoot "runtime\llama")) | Out-Null
$runtimeFiles = @(
    "llama-server.exe",
    "llama-server-impl.dll",
    "llama-common.dll",
    "llama.dll",
    "mtmd.dll",
    "ggml.dll",
    "ggml-base.dll",
    "libomp140.x86_64.dll"
)
foreach ($cpuDll in Get-ChildItem -LiteralPath $Extracted -Filter "ggml-cpu-*.dll" -File) { $runtimeFiles += $cpuDll.Name }
foreach ($name in $runtimeFiles | Select-Object -Unique) {
    $source = Join-Path $Extracted $name
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Required llama.cpp runtime file is missing: $name" }
    Copy-Item -LiteralPath $source -Destination (Join-Path $PackageRoot "runtime\llama\$name")
}
$ServiceSource = Join-Path $PyInstallerRoot "dist\RERC-eService"
$ServiceDestination = Join-Path $PackageRoot "service"
if (-not (Test-Path -LiteralPath (Join-Path $ServiceSource "RERC-eService.exe") -PathType Leaf)) { throw "The one-folder RERC-e service build was not created." }
Copy-Item -LiteralPath $ServiceSource -Destination $ServiceDestination -Recurse

if (-not (Test-Path -LiteralPath $Csc -PathType Leaf)) { throw "The Windows C# compiler was not found at $Csc." }
foreach ($assembly in @("WindowsFormsIntegration.dll", "PresentationCore.dll", "PresentationFramework.dll", "WindowsBase.dll", "System.Xaml.dll")) {
    if (-not (Test-Path -LiteralPath (Join-Path $FrameworkReferences $assembly) -PathType Leaf)) { throw "The .NET Framework 4.7.2 reference assembly is missing: $assembly" }
}
$MissingWebView2 = @(@($WebView2Core, $WebView2Wpf, $WebView2Loader) | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })
if ($MissingWebView2.Count -gt 0) {
    $DotNet = Get-Command dotnet -ErrorAction SilentlyContinue
    if (-not $DotNet) { throw "The .NET SDK is required to restore the pinned WebView2 dependency." }
    $OldDotNetHome = $env:DOTNET_CLI_HOME
    try {
        $env:DOTNET_CLI_HOME = Join-Path $CacheDir "dotnet-home"
        [IO.Directory]::CreateDirectory($env:DOTNET_CLI_HOME) | Out-Null
        & $DotNet.Source restore (Join-Path $Here "packaging\WebView2Sdk.csproj") --packages (Join-Path $CacheDir "nuget") --configfile (Join-Path $Here "packaging\NuGet.Config") --verbosity quiet
        if ($LASTEXITCODE -ne 0) { throw "The pinned WebView2 dependency restore failed." }
    } finally {
        $env:DOTNET_CLI_HOME = $OldDotNetHome
    }
}
$WebView2Nupkg = Join-Path $WebView2Package "microsoft.web.webview2.$WebView2Version.nupkg"
if (-not (Test-Path -LiteralPath $WebView2Nupkg -PathType Leaf) -or (Get-Sha256 $WebView2Nupkg) -ne $WebView2PackageSha256) {
    throw "The pinned WebView2 package failed its SHA-256 check."
}
foreach ($required in @($WebView2Core, $WebView2Wpf, $WebView2Loader)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "The pinned WebView2 dependency is missing: $required" }
}
$launcherConfig = Join-Path $Here "packaging\RERC-e.exe.config"
$launcherManifest = Join-Path $Here "packaging\RERC-e.exe.manifest"
$cscArgs = @(
    "/nologo", "/target:winexe", "/optimize+", "/platform:x64",
    "/out:$(Join-Path $PackageRoot 'RERC-e.exe')",
    "/win32icon:$(Join-Path $AssetRoot 'rerc-e.ico')",
    "/win32manifest:$launcherManifest",
    "/reference:System.dll", "/reference:System.Core.dll", "/reference:System.Drawing.dll",
    "/reference:System.Windows.Forms.dll", "/reference:System.Net.Http.dll",
    "/reference:System.Web.Extensions.dll", "/reference:System.Security.dll",
    "/reference:$(Join-Path $FrameworkReferences 'WindowsFormsIntegration.dll')",
    "/reference:$(Join-Path $FrameworkReferences 'PresentationCore.dll')",
    "/reference:$(Join-Path $FrameworkReferences 'PresentationFramework.dll')",
    "/reference:$(Join-Path $FrameworkReferences 'WindowsBase.dll')",
    "/reference:$(Join-Path $FrameworkReferences 'System.Xaml.dll')",
    "/reference:$WebView2Core", "/reference:$WebView2Wpf",
    (Join-Path $Here "packaging\RERC-eLauncher.cs")
)
& $Csc @cscArgs
if ($LASTEXITCODE -ne 0) { throw "The native RERC-e launcher build failed." }
Copy-Item -LiteralPath $launcherConfig -Destination (Join-Path $PackageRoot "RERC-e.exe.config")
Copy-Item -LiteralPath $WebView2Core -Destination $PackageRoot
Copy-Item -LiteralPath $WebView2Wpf -Destination $PackageRoot
Copy-Item -LiteralPath $WebView2Loader -Destination $PackageRoot
$launcherSignatureStatus = Sign-RercBinary (Join-Path $PackageRoot "RERC-e.exe")
$serviceSignatureStatus = Sign-RercBinary (Join-Path $PackageRoot "service\RERC-eService.exe")

$PythonRoot = (& python -c "import sys; print(sys.base_prefix)").Trim()
$PythonLicense = Join-Path $PythonRoot "LICENSE.txt"
if (-not (Test-Path -LiteralPath $PythonLicense -PathType Leaf)) { throw "The Python license file was not found at $PythonLicense." }
Copy-Item -LiteralPath $PythonLicense -Destination (Join-Path $PackageRoot "LICENSE-PYTHON.txt")
[IO.Directory]::CreateDirectory((Join-Path $PackageRoot "licenses")) | Out-Null
Copy-Item -LiteralPath (Join-Path $Here "licenses\GEMMA_TERMS.txt") -Destination (Join-Path $PackageRoot "licenses\GEMMA_TERMS.txt")
Copy-Item -LiteralPath (Join-Path $WebView2Package "LICENSE.txt") -Destination (Join-Path $PackageRoot "licenses\WEBVIEW2-LICENSE.txt")
Copy-Item -LiteralPath (Join-Path $WebView2Package "NOTICE.txt") -Destination (Join-Path $PackageRoot "licenses\WEBVIEW2-NOTICE.txt")
curl.exe -L --fail --retry 3 --output (Join-Path $PackageRoot "runtime\llama\LICENSE-llama.cpp") $LicenseUrl
if ($LASTEXITCODE -ne 0) { throw "The llama.cpp license download failed." }

Copy-Item -LiteralPath $sourceQaPath -Destination $PackageRoot
Copy-Item -LiteralPath (Join-Path $Here "RERC-e-LICENSE.txt") -Destination (Join-Path $PackageRoot "RERC-e-LICENSE.txt")
Copy-Item -LiteralPath (Join-Path $Here "packaging\RERC-e-LICENSE-MANIFEST.json") -Destination (Join-Path $PackageRoot "RERC-e-LICENSE-MANIFEST.json")
foreach ($name in @("README.md", "MODEL_NOTICE.md", "THIRD_PARTY_NOTICES.md")) {
    Copy-Item -LiteralPath (Join-Path $Here $name) -Destination $PackageRoot
}
Copy-Item -LiteralPath (Join-Path $Here "examples") -Destination $PackageRoot -Recurse
Copy-Item -LiteralPath (Join-Path $Here "local_knowledge") -Destination $PackageRoot -Recurse
[IO.Directory]::CreateDirectory((Join-Path $PackageRoot "assets")) | Out-Null
Copy-Item -LiteralPath (Join-Path $AssetRoot "rerc-e-eagle.jpg") -Destination (Join-Path $PackageRoot "assets\rerc-e-eagle.jpg")
Copy-Item -LiteralPath (Join-Path $AssetRoot "ASSET_PROVENANCE.md") -Destination (Join-Path $PackageRoot "ASSET_PROVENANCE.md")

$integrityFiles = @(
    Get-Item -LiteralPath (Join-Path $PackageRoot "RERC-e.exe")
    Get-Item -LiteralPath (Join-Path $PackageRoot "RERC-e.exe.config")
    Get-ChildItem -LiteralPath $PackageRoot -Filter "*.dll" -File
    Get-ChildItem -LiteralPath (Join-Path $PackageRoot "service") -Recurse -File | Where-Object { $_.Extension -in @(".exe", ".dll", ".pyd") }
    Get-ChildItem -LiteralPath (Join-Path $PackageRoot "runtime\llama") -File | Where-Object { $_.Extension -in @(".exe", ".dll") }
)
$entries = foreach ($file in $integrityFiles) {
    $relative = $file.FullName.Substring($PackageRoot.Length + 1).Replace("\", "/")
    [ordered]@{ path = $relative; bytes = $file.Length; sha256 = Get-Sha256 $file.FullName }
}
$integrity = [ordered]@{
    app = "RERC-e"
    version = $Version
    generated_utc = [DateTime]::UtcNow.ToString("o")
    files = @($entries)
}
$integrityPath = Join-Path $PackageRoot "file_integrity.json"
[IO.File]::WriteAllText($integrityPath, ($integrity | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))

$sourceCommit = (& git -C $RepoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $sourceCommit -notmatch "^[0-9a-f]{40}$") { throw "The build must run from a Git checkout with a valid source commit." }
$packageManifest = Get-Content -LiteralPath $sourceInstallerManifestPath -Raw | ConvertFrom-Json
$packageManifest.package.version = $Version
$packageManifest.package | Add-Member -NotePropertyName generated_utc -NotePropertyValue ([DateTime]::UtcNow.ToString("o")) -Force
$packageManifest.package | Add-Member -NotePropertyName source_commit -NotePropertyValue $sourceCommit -Force
$packageManifestPath = Join-Path $PackageRoot "installer_manifest.json"
[IO.File]::WriteAllText($packageManifestPath, ($packageManifest | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
$qaPath = Join-Path $PackageRoot "QA_EVIDENCE.json"
$qa = Get-Content -LiteralPath $qaPath -Raw | ConvertFrom-Json
$qa.status = "PACKAGE_BUILD"
$qa.evidence_stage = "package"
$qa.release_binding.source_commit = $sourceCommit
$qa.release_binding.integrity_manifest_sha256 = Get-Sha256 $integrityPath
$qa.release_binding | Add-Member -NotePropertyName built_utc -NotePropertyValue ([DateTime]::UtcNow.ToString("o")) -Force
$qa.release_binding | Add-Member -NotePropertyName worktree_clean -NotePropertyValue ($dirty.Count -eq 0) -Force
$qa.checks.package_integrity.status = "PASS"
$qa.checks.package_integrity.integrity_checked_binaries = @($entries).Count
$qa.release_binding.status = "PACKAGE_BOUND"
[IO.File]::WriteAllText($qaPath, ($qa | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))

$serviceQaPort = 18791
$serviceQaToken = ([Guid]::NewGuid().ToString("N") + [Guid]::NewGuid().ToString("N"))
$serviceQaExe = Join-Path $PackageRoot "service\RERC-eService.exe"
$serviceQaProcess = $null
$serviceQaReady = $false
$serviceAppWindowSecurity = $false
$oldSessionToken = $env:RERCIE_SESSION_TOKEN
$oldExpectedHost = $env:RERCIE_EXPECTED_HOST
$oldAppRoot = $env:RERCIE_APP_ROOT
try {
    $env:RERCIE_SESSION_TOKEN = $serviceQaToken
    $env:RERCIE_EXPECTED_HOST = "127.0.0.1:$serviceQaPort"
    $env:RERCIE_APP_ROOT = $PackageRoot
    $serviceQaProcess = Start-Process -FilePath $serviceQaExe -ArgumentList @("--serve", "--host", "127.0.0.1", "--port", "$serviceQaPort") -WorkingDirectory (Split-Path $serviceQaExe) -PassThru
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$serviceQaPort/health" -Headers @{ "X-RERC-e-Token" = $serviceQaToken } -TimeoutSec 2
            if ($health.status -eq "ok" -and $health.app -eq "RERC-e") { $serviceQaReady = $true; break }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    if ($serviceQaReady) {
        $launchCode = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$serviceQaPort/api/app-window-code" -Headers @{ "X-RERC-e-Token" = $serviceQaToken } -ContentType "application/json" -Body "{}" -TimeoutSec 3
        $browserSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
        $launchAddress = "http://127.0.0.1:$serviceQaPort/app-window?code=$([Uri]::EscapeDataString([string]$launchCode.code))"
        $launchResponse = Invoke-WebRequest -UseBasicParsing -Uri $launchAddress -WebSession $browserSession -MaximumRedirection 5 -TimeoutSec 3
        $launchFinalUri = if ($launchResponse.BaseResponse.PSObject.Properties["ResponseUri"]) { $launchResponse.BaseResponse.ResponseUri } else { $launchResponse.BaseResponse.RequestMessage.RequestUri }
        $cookie = $browserSession.Cookies.GetCookies([Uri]"http://127.0.0.1:$serviceQaPort/")["RERCeSession"]
        $cookieHealth = Invoke-RestMethod -Uri "http://127.0.0.1:$serviceQaPort/health" -WebSession $browserSession -TimeoutSec 3
        $replayStatus = 0
        try { Invoke-WebRequest -UseBasicParsing -Uri $launchAddress -MaximumRedirection 0 -TimeoutSec 3 | Out-Null }
        catch { if ($_.Exception.Response) { $replayStatus = [int]$_.Exception.Response.StatusCode } }
        $serviceAppWindowSecurity = $launchCode.expiresInSeconds -eq 60 -and $launchFinalUri.AbsolutePath -eq "/native" -and $cookie.HttpOnly -and $cookieHealth.status -eq "ok" -and $replayStatus -eq 403
    }
} finally {
    if ($serviceQaProcess -and -not $serviceQaProcess.HasExited) {
        Stop-Process -Id $serviceQaProcess.Id -Force -ErrorAction SilentlyContinue
        $serviceQaProcess.WaitForExit(10000)
    }
    $env:RERCIE_SESSION_TOKEN = $oldSessionToken
    $env:RERCIE_EXPECTED_HOST = $oldExpectedHost
    $env:RERCIE_APP_ROOT = $oldAppRoot
}
if (-not $serviceQaReady) { throw "The packaged authenticated RERC-e service health check failed." }
if (-not $serviceAppWindowSecurity) { throw "The packaged RERC-e one-time app-window handoff failed." }
if ($serviceQaProcess -and -not $serviceQaProcess.HasExited) { throw "The packaged RERC-e service did not stop cleanly." }
$qa.checks.service_identity_checks.status = "PASS"
$qa.checks.service_identity_checks | Add-Member -NotePropertyName packaged_authenticated_health -NotePropertyValue $true -Force
$qa.checks.service_identity_checks | Add-Member -NotePropertyName packaged_app_window_handoff -NotePropertyValue $true -Force
[IO.File]::WriteAllText($qaPath, ($qa | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))

$smokePath = Join-Path $BuildRoot "launcher-smoke.json"
$smokeProcess = Start-Process -FilePath (Join-Path $PackageRoot "RERC-e.exe") -ArgumentList @("--smoke-output", ('"' + $smokePath + '"')) -Wait -PassThru
if ($smokeProcess.ExitCode -ne 0) { throw "The native launcher smoke test failed." }
if (-not (Test-Path -LiteralPath $smokePath -PathType Leaf)) { throw "The native launcher smoke report was not created." }
$smoke = Get-Content -LiteralPath $smokePath -Raw | ConvertFrom-Json
if ($smoke.status -ne "PASS" -or $smoke.version -ne $Version -or $smoke.powershell_required -ne $false) { throw "The native launcher smoke report was not valid for RERC-e $Version." }
if ($smoke.model_name -ne "gemma-3-4b-it-Q4_K_M.gguf" -or $smoke.model_sha256 -ne "882e8d2db44dc554fb0ea5077cb7e4bc49e7342a1f0da57901c0802ea21a0863") { throw "The launcher smoke report does not identify the approved Gemma model." }
if ($smoke.app_window_mode -ne "embedded WebView2 composition" -or $smoke.composition_visual_host -ne $true -or $smoke.same_window_transition -ne $true -or $smoke.address_bar_visible -ne $false -or $smoke.full_session_token_in_url -ne $false -or $smoke.full_session_token_in_command_line -ne $false) { throw "The native launcher smoke report does not validate the embedded composition host." }

$downloadProbePath = Join-Path $BuildRoot "launcher-download-probe.json"
$downloadProbeProcess = Start-Process -FilePath (Join-Path $PackageRoot "RERC-e.exe") -ArgumentList @("--probe-download-output", ('"' + $downloadProbePath + '"')) -Wait -PassThru
if ($downloadProbeProcess.ExitCode -ne 0) { throw "The native launcher could not reach the Gemma download endpoint." }
if (-not (Test-Path -LiteralPath $downloadProbePath -PathType Leaf)) { throw "The Gemma download probe report was not created." }
$downloadProbe = Get-Content -LiteralPath $downloadProbePath -Raw | ConvertFrom-Json
if ($downloadProbe.status -ne "PASS" -or $downloadProbe.http_status -notin @(200, 206) -or $downloadProbe.bytes -ne 1024 -or $downloadProbe.model -ne "gemma-3-4b-it-Q4_K_M.gguf") { throw "The Gemma download probe report was not valid." }
$qa.checks.native_launcher | Add-Member -NotePropertyName download_probe_http_status -NotePropertyValue $downloadProbe.http_status -Force
$qa.checks.native_launcher | Add-Member -NotePropertyName download_probe_bytes -NotePropertyValue $downloadProbe.bytes -Force
$qa.checks.native_launcher.status = "PASS"
$qa.status = "PACKAGE_PASS"
[IO.File]::WriteAllText($qaPath, ($qa | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
if (-not (Test-Path -LiteralPath $InnoCompiler -PathType Leaf)) { throw "Inno Setup was not found at $InnoCompiler." }
if (Test-Path -LiteralPath $InstallerPath) { Remove-Item -LiteralPath $InstallerPath -Force }
& $InnoCompiler "/DSourceRoot=$PackageRoot" "/DOutputDir=$OutputDirectory" "/DAppVersion=$Version" (Join-Path $Here "packaging\RERC-e.iss")
if ($LASTEXITCODE -ne 0) { throw "The RERC-e installer build failed." }
if (-not (Test-Path -LiteralPath $InstallerPath -PathType Leaf)) { throw "The RERC-e installer was not created." }
$installerSignatureStatus = Sign-RercBinary $InstallerPath

$installerSha256 = Get-Sha256 $InstallerPath
$checksumPath = Join-Path $OutputDirectory "RERC-e-Setup.exe.sha256"
[IO.File]::WriteAllText($checksumPath, "$installerSha256  RERC-e-Setup.exe`n", [Text.UTF8Encoding]::new($false))

$testInstallDir = Join-Path $BuildRoot "isolated-install"
if (Test-Path -LiteralPath $testInstallDir) { Remove-Item -LiteralPath $testInstallDir -Recurse -Force }
$installArgs = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER", ('/DIR="' + $testInstallDir + '"'), '/MERGETASKS="!desktopicon"')
$installExit = $null
$upgradeExit = $null
$uninstallExit = $null
$upgradePreservedModels = $false
$installedSmoke = $null
try {
    $installProcess = Start-Process -FilePath $InstallerPath -ArgumentList $installArgs -Wait -PassThru
    $installExit = $installProcess.ExitCode
    if ($installExit -ne 0) { throw "The isolated installer test failed with exit code $installExit." }
    $installedSmokePath = Join-Path $testInstallDir "installed-smoke.json"
    $installedSmokeProcess = Start-Process -FilePath (Join-Path $testInstallDir "RERC-e.exe") -ArgumentList @("--smoke-output", ('"' + $installedSmokePath + '"')) -Wait -PassThru
    if ($installedSmokeProcess.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $installedSmokePath)) { throw "The installed launcher smoke test failed." }
    $installedSmoke = Get-Content -LiteralPath $installedSmokePath -Raw | ConvertFrom-Json
    if ($installedSmoke.status -ne "PASS" -or $installedSmoke.version -ne $Version -or $installedSmoke.powershell_required -ne $false -or $installedSmoke.model_name -ne "gemma-3-4b-it-Q4_K_M.gguf") { throw "The installed launcher smoke evidence is invalid for RERC-e $Version." }
    $modelDir = Join-Path $testInstallDir "models"
    [IO.Directory]::CreateDirectory($modelDir) | Out-Null
    $modelSentinel = Join-Path $modelDir "upgrade-preservation-test.txt"
    [IO.File]::WriteAllText($modelSentinel, "preserve", [Text.UTF8Encoding]::new($false))
    $upgradeProcess = Start-Process -FilePath $InstallerPath -ArgumentList $installArgs -Wait -PassThru
    $upgradeExit = $upgradeProcess.ExitCode
    if ($upgradeExit -ne 0) { throw "The isolated upgrade test failed with exit code $upgradeExit." }
    $upgradePreservedModels = Test-Path -LiteralPath $modelSentinel
    if (-not $upgradePreservedModels) { throw "The isolated upgrade removed the model folder." }
} finally {
    $uninstaller = Join-Path $testInstallDir "unins000.exe"
    if (Test-Path -LiteralPath $uninstaller) {
        $uninstallProcess = Start-Process -FilePath $uninstaller -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") -Wait -PassThru
        $uninstallExit = $uninstallProcess.ExitCode
    }
}
if ($uninstallExit -ne 0) { throw "The isolated uninstall test failed with exit code $uninstallExit." }

$signature = Get-AuthenticodeSignature -LiteralPath $InstallerPath
$signatureDisclosure = if ($signature.Status -eq "Valid") { "The installer has a valid authorized publisher signature." } else { "The installer is not code-signed, so Windows may show a safety notice." }
$releaseQaPath = Join-Path $OutputDirectory "RERC-e-Release-QA.json"
$releaseQa = [ordered]@{
    status = if ($signature.Status -eq "Valid") { "PASS" } else { "QA_ONLY_UNSIGNED" }
    evidence_stage = "release_asset"
    app = "RERC-e"
    version = $Version
    source_commit = $sourceCommit
    installer_file = "RERC-e-Setup.exe"
    installer_bytes = (Get-Item -LiteralPath $InstallerPath).Length
    installer_sha256 = $installerSha256
    checksum_file = "RERC-e-Setup.exe.sha256"
    package_qa_sha256 = Get-Sha256 $qaPath
    integrity_manifest_sha256 = Get-Sha256 $integrityPath
    integrity_files = @($entries).Count
    signature_status = [string]$signature.Status
    publisher_signature_requested = $PublisherSignatureRequested
    signing_method = if ($ArtifactSigningRequested) { "Azure Artifact Signing" } elseif ($CodeSigningThumbprint) { "Local certificate" } else { "Unsigned QA" }
    publisher_legal_name = $PublisherLegalName
    signature_subject = if ($signature.SignerCertificate) { $signature.SignerCertificate.Subject } else { $null }
    public_release_allowed = ($signature.Status -eq "Valid")
    launcher_signature_status = $launcherSignatureStatus
    service_signature_status = $serviceSignatureStatus
    powershell_required = $false
    approved_model = $installedSmoke.model_name
    isolated_install = [ordered]@{
        status = "PASS"
        install_exit = $installExit
        launcher_status = $installedSmoke.status
        upgrade_exit = $upgradeExit
        upgrade_preserved_models = $upgradePreservedModels
        uninstall_exit = $uninstallExit
    }
    disclosed_limits = @(
        $signatureDisclosure,
        "The isolated test ran on the build computer rather than a clean Windows virtual machine.",
        "Source-bound local Gemma inference passed against the final RERC-e source before packaging.",
        "Users must review generated drafts and verify current rules on official funding pages."
    )
}
[IO.File]::WriteAllText($releaseQaPath, ($releaseQa | ConvertTo-Json -Depth 7), [Text.UTF8Encoding]::new($false))

[pscustomobject]@{
    status = $releaseQa.status
    version = $Version
    installer = $InstallerPath
    bytes = (Get-Item -LiteralPath $InstallerPath).Length
    sha256 = $installerSha256
    checksum = $checksumPath
    release_qa = $releaseQaPath
    signature_status = [string]$signature.Status
    publisher_signature_requested = $PublisherSignatureRequested
    signing_method = if ($ArtifactSigningRequested) { "Azure Artifact Signing" } elseif ($CodeSigningThumbprint) { "Local certificate" } else { "Unsigned QA" }
    launcher_signature_status = $launcherSignatureStatus
    service_signature_status = $serviceSignatureStatus
    powershell_required = $false
    integrity_files = @($entries).Count
    source_commit = $sourceCommit
    worktree_clean = ($dirty.Count -eq 0)
    launcher_smoke = $smokePath
} | ConvertTo-Json
