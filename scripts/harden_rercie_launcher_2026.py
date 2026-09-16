#!/usr/bin/env python3
"""Harden the RERC-e 0.5.1 Windows launcher and installer build gates."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if text.count(old) != 1:
        raise ValueError(f"Expected one {label}, found {text.count(old)}")
    return text.replace(old, new, 1)


def update_launcher() -> None:
    path = ROOT / "rercie" / "packaging" / "RERC-eLauncher.cs"
    text = path.read_text(encoding="utf-8")

    download_anchor = '        public static async Task DownloadAsync(string url, string destination, Action<long, long> progress)\n'
    free_space = '''        public static void EnsureDownloadSpace(string destination, long expectedBytes)
        {
            string partial = destination + ".partial";
            long existing = File.Exists(partial) ? new FileInfo(partial).Length : 0L;
            long remaining = Math.Max(0L, expectedBytes - existing);
            string root = Path.GetPathRoot(Path.GetFullPath(destination));
            DriveInfo drive = new DriveInfo(root);
            long reserve = 200L * 1024L * 1024L;
            if (drive.AvailableFreeSpace < remaining + reserve)
                throw new InvalidOperationException("RERC-e needs about " + ((remaining + reserve) / 1048576L).ToString("N0") + " MB of free space before downloading.");
        }


''' + '        public static async Task DownloadAsync(string url, string destination, Action<long, long> progress, CancellationToken cancellationToken)\n'
    text = replace_once(text, download_anchor, free_space, "download space and cancellation signature")
    text = text.replace(
        'using (HttpResponseMessage response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead))',
        'using (HttpResponseMessage response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken))',
        1,
    )
    text = text.replace('while ((read = await input.ReadAsync(buffer, 0, buffer.Length)) > 0)', 'while ((read = await input.ReadAsync(buffer, 0, buffer.Length, cancellationToken)) > 0)', 1)
    text = text.replace('await output.WriteAsync(buffer, 0, read);', 'await output.WriteAsync(buffer, 0, read, cancellationToken);', 1)
    text = text.replace('                catch (Exception error)\n                {\n                    lastError = error;\n                }\n                if (attempt < 4) await Task.Delay(attempt * 1500);', '                catch (OperationCanceledException)\n                {\n                    throw new InvalidOperationException("The download was canceled. The saved partial download can resume later.");\n                }\n                catch (Exception error)\n                {\n                    lastError = error;\n                }\n                if (attempt < 4) await Task.Delay(attempt * 1500, cancellationToken);', 1)

    old_probe = '''                        response.EnsureSuccessStatusCode();
                        byte[] body = await response.Content.ReadAsByteArrayAsync();
                        if (body.Length != 1024) throw new InvalidOperationException("The Gemma endpoint returned an unexpected probe size.");
                        return new { status = "PASS", http_status = (int)response.StatusCode, bytes = body.Length, model = Config.ModelName, source = Config.ModelPageUrl };
'''
    new_probe = '''                        response.EnsureSuccessStatusCode();
                        byte[] body = new byte[1024];
                        int totalRead = 0;
                        using (Stream input = await response.Content.ReadAsStreamAsync())
                        {
                            while (totalRead < body.Length)
                            {
                                int read = await input.ReadAsync(body, totalRead, body.Length - totalRead);
                                if (read <= 0) break;
                                totalRead += read;
                            }
                        }
                        if (totalRead != 1024) throw new InvalidOperationException("The Gemma endpoint returned an unexpected probe size.");
                        return new { status = "PASS", http_status = (int)response.StatusCode, bytes = totalRead, model = Config.ModelName, source = Config.ModelPageUrl };
'''
    text = replace_once(text, old_probe, new_probe, "bounded model probe")

    text = replace_once(text, '        private bool busy;\n', '        private bool busy;\n        private CancellationTokenSource activeOperationCancellation;\n', "launcher cancellation field")
    text = replace_once(text, '            StartPosition = FormStartPosition.CenterScreen;\n', '            StartPosition = FormStartPosition.CenterScreen;\n            AutoScaleMode = AutoScaleMode.Dpi;\n            AutoScroll = true;\n', "DPI scaling")
    text = text.replace('            startButton.Text = "Start RERC-e";', '            startButton.Text = "&Start RERC-e";', 1)
    text = text.replace('            openButton.Text = "Open RERC-e";', '            openButton.Text = "&Open RERC-e";', 1)
    text = text.replace('            stopButton.Text = "Stop";', '            stopButton.Text = "&Stop";', 1)
    text = replace_once(text, '            Controls.Add(stopButton);\n\n            Shown +=', '            Controls.Add(stopButton);\n            AcceptButton = startButton;\n            CancelButton = stopButton;\n\n            Shown +=', "keyboard defaults")

    old_refresh = '''            startButton.Text = modelExists ? "Start RERC-e" : "Download and start";
            startButton.Enabled = !busy && !appReady;
            openButton.Enabled = !busy && appReady;
            stopButton.Enabled = !busy && appReady;
'''
    new_refresh = '''            startButton.Text = modelExists ? "&Start RERC-e" : "&Download and start";
            startButton.Enabled = !busy && !appReady;
            openButton.Enabled = !busy && appReady;
            stopButton.Text = busy ? "&Cancel" : "&Stop";
            stopButton.Enabled = busy || appReady;
'''
    text = replace_once(text, old_refresh, new_refresh, "button state")
    text = replace_once(text, '        private async void StartClicked(object sender, EventArgs args)\n        {\n            busy = true;\n            statusLabel.ForeColor = Color.FromArgb(70, 80, 75);', '        private async void StartClicked(object sender, EventArgs args)\n        {\n            busy = true;\n            activeOperationCancellation = new CancellationTokenSource();\n            statusLabel.ForeColor = Color.FromArgb(70, 80, 75);', "start cancellation source")
    text = text.replace('if (!Runtime.VcRuntimeReady()) await InstallWindowsRuntimeAsync();', 'if (!Runtime.VcRuntimeReady()) await InstallWindowsRuntimeAsync(activeOperationCancellation.Token);')
    text = text.replace('                    statusLabel.Text = "Downloading the local model...";\n                    await Runtime.DownloadAsync(Config.ModelUrl, Runtime.ModelPath, UpdateDownloadProgress);', '                    Runtime.EnsureDownloadSpace(Runtime.ModelPath, Config.ModelBytes);\n                    statusLabel.Text = "Downloading the local model...";\n                    await Runtime.DownloadAsync(Config.ModelUrl, Runtime.ModelPath, UpdateDownloadProgress, activeOperationCancellation.Token);')
    text = text.replace('                busy = false;\n                RefreshButtons();\n            }\n        }\n\n        private void UpdateDownloadProgress', '                busy = false;\n                if (activeOperationCancellation != null) { activeOperationCancellation.Dispose(); activeOperationCancellation = null; }\n                RefreshButtons();\n            }\n        }\n\n        private void UpdateDownloadProgress', 1)
    text = text.replace('        private async Task InstallWindowsRuntimeAsync()\n', '        private async Task InstallWindowsRuntimeAsync(CancellationToken cancellationToken)\n')
    text = text.replace('            await Runtime.DownloadAsync(Config.VcRuntimeUrl, installer, null);', '            await Runtime.DownloadAsync(Config.VcRuntimeUrl, installer, null, cancellationToken);')

    stop_anchor = '''        private async void StopClicked(object sender, EventArgs args)
        {
            busy = true;
'''
    stop_replacement = '''        private async void StopClicked(object sender, EventArgs args)
        {
            if (busy && activeOperationCancellation != null)
            {
                activeOperationCancellation.Cancel();
                statusLabel.Text = "Canceling the current operation...";
                return;
            }
            busy = true;
'''
    text = replace_once(text, stop_anchor, stop_replacement, "cancel button behavior")
    path.write_text(text, encoding="utf-8", newline="\n")


def update_installer() -> None:
    path = ROOT / "rercie" / "packaging" / "RERC-e.iss"
    text = path.read_text(encoding="utf-8")
    old = """  if (CurStep = ssInstall) and FileExists(ExpandConstant('{app}\\RERC-e.exe')) then
    Exec(ExpandConstant('{app}\\RERC-e.exe'), '--stop', ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
"""
    new = """  if (CurStep = ssInstall) and FileExists(ExpandConstant('{app}\\RERC-e.exe')) then
  begin
    if (not Exec(ExpandConstant('{app}\\RERC-e.exe'), '--stop', ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode)) or (ResultCode <> 0) then
      RaiseException('RERC-e could not stop the previous version. Close RERC-e and run setup again.');
  end;
"""
    text = replace_once(text, old, new, "upgrade stop gate")
    path.write_text(text, encoding="utf-8", newline="\n")


def update_build() -> None:
    path = ROOT / "rercie" / "build_installer.ps1"
    text = path.read_text(encoding="utf-8")
    old_sign = '''function Get-SignToolPath {
    $candidates = @(
        "C:\\Program Files (x86)\\Windows Kits\\10\\bin\\10.0.26100.0\\x64\\signtool.exe",
        "C:\\Program Files (x86)\\Windows Kits\\10\\bin\\10.0.26100.0\\x86\\signtool.exe"
    )
    return $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}
'''
    new_sign = '''function Get-SignToolPath {
    $root = "C:\\Program Files (x86)\\Windows Kits\\10\\bin"
    $candidates = @()
    if (Test-Path -LiteralPath $root -PathType Container) {
        $versions = Get-ChildItem -LiteralPath $root -Directory | Sort-Object Name -Descending
        foreach ($version in $versions) {
            $candidates += Join-Path $version.FullName "x64\\signtool.exe"
            $candidates += Join-Path $version.FullName "x86\\signtool.exe"
        }
    }
    return $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}
'''
    text = replace_once(text, old_sign, new_sign, "dynamic SignTool lookup")

    manifest_anchor = '$sourceInstallerManifestPath = Join-Path $Here "packaging\\installer_manifest.json"\n'
    license_gate = '''$licensePath = Join-Path $Here "RERC-e-LICENSE.txt"
$licenseManifestPath = Join-Path $Here "packaging\\RERC-e-LICENSE-MANIFEST.json"
$licenseManifest = Get-Content -LiteralPath $licenseManifestPath -Raw | ConvertFrom-Json
if ($licenseManifest.version -ne $Version) { throw "The Timberwing license manifest is not for RERC-e $Version." }
if ($licenseManifest.license_sha256 -ne (Get-Sha256 $licensePath)) { throw "The Timberwing license manifest hash does not match RERC-e-LICENSE.txt." }

''' + manifest_anchor
    text = replace_once(text, manifest_anchor, license_gate, "license hash gate")
    text = text.replace('if ($downloadProbe.status -ne "PASS" -or $downloadProbe.http_status -ne 206 -or $downloadProbe.bytes -ne 1024', 'if ($downloadProbe.status -ne "PASS" -or $downloadProbe.http_status -notin @(200, 206) -or $downloadProbe.bytes -ne 1024')
    text = text.replace('    status = "PASS"\n    evidence_stage = "release_asset"', '    status = if ($signature.Status -eq "Valid") { "PASS" } else { "PASS_WITH_UNSIGNED_WARNING" }\n    evidence_stage = "release_asset"')
    text = text.replace('    status = "PASS"\n    version = $Version\n    installer = $InstallerPath', '    status = $releaseQa.status\n    version = $Version\n    installer = $InstallerPath')
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    update_launcher()
    update_installer()
    update_build()
    print("Applied RERC-e launcher and installer hardening.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
