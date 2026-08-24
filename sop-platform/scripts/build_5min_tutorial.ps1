param()

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$ffmpeg = 'D:\Anaconda\Library\bin\ffmpeg.exe'
$ffprobe = 'D:\Anaconda\Library\bin\ffprobe.exe'
$ttsPython = 'C:\Users\Administrator\.hermes\hermes-agent\venv\Scripts\python.exe'
$truststoreSite = 'C:\Users\Administrator\AppData\Roaming\Python\Python312\site-packages'
$out = Join-Path $root 'output\tutorial'
$frames = Join-Path $out 'frames'
$work = Join-Path $out 'work'
$voice = Join-Path $out 'voice'
$media = Join-Path $root 'web\media'
$font = 'C\:/Windows/Fonts/msyh.ttc'
New-Item -ItemType Directory -Path $work, $voice -Force | Out-Null

function Invoke-FFmpeg([string[]]$Arguments) {
  & $ffmpeg -hide_banner -loglevel error -y @Arguments
  if ($LASTEXITCODE -ne 0) { throw "FFmpeg 失败：$($Arguments -join ' ')" }
}

function New-StillSegment([string]$Image, [double]$Duration, [string]$Output) {
  $filter = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=white,zoompan=z='min(zoom+0.00008,1.025)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=$([int]($Duration*30)):s=1920x1080:fps=30,format=yuv420p"
  Invoke-FFmpeg @('-loop','1','-i',$Image,'-t',"$Duration",'-vf',$filter,'-an','-c:v','libx264','-preset','veryfast','-crf','20',$Output)
}

function New-VideoSegment([string]$SourceVideo, [double]$Start, [double]$Duration, [string]$Output) {
  Invoke-FFmpeg @('-ss',"$Start",'-i',$SourceVideo,'-t',"$Duration",'-vf','scale=1920:854:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x07121d,format=yuv420p','-an','-c:v','libx264','-preset','veryfast','-crf','20',$Output)
}

$segmentSpecs = @(
  @{id='00_intro'; image='01_总览.png'; duration=20},
  @{id='01_overview'; image='01_总览.png'; duration=30},
  @{id='02_ingest'; image='02_数据获取与清洗.png'; duration=40},
  @{id='03_prelabel_a'; image='03_AI预标注与证据.png'; duration=15},
  @{id='04_cvat'; image='04_CVAT人工复核.png'; duration=50},
  @{id='05_dataset'; image='05_数据集构建.png'; duration=35},
  @{id='06_training'; image='06_训练与部署.png'; duration=40},
  @{id='07_mes_a'; image='07_实时SOP_MES.png'; duration=10},
  @{id='08_outro'; image='01_总览.png'; duration=10}
)

foreach ($spec in $segmentSpecs) {
  New-StillSegment (Join-Path $frames $spec.image) $spec.duration (Join-Path $work ($spec.id + '.mp4'))
}
New-VideoSegment (Join-Path $media '仪表板SOP_视频六_0f1c_改进YOLO26_SAHI_TTA_WBF_无遮挡版.mp4') 8 25 (Join-Path $work '03_prelabel_b.mp4')
New-VideoSegment (Join-Path $media '仪表板SOP_YOLOv8逐帧识别演示_小目标增强版_右侧SOP步骤面板版.mp4') 28 25 (Join-Path $work '07_mes_b.mp4')

$videoOrder = '00_intro','01_overview','02_ingest','03_prelabel_a','03_prelabel_b','04_cvat','05_dataset','06_training','07_mes_a','07_mes_b','08_outro'
$videoList = Join-Path $work 'video_concat.txt'
[System.IO.File]::WriteAllLines($videoList, ($videoOrder | ForEach-Object { "file '$((Join-Path $work ($_.ToString()+'.mp4')).Replace("'","''"))'" }), [System.Text.UTF8Encoding]::new($false))
$baseVideo = Join-Path $work 'tutorial_base_300s.mp4'
Invoke-FFmpeg @('-f','concat','-safe','0','-i',$videoList,'-c','copy',$baseVideo)

$plans = Get-Content -LiteralPath (Join-Path $out 'narration_sections.json') -Raw -Encoding utf8 | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $ttsPython)) { throw "未找到中文配音工具：$ttsPython" }
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = $truststoreSite
$processedAudio = @()
foreach ($plan in $plans) {
  $raw = Join-Path $voice ($plan.id + '_raw.mp3')
  $fixed = Join-Path $voice ($plan.id + '.wav')
  if (Test-Path -LiteralPath $raw) { Remove-Item -LiteralPath $raw -Force }
  & $ttsPython -c "import truststore; truststore.inject_into_ssl(); from edge_tts.util import main; main()" --voice 'zh-CN-YunyangNeural' --text ([string]$plan.text) --write-media $raw
  if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $raw)) { throw "中文配音生成失败：$($plan.id)" }
  $rawDuration = [double](& $ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $raw)
  $targetSpeech = [math]::Max(1, [double]$plan.duration - 2)
  if ($rawDuration -gt $targetSpeech) {
    $tempo = $rawDuration / $targetSpeech
    Invoke-FFmpeg @('-i',$raw,'-af',("atempo={0:F6},apad,atrim=duration={1}" -f $tempo,$plan.duration),'-ar','48000','-ac','2',$fixed)
  } else {
    Invoke-FFmpeg @('-i',$raw,'-af',("adelay=800|800,apad,atrim=duration={0}" -f $plan.duration),'-ar','48000','-ac','2',$fixed)
  }
  $processedAudio += $fixed
}
$env:PYTHONPATH = $previousPythonPath
$audioList = Join-Path $work 'audio_concat.txt'
[System.IO.File]::WriteAllLines($audioList, ($processedAudio | ForEach-Object { "file '$($_.Replace("'","''"))'" }), [System.Text.UTF8Encoding]::new($false))
$fullAudio = Join-Path $work 'narration_300s.wav'
Invoke-FFmpeg @('-f','concat','-safe','0','-i',$audioList,'-c:a','pcm_s16le',$fullAudio)

$assTemp = Join-Path $env:TEMP 'sop_tutorial_overlay.ass'
Copy-Item -LiteralPath (Join-Path $out 'tutorial_overlay.ass') -Destination $assTemp -Force
$ass = $assTemp.Replace('\','/').Replace(':','\:')
$final = Join-Path $out '宁波视觉SOP_CVAT闭环平台_5分钟中文配音字幕教学_20260824.mp4'
Invoke-FFmpeg @('-i',$baseVideo,'-i',$fullAudio,'-vf',("ass='{0}':fontsdir='C\:/Windows/Fonts'" -f $ass),'-c:v','libx264','-preset','medium','-crf','20','-c:a','aac','-b:a','192k','-t','300','-movflags','+faststart',$final)

Write-Host "教学视频：$final"
