#ifndef SourceRoot
  #error SourceRoot must be defined by the build script.
#endif
#ifndef OutputDir
  #error OutputDir must be defined by the build script.
#endif
#ifndef AppVersion
  #define AppVersion "0.5.1"
#endif

#define AppName "RERC-e"
#define AppExe "RERC-e.exe"
#define AppUrl "https://henkelpress.github.io/rerc-grant-finder/"

[Setup]
AppId={{E07265FC-1C63-4B51-99BB-EFA80D9497B8}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=EPR, P.C. - Timberwing Systems
AppPublisherURL={#AppUrl}
AppSupportURL=https://github.com/henkelpress/rerc-grant-finder/issues
AppUpdatesURL=https://github.com/henkelpress/rerc-grant-finder/releases/latest
DefaultDirName={localappdata}\Programs\RERC-e
DefaultGroupName=RERC-e
DisableProgramGroupPage=yes
DisableWelcomePage=no
DisableReadyPage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=RERC-e-Setup
SetupIconFile=..\..\site-src\assets\rerc-e.ico
WizardImageFile=rerc-e-eagle-wizard.bmp
InfoBeforeFile=INSTALLER_NOTICE.txt
LicenseFile={#SourceRoot}\RERC-e-LICENSE.txt
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
ChangesAssociations=yes
RestartApplications=no
SetupLogging=yes
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName=RERC-e
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany=EPR, P.C. - Timberwing Systems
VersionInfoDescription=RERC-e local grant-writing guide
VersionInfoProductName=RERC-e
AppMutex=Local\RERC-e-Desktop

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\RERC-e"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Comment: "Use a funding option and project notes to make a first draft"
Name: "{autodesktop}\RERC-e"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon; Comment: "Use a funding option and project notes to make a first draft"
Name: "{autoprograms}\RERC-e website"; Filename: "{#AppUrl}"

[Registry]
Root: HKA; Subkey: "Software\Classes\.rercie"; ValueType: string; ValueName: ""; ValueData: "RERC-e.Plan"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.rerc-e"; ValueType: string; ValueName: ""; ValueData: "RERC-e.Plan"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\RERC-e.Plan"; ValueType: string; ValueName: ""; ValueData: "RERC-e Community Explorer Plan"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\RERC-e.Plan\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"
Root: HKA; Subkey: "Software\Classes\RERC-e.Plan\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""

[Run]
Filename: "{app}\{#AppExe}"; Description: "Meet RERC-e"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#AppExe}"; Parameters: "--stop"; WorkingDir: "{app}"; Flags: runhidden waituntilterminated; RunOnceId: "StopRERC-e"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\models"
Type: filesandordirs; Name: "{app}\runtime\logs"
Type: filesandordirs; Name: "{app}\runtime\pids"
Type: filesandordirs; Name: "{app}\runtime\handoff"
Type: files; Name: "{app}\*.partial"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if (CurStep = ssInstall) and FileExists(ExpandConstant('{app}\RERC-e.exe')) then
  begin
    if (not Exec(ExpandConstant('{app}\RERC-e.exe'), '--stop', ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode)) or (ResultCode <> 0) then
      RaiseException('RERC-e could not stop the previous version. Close RERC-e and run setup again.');
  end;
end;
