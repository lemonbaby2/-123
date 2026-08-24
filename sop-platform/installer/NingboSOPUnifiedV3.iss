#define AppName "宁波SOP多人标注与决策平台 V3"
#define AppVersion "2026.08.24.3"
#define AppExe "NingboSOPUnifiedV3.exe"
[Setup]
AppId={{BB5EFF48-0B33-41AE-8518-B8AD42889D41}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=宁波零部件SOP项目组
DefaultDirName={localappdata}\Programs\NingboSOPUnifiedV3
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\release-v3
OutputBaseFilename=宁波SOP多人标注与决策平台_V3_安装程序_20260824
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
VersionInfoVersion=2026.8.24.3
VersionInfoDescription=分布式预标注、五人协同、CVAT、三模型训练、实时SOP与MES审计客户端
[Tasks]
Name: desktopicon; Description: "创建桌面快捷方式"; Flags: checkedonce
[Files]
Source: "..\dist-v3\NingboSOPUnifiedV3\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\40_V3多人标注审计与公网部署说明_20260824.md"; DestDir: "{app}\docs"; Flags: ignoreversion
[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
[Run]
Filename: "{app}\{#AppExe}"; Description: "启动 {#AppName}"; Flags: nowait postinstall skipifsilent
