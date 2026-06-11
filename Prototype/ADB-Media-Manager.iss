#define MyAppName "ADB-Media-Manager"
#include "version.iss"
#define MyAppPublisher "ADB-Media-Manager"
#define MyAppExeName "ADB-Media-Manager.exe"
#define MyAndroidApkName "ADBMediaManagerCompanion.apk"

[Setup]
AppId={{B2F7C1D8-6B8D-4A2C-9F11-7C3E9D4A1111}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableDirPage=no
AllowNoIcons=yes
OutputDir=output
OutputBaseFilename=ADB-Media-Manager_Setup
SetupIconFile=ADB-Media-Manager.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
Name: "installandroidapp"; Description: "Install Android companion app to connected phone"; GroupDescription: "Android companion app:"; Flags: unchecked

[Files]
; Main Windows application.
; This includes _internal, version.json, platform-tools, adb.exe and all PyInstaller files.
Source: "dist\ADB-Media-Manager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Release notes shown inside the installer wizard.
Source: "release_notes.txt"; Flags: dontcopy

; Android companion APK.
; Source location before installer build:
; installer\android\ADBMediaManagerCompanion.apk
;
; Installed location:
; {app}\_internal\android\ADBMediaManagerCompanion.apk
Source: "android\{#MyAndroidApkName}"; DestDir: "{app}\_internal\android"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  ReleaseNotesPage: TOutputMsgMemoWizardPage;
  IsUpgradeMode: Boolean;
  BackupDir: String;
  InstallSucceeded: Boolean;

procedure InitializeWizard;
var
  Notes: AnsiString;
begin
  InstallSucceeded := False;
  IsUpgradeMode := False;
  BackupDir := '';

  ReleaseNotesPage :=
    CreateOutputMsgMemoPage(
      wpReady,
      'What''s New',
      'Changes in this version',
      'Here are the latest updates:',
      ''
    );

  Notes := '';

  try
    ExtractTemporaryFile('release_notes.txt');

    if LoadStringFromFile(ExpandConstant('{tmp}\release_notes.txt'), Notes) then
      ReleaseNotesPage.RichEditViewer.Lines.Text := Notes
    else
      ReleaseNotesPage.RichEditViewer.Lines.Text := 'No release notes available.';
  except
    ReleaseNotesPage.RichEditViewer.Lines.Text := 'No release notes available.';
  end;
end;

function IsUpgradeInstall(InstallDir: string): Boolean;
begin
  Result :=
    FileExists(InstallDir + '\{#MyAppExeName}') and
    FileExists(InstallDir + '\_internal\version.json') and
    FileExists(InstallDir + '\.install_marker');
end;

function GetBackupDir: String;
begin
  Result := ExpandConstant('{localappdata}\{#MyAppName}_Backup');
end;

function IsAppRunning: Boolean;
var
  ResultCode: Integer;
begin
  Result :=
    Exec(
      ExpandConstant('{cmd}'),
      '/C tasklist /FI "IMAGENAME eq {#MyAppExeName}" | find /I "{#MyAppExeName}" >nul',
      '',
      SW_HIDE,
      ewWaitUntilTerminated,
      ResultCode
    ) and (ResultCode = 0);
end;

function CopyDirRecursive(SourceDir, DestDir: String): Boolean;
var
  FindRec: TFindRec;
  SourcePath: String;
  DestPath: String;
begin
  Result := True;

  if not DirExists(SourceDir) then
    Exit;

  if not ForceDirectories(DestDir) then
  begin
    Result := False;
    Exit;
  end;

  if FindFirst(SourceDir + '\*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
        begin
          SourcePath := SourceDir + '\' + FindRec.Name;
          DestPath := DestDir + '\' + FindRec.Name;

          if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
          begin
            if not CopyDirRecursive(SourcePath, DestPath) then
            begin
              Result := False;
              Exit;
            end;
          end
          else
          begin
            if not FileCopy(SourcePath, DestPath, False) then
            begin
              Result := False;
              Exit;
            end;
          end;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

function CreateBackup: Boolean;
begin
  BackupDir := GetBackupDir;

  if DirExists(BackupDir) then
  begin
    if not DelTree(BackupDir, True, True, True) then
    begin
      Result := False;
      Exit;
    end;
  end;

  Result := CopyDirRecursive(WizardDirValue, BackupDir);
end;

function RestoreBackup: Boolean;
begin
  Result := True;

  if BackupDir = '' then
    Exit;

  if not DirExists(BackupDir) then
    Exit;

  if DirExists(WizardDirValue) then
  begin
    if not DelTree(WizardDirValue, True, True, True) then
    begin
      Result := False;
      Exit;
    end;
  end;

  Result := CopyDirRecursive(BackupDir, WizardDirValue);
end;

procedure CreateInstallMarker;
begin
  SaveStringToFile(
    ExpandConstant('{app}\.install_marker'),
    'ADB-Media-Manager installation marker',
    False
  );
end;

function GetAdbDir: String;
begin
  Result := ExpandConstant('{app}\_internal\platform-tools');
end;

function GetAdbPath: String;
begin
  Result := GetAdbDir + '\adb.exe';
end;

function GetApkPath: String;
begin
  Result := ExpandConstant('{app}\_internal\android\{#MyAndroidApkName}');
end;

function IsAdbAvailable: Boolean;
begin
  Result :=
    FileExists(GetAdbPath) and
    FileExists(GetAdbDir + '\AdbWinApi.dll') and
    FileExists(GetAdbDir + '\AdbWinUsbApi.dll');
end;

function GetAdbDevicesOutput(var Output: AnsiString): Boolean;
var
  ResultCode: Integer;
  TempFile: String;
begin
  TempFile := ExpandConstant('{tmp}\adb_devices.txt');

  Result :=
    Exec(
      ExpandConstant('{cmd}'),
      '/C ""' + GetAdbPath + '" devices > "' + TempFile + '""',
      GetAdbDir,
      SW_HIDE,
      ewWaitUntilTerminated,
      ResultCode
    ) and (ResultCode = 0);

  if Result then
    Result := LoadStringFromFile(TempFile, Output);
end;

function HasAuthorizedAndroidDevice: Boolean;
var
  Output: AnsiString;
begin
  Result := False;

  if not GetAdbDevicesOutput(Output) then
    Exit;

  Result :=
    (Pos(#9 + 'device', Output) > 0) or
    (Pos(' device', Output) > 0);
end;

function HasUnauthorizedAndroidDevice: Boolean;
var
  Output: AnsiString;
begin
  Result := False;

  if not GetAdbDevicesOutput(Output) then
    Exit;

  Result := Pos('unauthorized', Output) > 0;
end;

function InstallAndroidApk: Boolean;
var
  ResultCode: Integer;
begin
  Result :=
    Exec(
      GetAdbPath,
      'install -r "' + GetApkPath + '"',
      GetAdbDir,
      SW_SHOW,
      ewWaitUntilTerminated,
      ResultCode
    ) and (ResultCode = 0);
end;

procedure TryInstallAndroidApp;
begin
  if MsgBox(
    'The Android companion app can be installed to a connected Android phone.' + #13#10 + #13#10 +
    'Before continuing, make sure:' + #13#10 +
    '- the phone is connected by USB' + #13#10 +
    '- USB debugging is enabled' + #13#10 +
    '- the phone is unlocked' + #13#10 +
    '- you accept the USB debugging permission popup on the phone' + #13#10 + #13#10 +
    'Do you want to continue with Android app installation?',
    mbConfirmation,
    MB_YESNO
  ) <> IDYES then
  begin
    Exit;
  end;

  if not FileExists(GetApkPath) then
  begin
    MsgBox(
      'The Android APK could not be found in the installation folder.' + #13#10 + #13#10 +
      'Expected location:' + #13#10 +
      GetApkPath + #13#10 + #13#10 +
      'The Windows application was installed successfully, but the Android companion app could not be installed.',
      mbError,
      MB_OK
    );
    Exit;
  end;

  if not IsAdbAvailable then
  begin
    MsgBox(
      'ADB could not be found in the installation folder.' + #13#10 + #13#10 +
      'Expected location:' + #13#10 +
      GetAdbPath + #13#10 + #13#10 +
      'The Windows application was installed successfully, but the Android companion app could not be installed.',
      mbError,
      MB_OK
    );
    Exit;
  end;

  if HasUnauthorizedAndroidDevice then
  begin
    MsgBox(
      'An Android device was detected, but it is not authorized.' + #13#10 + #13#10 +
      'Please unlock the phone, accept the USB debugging permission popup, and then run the installer again or install the APK manually.',
      mbInformation,
      MB_OK
    );
    Exit;
  end;

  if not HasAuthorizedAndroidDevice then
  begin
    MsgBox(
      'No authorized Android device was detected.' + #13#10 + #13#10 +
      'The Windows application was installed successfully, but the Android companion app was not installed.' + #13#10 + #13#10 +
      'Please connect the phone, enable USB debugging, accept the authorization prompt, and try again.',
      mbInformation,
      MB_OK
    );
    Exit;
  end;

  if InstallAndroidApk then
  begin
    MsgBox(
      'The Android companion app was installed successfully.',
      mbInformation,
      MB_OK
    );
  end
  else
  begin
    MsgBox(
      'The Android companion app installation failed.' + #13#10 + #13#10 +
      'The Windows application was installed successfully. You can try installing the APK manually from:' + #13#10 +
      GetApkPath,
      mbError,
      MB_OK
    );
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Msg: string;
begin
  Result := True;

  if CurPageID = wpSelectDir then
  begin
    if IsUpgradeInstall(WizardDirValue) then
      Msg :=
        'Existing ADB-Media-Manager installation detected. ' +
        'The installer will update the application files. ' +
        'A backup will be created before the update starts.'
    else
      Msg :=
        'No previous ADB-Media-Manager installation detected. ' +
        'A new installation will be created.';

    MsgBox(Msg, mbInformation, MB_OK);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';

  IsUpgradeMode := IsUpgradeInstall(WizardDirValue);
  BackupDir := GetBackupDir;

  if IsUpgradeMode then
  begin
    if IsAppRunning then
    begin
      Result :=
        'ADB-Media-Manager is currently running. ' +
        'Please close the application before continuing with the update.';
      Exit;
    end;

    if not CreateBackup then
    begin
      Result :=
        'The installer could not create a backup of the existing installation. ' +
        'The update has been stopped to protect the currently installed version.';
      Exit;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    CreateInstallMarker;

    if WizardIsTaskSelected('installandroidapp') then
    begin
      TryInstallAndroidApp;
    end;
  end;

  if CurStep = ssDone then
  begin
    InstallSucceeded := True;

    if IsUpgradeMode and DirExists(BackupDir) then
      DelTree(BackupDir, True, True, True);
  end;
end;

procedure DeinitializeSetup;
begin
  if IsUpgradeMode and (not InstallSucceeded) and DirExists(BackupDir) then
  begin
    if RestoreBackup then
    begin
      MsgBox(
        'The update did not complete successfully. The previous installation has been restored from backup.',
        mbInformation,
        MB_OK
      );
    end
    else
    begin
      MsgBox(
        'The update did not complete successfully, and the installer could not fully restore the previous version from backup. Please check the installation folder manually.',
        mbError,
        MB_OK
      );
    end;
  end;
end;