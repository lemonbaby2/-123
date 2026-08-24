#define MyAppName "宁波SOP + CVAT一体化工作台 V2"
#define MyAppVersion "2026.08.24.2"
#define MyAppPublisher "宁波零部件SOP项目组"
#define MyAppExeName "NingboSOPUnified.exe"

[Setup]
AppId={{FD90C978-7F5F-4B41-8F4E-D689DF66BA0B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\NingboSOPUnified
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\release-unified
OutputBaseFilename=宁波SOP_CVAT一体化工作台_V2_安装程序_20260824
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayName={#MyAppName}
VersionInfoVersion=2026.8.24.2
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=统一登录、数据清洗、CVAT标注、三模型训练验证、实时SOP与MES闭环客户端
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: checkedonce

[Files]
Source: "..\dist-unified\NingboSOPUnified\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\38_SOP_CVAT一体化工作台与公网部署说明_20260824.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\39_V2构建与公网验收报告_20260824.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\scripts\Start-CloudflareQuickTunnel.ps1"; DestDir: "{app}\cloudflare"; Flags: ignoreversion
Source: "..\scripts\Stop-CloudflareQuickTunnel.ps1"; DestDir: "{app}\cloudflare"; Flags: ignoreversion
Source: "..\scripts\Test-LegacyWebIntegrity.ps1"; DestDir: "{app}\cloudflare"; Flags: ignoreversion
Source: "..\deploy\cloudflare\config.named.example.yml"; DestDir: "{app}\cloudflare"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
