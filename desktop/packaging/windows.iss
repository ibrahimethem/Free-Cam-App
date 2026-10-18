; Compile through package_windows.py, not directly. Stable AppId enables upgrades.
#ifndef ProductVersion
  #error ProductVersion is required
#endif
#ifndef RepoRoot
  #error RepoRoot is required
#endif
#ifndef PackageName
  #error PackageName is required
#endif

[Setup]
AppId={{D85B6327-1A15-470D-80CA-88365D40807B}
AppName=NoSub Studio
AppVersion={#ProductVersion}
#ifdef PublicBeta
AppVerName=NoSub Studio {#ProductVersion} — Unsigned public beta 1
#endif
AppPublisher=İbrahim Ethem Karalı
AppPublisherURL=https://ibrahimethem.github.io/Free-Cam-App/
AppSupportURL=https://ibrahimethem.github.io/Free-Cam-App/support/
DefaultDirName={autopf}\NoSub Studio
DefaultGroupName=NoSub Studio
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\FreeCam.exe
SetupIconFile={#RepoRoot}\build\branding\NoSubStudio.ico
OutputDir={#RepoRoot}\dist\installers
OutputBaseFilename={#PackageName}
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.22000
PrivilegesRequired=admin
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
AppMutex=NoSubStudio.Desktop.InstallGuard
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
VersionInfoVersion={#ProductVersion}
VersionInfoDescription=NoSub Studio installer
#ifdef PublicBeta
InfoBeforeFile={#RepoRoot}\desktop\packaging\WINDOWS-BETA.txt
#else
InfoBeforeFile={#RepoRoot}\desktop\packaging\WINDOWS-INSTALL.txt
#endif
LicenseFile={#RepoRoot}\build\windows-installer-license.txt

[Languages]
Name: english; MessagesFile: compiler:Default.isl

[Types]
Name: full; Description: NoSub Studio with native webcam (recommended)
Name: receiver; Description: Receiver only (OBS or MJPEG output)
Name: custom; Description: Custom installation; Flags: iscustom

[Components]
Name: app; Description: NoSub Studio; Types: full receiver custom; Flags: fixed
Name: camera; Description: NoSub Camera for Windows video apps; Types: full

[Tasks]
Name: desktopicon; Description: Create a desktop shortcut; Flags: unchecked

[Files]
Source: {#RepoRoot}\LICENSE; DestDir: {app}; Flags: ignoreversion; Components: app
Source: {#RepoRoot}\THIRD_PARTY_NOTICES.md; DestDir: {app}; Flags: ignoreversion; Components: app
Source: {#RepoRoot}\dist\FreeCam\*; DestDir: {app}; Flags: ignoreversion recursesubdirs createallsubdirs; Components: app
; Frame Server must load the camera from an administrator-protected directory.
Source: {#RepoRoot}\build\native-camera-windows\Release\NoSubCamera.dll; DestDir: {autopf}\NoSub Studio Camera; Components: camera; Flags: ignoreversion
Source: {#RepoRoot}\build\native-camera-windows\licenses\*; DestDir: {autopf}\NoSub Studio Camera\licenses; Components: camera; Flags: ignoreversion

[Registry]
Root: HKLM64; Subkey: SOFTWARE\Classes\CLSID\{{A9179078-9633-49C0-A36E-312B7E861A70}; Flags: uninsdeletekeyifempty; Components: camera
Root: HKLM64; Subkey: SOFTWARE\Classes\CLSID\{{A9179078-9633-49C0-A36E-312B7E861A70}\InprocServer32; ValueType: string; ValueData: {autopf}\NoSub Studio Camera\NoSubCamera.dll; Flags: uninsdeletevalue uninsdeletekeyifempty; Components: camera
Root: HKLM64; Subkey: SOFTWARE\Classes\CLSID\{{A9179078-9633-49C0-A36E-312B7E861A70}\InprocServer32; ValueType: string; ValueName: ThreadingModel; ValueData: Both; Flags: uninsdeletevalue; Components: camera

[Icons]
Name: {group}\NoSub Studio; Filename: {app}\FreeCam.exe
Name: {autodesktop}\NoSub Studio; Filename: {app}\FreeCam.exe; Tasks: desktopicon

[Run]
Filename: {app}\FreeCam.exe; Description: Open NoSub Studio; Flags: nowait postinstall skipifsilent runasoriginaluser

[Code]
function GetFileAttributesW(lpFileName: String): LongWord;
  external 'GetFileAttributesW@kernel32.dll stdcall';

function SafeCameraPath: Boolean;
var Base: String;
begin
  Base := ExpandConstant('{autopf}\NoSub Studio Camera');
  Result := True;
  { Never follow a user-created junction, even for a known product filename. }
  if DirExists(Base) then Result := (GetFileAttributesW(Base) and $400) = 0;
  if DirExists(Base + '\licenses') then
    Result := Result and ((GetFileAttributesW(Base + '\licenses') and $400) = 0);
  if FileExists(Base + '\NoSubCamera.dll') then
    Result := Result and ((GetFileAttributesW(Base + '\NoSubCamera.dll') and $400) = 0);
  if FileExists(Base + '\licenses\Microsoft-Windows-Camera.txt') then
    Result := Result and ((GetFileAttributesW(Base + '\licenses\Microsoft-Windows-Camera.txt') and $400) = 0);
  if FileExists(Base + '\licenses\Microsoft-WIL.txt') then
    Result := Result and ((GetFileAttributesW(Base + '\licenses\Microsoft-WIL.txt') and $400) = 0);
end;

function ValidateCameraOwnership: Boolean;
var Existing: String;
begin
  Result := SafeCameraPath;
  if not Result then begin
    MsgBox('The camera installation path is unsafe. No changes were made. Contact NoSub support.', mbError, MB_OK);
    exit;
  end;
  if RegQueryStringValue(HKLM64,
    'SOFTWARE\Classes\CLSID\{A9179078-9633-49C0-A36E-312B7E861A70}\InprocServer32', '', Existing) then
    if CompareText(Existing, ExpandConstant('{autopf}\NoSub Studio Camera\NoSubCamera.dll')) <> 0 then begin
      MsgBox('An unexpected camera registration was found. Setup will not overwrite it. Contact NoSub support.', mbError, MB_OK);
      Result := False;
    end;
end;

function InitializeSetup: Boolean;
begin
  Result := ValidateCameraOwnership;
end;

function InitializeUninstall: Boolean;
begin
  Result := ValidateCameraOwnership;
end;

procedure RegisterExtraCloseApplicationsResources;
begin
  RegisterExtraCloseApplicationsResource(True, ExpandConstant('{autopf}\NoSub Studio Camera\NoSubCamera.dll'));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if CheckForMutexes('NoSubStudio.Desktop.InstallGuard') then
    Result := 'Choose Quit NoSub Studio from its notification-area menu before installing. Closing its window is not enough.';
end;
