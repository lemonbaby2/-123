$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$git = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"
$extensions = @(".md", ".py", ".ps1", ".toml", ".yaml", ".yml", ".xml", ".txt", ".hpp", ".cpp", ".cff", ".bib", ".ply")
$names = @("LICENSE", ".gitignore", ".gitattributes", "CMakeLists.txt")
$encoding = New-Object System.Text.UTF8Encoding($false)
$paths = & $git -C $repoRoot diff --cached --name-only --diff-filter=ACM

foreach ($relative in $paths) {
    $path = Join-Path $repoRoot $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        continue
    }
    $item = Get-Item -LiteralPath $path
    if (($extensions -notcontains $item.Extension) -and ($names -notcontains $item.Name)) {
        continue
    }
    $content = [IO.File]::ReadAllText($item.FullName)
    $content = $content.TrimEnd([char[]]@([char]13, [char]10)) + "`n"
    [IO.File]::WriteAllText($item.FullName, $content, $encoding)
}
