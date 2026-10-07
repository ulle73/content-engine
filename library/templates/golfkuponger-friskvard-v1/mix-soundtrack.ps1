# Builds assets/soundtrack.wav: ACE-Step BGM (from its 4.693s phrase start) + beat-placed SFX.
# Grid: 165 BPM, beat = 0.363636s. Frame starts: 0, 4.364, 10.182, 14.545, 20.364, 24.727. Total 30.545s.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$total = 30.545
$musicStart = 4.693

# file, time-in-video (s), offset-in-file (s), length (s, 0 = whole), gain
$cues = @(
  # F1 hook
  @('whoosh-short',      0.00,  0.0, 0,    0.30),
  @('sparkle',           2.909, 0.0, 0,    0.18),
  # F1 -> F2 zoom-through
  @('whoosh-short',      4.25,  0.0, 0,    0.40),
  # F2 count-up: riser ends at the landing, soft impact on landing, sparkle on shimmer
  @('riser',             6.10,  1.5, 1.9,  0.40),
  @('impact-bass-1',     8.00,  0.0, 0,    0.50),
  @('sparkle',           8.728, 0.0, 0,    0.22),
  # F2 -> F3, chips
  @('whoosh-short',     10.08,  0.0, 0,    0.25),
  @('click-soft',       11.273, 0.0, 0,    0.22),
  @('click-soft',       11.637, 0.0, 0,    0.22),
  @('click-soft',       12.000, 0.0, 0,    0.22),
  @('click-soft',       12.364, 0.0, 0,    0.22),
  # F3 -> F4, club swaps
  @('whoosh-short',     14.45,  0.0, 0,    0.25),
  @('whoosh-short',     15.95,  0.0, 0,    0.14),
  @('whoosh-short',     17.40,  0.0, 0,    0.14),
  @('whoosh-short',     18.86,  0.0, 0,    0.14),
  # F4 -> F5 push-slide, logo cards
  @('whoosh-short',     20.27,  0.0, 0,    0.30),
  @('click-soft',       21.091, 0.0, 0,    0.22),
  @('click-soft',       21.455, 0.0, 0,    0.22),
  @('click-soft',       21.819, 0.0, 0,    0.22),
  @('click-soft',       22.182, 0.0, 0,    0.22),
  # F6 close: cinematic whoosh peaks into the light sweep, chime on emblem landing, sparkle on URL shimmer
  @('whoosh-cinematic', 23.50,  1.0, 3.0,  0.32),
  @('chime',            25.42,  0.0, 0,    1.40),
  @('sparkle',          28.363, 0.0, 0,    0.22)
)

$inputs = @('-i', 'assets/bgm.wav')
$filters = @("[0:a]atrim=start=${musicStart}:duration=${total},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.02,afade=t=out:st=29.85:d=0.69,volume=0.9[m]")
$labels = @('[m]')
for ($i = 0; $i -lt $cues.Count; $i++) {
  $c = $cues[$i]; $n = $i + 1
  $inputs += @('-i', "assets/sfx/$($c[0]).mp3")
  $trim = if ($c[3] -gt 0) { "atrim=start=$($c[2]):duration=$($c[3])," } elseif ($c[2] -gt 0) { "atrim=start=$($c[2])," } else { '' }
  $tail = if ($c[3] -gt 0) { "afade=t=out:st=$([math]::Max(0,$c[3]-0.06)):d=0.06," } else { '' }
  $ms = [int][math]::Round($c[1] * 1000)
  $filters += "[$n`:a]aresample=48000,aformat=channel_layouts=stereo,${trim}asetpts=PTS-STARTPTS,${tail}volume=$($c[4]),adelay=${ms}|${ms}[s$n]"
  $labels += "[s$n]"
}
$filters += ($labels -join '') + "amix=inputs=$($labels.Count):normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000[out]"
$fc = $filters -join ';'
ffmpeg -y -hide_banner -loglevel error @inputs -filter_complex $fc -map '[out]' -t $total -c:a pcm_s16le assets/soundtrack.wav
ffprobe -v error -show_entries format=duration -of csv=p=0 assets/soundtrack.wav
