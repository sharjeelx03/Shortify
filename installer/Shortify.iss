#define MyAppName "Shortify"
#define MyAppVersion "0.6.0"
#define MyAppPublisher "Muhammad Sharjeel"
#define MyAppExeName "Shortify.exe"

[Setup]
AppId={{2D6D9CF2-5D2F-4D0C-85E8-000SHORTIFY}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
LicenseFile=..\LICENSE
OutputDir=..\release
OutputBaseFilename=Shortify_Setup_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Files]
Source: "..\dist\Shortify\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/c start \"\" \"https://ollama.com/download/windows\""; Description: "Open Ollama download page"; Flags: postinstall runhidden skipifsilent; Check: ShouldOpenOllama
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  AIPage: TInputOptionWizardPage;

procedure InitializeWizard;
begin
  AIPage := CreateInputOptionPage(
    wpSelectTasks,
    'AI Provider Setup',
    'Choose how you want to use Shortify AI.',
    'Shortify can use local Ollama or cloud API keys. Ollama is optional; it is not bundled with the installer.',
    False,
    False
  );

  AIPage.Add('I already have Ollama installed');
  AIPage.Add('I will use Claude / OpenAI / Gemini API keys instead');
  AIPage.Add('Open Ollama download page after installation');

  AIPage.Values[0] := True;
end;

function ShouldOpenOllama: Boolean;
begin
  Result := AIPage.Values[2];
end;
