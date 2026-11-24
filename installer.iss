#define AppName "HORIZION"
#define AppVersion "0.1.0"
#define AppPublisher "HORIZION Project"
#define AppExeName "HORIZION.exe"

[Setup]
AppId={{A19C25D1-5D2A-4A75-8A8E-0C10D8C5B701}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\HORIZION
DefaultGroupName={#AppName}
OutputDir=Output
OutputBaseFilename=HORIZION-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#AppExeName}

[Files]
Source: "dist\HORIZION\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\HORIZION"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\HORIZION"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch HORIZION"; Flags: postinstall nowait skipifsilent
