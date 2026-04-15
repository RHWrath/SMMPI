#define MyAppName "ADB-Media-Manager"
#include "version.iss"
#define MyAppPublisher "ADB-Media-Manager"
#define MyAppExeName "ADB-Media-Manager.exe"

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

[Files]
Source: "dist\ADB-Media-Manager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "release_notes.txt"; Flags: dontcopy

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  ReleaseNotesPage: TOutputMsgMemoWizardPage;

procedure InitializeWizard;
var
  Notes: AnsiString;
begin
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
    FileExists(InstallDir + '\ADB-Media-Manager.exe') and
    FileExists(InstallDir + '\_internal\version.json') and
    FileExists(InstallDir + '\_internal\.install_marker');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Msg: string;
begin
  Result := True;

  if CurPageID = wpSelectDir then
  begin
    if IsUpgradeInstall(WizardDirValue) then
      Msg := 'Existing ADB-Media-Manager installation detected. The installer will update and overwrite the old application files.'
    else
      Msg := 'No previous ADB-Media-Manager installation detected. A new installation will be created.';

    MsgBox(Msg, mbInformation, MB_OK);
  end;
end;