; The Windows installer of SMTV (Inno Setup 6, free: https://jrsoftware.org/isinfo.php). Made by install/app/build.py:
;   ISCC /DAppVersion=0.1.0 /DSourceDir=build\app\win-x64\SMTV /DOutputDir=build\app install\app\smtv.iss
; For the signed-in person only, without administrator rights: the program goes to %LOCALAPPDATA%\Programs\SMTV, the
; icon to the Start menu (and the desktop, if ticked), «Uninstall» to Settings → Apps. Clips, jobs and settings live in
; SMTV's own folder (%USERPROFILE%\.smtv by default), never in the program's folder: an uninstall leaves them.
; The window's update (kind "exe") opens the new installer; it installs over the old version in the same folder.

#ifndef AppVersion
  #error AppVersion is needed: /DAppVersion=0.1.0
#endif
#ifndef SourceDir
  #error SourceDir is needed: the folder SMTV made by build.py
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif

[Setup]
; never change AppId: Windows finds the installed SMTV by it (updates, uninstall)
AppId={{6F0B7E52-6C1D-4E57-9C4B-3B7D2B1E5A10}
AppName=SMTV
AppVersion={#AppVersion}
AppVerName=SMTV {#AppVersion}
AppPublisher=StreamMoment
AppPublisherURL=https://streammoment.tv
AppSupportURL=https://github.com/yuriti/clipit/issues
AppUpdatesURL=https://github.com/yuriti/clipit/releases
DefaultDirName={localappdata}\Programs\SMTV
DefaultGroupName=SMTV
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir={#OutputDir}
OutputBaseFilename=SMTV-{#AppVersion}-windows-x64-setup
SetupIconFile={#SourceDir}\smtv.ico
UninstallDisplayIcon={app}\smtv.ico
UninstallDisplayName=SMTV
; ISCC itself is a 32-bit program: the 64 MB dictionary with 4 threads needs about 3 GB and stopped the build with
; «Out of memory». The compressor runs in its own 64-bit process (islzma64.exe), with 2 threads: about 1.5 GB.
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=2
WizardStyle=modern
; an update closes the running SMTV first (its files cannot be replaced while it runs)
CloseApplications=yes
RestartApplications=no
ShowLanguageDialog=auto

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "ja"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "ko"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; files of the previous version that the new one no longer has (packages change between versions)
Type: filesandordirs; Name: "{app}\Lib"
Type: filesandordirs; Name: "{app}\ffmpeg"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; SMTV.exe is Python's windowless program under SMTV's name; `-m smtv app` opens the window
Name: "{autoprograms}\SMTV"; Filename: "{app}\SMTV.exe"; Parameters: "-m smtv app"; WorkingDir: "{%USERPROFILE}"; IconFilename: "{app}\smtv.ico"; Comment: "SMTV"
Name: "{autodesktop}\SMTV"; Filename: "{app}\SMTV.exe"; Parameters: "-m smtv app"; WorkingDir: "{%USERPROFILE}"; IconFilename: "{app}\smtv.ico"; Comment: "SMTV"; Tasks: desktopicon

[Run]
Filename: "{app}\SMTV.exe"; Parameters: "-m smtv app"; WorkingDir: "{%USERPROFILE}"; Description: "{cm:LaunchProgram,SMTV}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; what Python wrote into the program's folder (compiled files, yt-dlp if it was added): the folder goes whole
Type: filesandordirs; Name: "{app}"
