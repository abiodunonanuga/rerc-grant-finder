# RERC-e verified-publisher release plan

## What Windows is checking

Windows shows a verified publisher only when the executable or installer has a valid Authenticode signature whose certificate chains to a trusted root and whose subject was issued after identity validation. A self-signed certificate cannot provide that result. The publisher text comes from the signing certificate, so the legal identity must be settled before enrollment.

Microsoft currently recommends [Azure Artifact Signing](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options) for Windows applications distributed outside the Microsoft Store. It was formerly named Trusted Signing. A traditional publicly trusted organization-validation code-signing certificate is also viable, but its private key must be held in compliant hardware or a managed signing service under the current [CA/Browser Forum code-signing requirements](https://cabforum.org/working-groups/code-signing/requirements/).

## Identity decision required

Choose the exact legal publisher that can pass public-record and domain checks:

- `EPR, P.C.` if that is the legal entity that owns and releases RERC-e; or
- `Timberwing Systems` only if it is a registered organization or validated trade name that the signing provider will place in the certificate subject.

The current marketing text, `Timberwing Systems, an EPR, P.C. initiative`, is not itself proof of a legal identity. After validation, update `AppPublisher`, `VersionInfoCompany`, the package manifest, and release copy to match the certificate's verified name. Do not publish a signed build with a conflicting publisher label.

## Recommended Artifact Signing route

1. Use an Azure subscription owned by the selected legal publisher and register the `Microsoft.CodeSigning` resource provider.
2. Create an Artifact Signing account in a supported region and start an **Organization / Public** identity validation. Prepare the exact legal name, business identifier, business address, a monitored email on the organization's domain, and an authorized representative who can complete government-ID verification. Microsoft says validation can take from one to twenty business days and can take longer when records do not align.
3. Create a **Public Trust** certificate profile. Artifact Signing supplies short-lived public certificates; timestamping is therefore mandatory.
4. Grant the release identity the `Artifact Signing Certificate Profile Signer` role with least privilege.
5. Install the official Artifact Signing Client Tools or its individual prerequisites: Windows SDK SignTool `10.0.2261.755` or later, the .NET 8 runtime, the Microsoft Visual C++ Redistributable, and the matching-architecture Artifact Signing client dlib. Keep the dlib, account/profile metadata, and Azure credentials out of the repository.
6. Build from a reviewed clean commit and sign the native launcher, packaged service, and final installer. The build script supports this route:

   ```powershell
   .\build_installer.ps1 `
     -AcceptRuntimeDownload `
     -ArtifactSigningDlib "C:\secure-tools\Azure.CodeSigning.Dlib.dll" `
     -ArtifactSigningMetadata "C:\secure-config\rerc-e-artifact-signing.json" `
     -PublisherLegalName "EPR, P.C." `
     -RequireCodeSignature
   ```

   The metadata file follows Microsoft's SignTool integration format and must contain `Endpoint`, `CodeSigningAccountName`, and `CertificateProfileName`. The script signs with SHA-256 and the Artifact Signing timestamp service, verifies each signature, and rejects a certificate whose simple name differs from `PublisherLegalName`.

7. Verify every release file independently:

   ```powershell
   signtool verify /pa /all /v .\RERC-e.exe
   signtool verify /pa /all /v .\RERC-eService.exe
   signtool verify /pa /all /v .\RERC-e-Setup.exe
   Get-AuthenticodeSignature .\RERC-e-Setup.exe | Format-List Status,StatusMessage,SignerCertificate,TimeStamperCertificate
   ```

8. Test the timestamped installer on a clean, fully updated Windows 10 and Windows 11 virtual machine downloaded through a browser. Confirm the signature properties and UAC publisher name before installing, then test install, first launch, upgrade, uninstall, file association, and the embedded RERC-e window.

Microsoft's [Artifact Signing quickstart](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart), [SignTool integration guide](https://learn.microsoft.com/en-us/azure/artifact-signing/how-to-signing-integrations), [SignTool documentation](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool), and [Authenticode timestamp guidance](https://learn.microsoft.com/en-us/windows/win32/seccrypto/time-stamping-authenticode-signatures) are the controlling setup references.

## SmartScreen expectation

A valid signature supplies the verified publisher identity, but it does not guarantee that Microsoft Defender SmartScreen will immediately stop showing an “unrecognized app” warning. Microsoft states that reputation is built from the certificate and the downloaded file's reputation; EV certificates no longer receive automatic initial reputation. Maintain one stable publisher identity, timestamp every release, avoid unnecessary certificate changes, and submit false positives to Microsoft when needed. The [Microsoft Store](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation) is the distribution route Microsoft identifies for reliably avoiding SmartScreen download warnings.

## Current hold

This computer currently has no eligible public code-signing certificate with a private key, no SignTool installation, and no Inno Setup compiler. No signed installer was produced during source QA. Enrollment, identity validation, any subscription or certificate purchase, and the clean-machine release test remain release-owner actions.
