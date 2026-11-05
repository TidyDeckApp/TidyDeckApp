; TidyDeck - script Inno Setup 6 (OFFICIEL, livree avec la source)
;
; Rappelle-le : TidyDeck n'exige PAS d'installeur. Le dossier construit par
; PyInstaller se copie ou l'utilisateur le veut, et c'est comme ca que le
; logiciel est congu (une seule instance, aucun service installe). Ce script est
; fourni pour celles et ceux qui preferent un vrai installeur .exe, ou pour une
; entreprise qui deploie par GPO.
;
; Construire :
;   1) build_env\Scripts\pyinstaller --noconfirm --clean ^
;        "TidyDeck_v2\TidyDeck\packaging\TidyDeck.spec" --distpath dist --workpath work
;   2) ISCC.exe packaging\tidydeck.iss          (Inno Setup 6)
;
; Installation par utilisateur (pas d'admin) : TidyDeck ne reclame les droits
; administrateur qu'au cas par cas, via l'invite UAC du logiciel lui-meme.

#define MyAppName "TidyDeck"
#define MyAppVersion "0.6.1"
; Nom de l'editeur tel qu'il s'affiche dans « Applications installees » :
; c'est le signataire de la licence (voir LICENSE), pas le nom du logiciel.
#define MyAppPublisher "Florius"
#define MyAppURL "https://tidydeckapp.app"
#define MySource "..\..\..\dist\TidyDeck"

[Setup]
AppId={{8B6E4C1D-6F2A-4A7B-9D3E-5C0A1F7B2E94}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableWelcomePage=no
; Pas d'admin : on installe dans {localappdata}, accessible sans UAC.
PrivilegesRequired=lowest
OutputBaseFilename=TidyDeck-{#MyAppVersion}-installateur
OutputDir=.
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\tidydeck.ico
UninstallDisplayIcon={app}\TidyDeck.exe
UninstallDisplayName={#MyAppName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#MySource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\TidyDeck.exe"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\TidyDeck.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TidyDeck.exe"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
// L'entree « demarrer avec Windows » pointe vers l'ancien chemin si l'utilisateur
// avait deja TidyDeck ailleurs : on la retire a la desinstallation pour ne pas
// laisser de ligne orpheline dans la cle Run.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'TidyDeck') then
      Log('Entree Run TidyDeck supprimee')
    else
      Log('Rien a retirer de la cle Run');
  end;
end;
