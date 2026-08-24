#define MyAppName "宁波视觉SOP与CVAT闭环平台"
#define MyAppVersion "2026.08.24"
#define MyAppPublisher "宁波零部件SOP项目组"
#define MyAppExeName "NingboSOPCVAT.exe"

[Setup]
AppId={{938968F0-5F49-4A53-B472-F03700C21A64}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\NingboSOPCVAT
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=宁波视觉SOP_CVAT闭环平台_完整安装程序_20260824
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName={#MyAppName}
VersionInfoVersion=2026.8.24.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=三产线、三算法、CVAT标注、训练发布、SOP实时检测与MES闭环桌面平台
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: checkedonce

[Files]
Source: "..\dist\NingboSOPCVAT\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
