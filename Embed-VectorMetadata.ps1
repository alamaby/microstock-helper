<#
.SYNOPSIS
  Embed metadata Adobe Stock + Dreamstime ke paket vektor (JPG+SVG / JPG+EPS).

.DESCRIPTION
  Membaca CSV (SourceFile,Title,Description,Keywords,Copyright,Creator),
  memasangkan tiap baris dengan JPG preview (di JpgDir) dan file vektor
  (di VecDir) berdasar BASENAME yang sama (ekstensi diabaikan), menyalin
  keduanya ke OutDir, lalu meng-embed metadata:

    JPG -> triple-sync IPTC+XMP+EXIF (sama seperti Embed-JpgMetadata.ps1)
    EPS -> XMP-dc saja (Title/Description/Subject/Rights/Creator).
           ExifTool TERBUKTI bisa tulis+baca XMP pada EPS.
    SVG -> injeksi XML native (<title>, <desc>, paket RDF/XMP di <metadata>).
           ExifTool TIDAK mendukung tulis SVG, jadi ini best-effort;
           CSV pendamping tetap sumber kebenaran untuk upload.

  CSV agensi ikut disalin ke OutDir sebagai pendamping paket upload.
  File sumber tidak pernah diubah. Pencocokan fallback via nomor 3 digit
  (pola yang sama dengan Embed-JpgMetadata.ps1).

.EXAMPLE
  .\Embed-VectorMetadata.ps1 -CsvPath .\m_adobe.csv -JpgDir .\06_preview_jpg -VecDir .\05_svg -OutDir .\for_adobe -VecKind svg
  .\Embed-VectorMetadata.ps1 -CsvPath .\m_adobe.csv -JpgDir .\06_preview_jpg -VecDir .\07_eps -OutDir .\for_adobe -VecKind eps -DryRun
#>
[CmdletBinding()]
param(
  [string]$CsvPath = "",
  [string]$JpgDir = "",
  [string]$VecDir = "",
  [string]$OutDir = "",
  [ValidateSet("auto", "svg", "eps")][string]$VecKind = "auto",
  [string]$ExifTool = "C:\Apps\exiftool\exiftool.exe",
  [switch]$DryRun,
  [switch]$KeepBackup
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  EMBED-VECTOR v1.0 - JPG triple-sync + EPS XMP + SVG XML" -ForegroundColor Cyan
Write-Host ""

function Ask-Path($prompt, $mustBe, $default = "") {
  while ($true) {
    $hint = if ($default) { " [Enter=$default]" } else { "" }
    $v = (Read-Host "$prompt$hint").Trim().Trim('"')
    if (-not $v -and $default) { return $default }
    if (-not $v) { continue }
    if ($mustBe -eq "any") { return $v }
    if ($mustBe -eq "dir" -and (Test-Path $v -PathType Container)) { return $v }
    if ($mustBe -eq "file" -and (Test-Path $v -PathType Leaf)) { return $v }
    Write-Host "  (!) tidak ditemukan: $v" -ForegroundColor Yellow
  }
}

if (-not $CsvPath -or -not (Test-Path $CsvPath -PathType Leaf)) { $CsvPath = Ask-Path "Path file CSV metadata" "file" }
if (-not $JpgDir -or -not (Test-Path $JpgDir -PathType Container)) { $JpgDir = Ask-Path "Folder JPG preview" "dir" }
if (-not $VecDir -or -not (Test-Path $VecDir -PathType Container)) { $VecDir = Ask-Path "Folder file vektor (SVG/EPS)" "dir" }
if (-not (Test-Path $ExifTool -PathType Leaf)) { throw "ExifTool tidak ada: $ExifTool" }
if (-not $OutDir) {
  $suf = if ($CsvPath -match "dreamstime") { "_for_dreamstime" } else { "_for_upload" }
  if ($CsvPath -match "adobe") { $suf = "_for_adobe" }
  $defOut = (Get-Item $JpgDir).Parent.FullName.TrimEnd("\", "/") + $suf
  $OutDir = Ask-Path "Folder output paket" "any" $defOut
}

$script:spinIdx = 0
function Show-Bar($done, $total, $label) {
  $w = 24
  $p = if ($total -gt 0) { $done / $total } else { 1 }
  $f = [math]::Min($w, [int][math]::Floor($p * $w))
  $bar = if ($f -ge $w) { "=" * $w } else { ("=" * $f) + ">" + ("-" * ($w - $f - 1)) }
  $ch = @("|", "/", "-", "\")[$script:spinIdx % 4]; $script:spinIdx++
  if ($label.Length -gt 42) { $label = "..." + $label.Substring($label.Length - 39) }
  Write-Host ("`r[{0}] {1}/{2} {3} {4}   " -f $bar, $done, $total, $ch, $label) -NoNewline
}

function Get-FileNumber([string]$name) {
  $best = $null; $bestScore = 0
  foreach ($m in [regex]::Matches($name, "(?<!\d)(\d{3})(?!\d)")) {
    $prev = if ($m.Index -ge 2 -and $name.Substring($m.Index - 2, 2) -eq "__") { "__" }
            elseif ($m.Index -ge 1) { $name[$m.Index - 1] } else { "" }
    $score = if ($prev -eq "__") { 3 } elseif ($prev -eq "_" -or $prev -eq "-" -or $prev -eq "") { 2 } else { 1 }
    if ($score -gt $bestScore) { $bestScore = $score; $best = $m.Groups[1].Value }
    elseif ($score -eq $bestScore -and $best -ne $m.Groups[1].Value) { $best = $null }
  }
  return $best
}

function Find-Pair($dirFiles, [string]$csvName, [string[]]$exts) {
  # 1) basename sama (abaikan ekstensi), 2) fallback nomor 3 digit.
  $base = [IO.Path]::GetFileNameWithoutExtension($csvName)
  $hit = @($dirFiles | Where-Object {
    ([IO.Path]::GetFileNameWithoutExtension($_) -ieq $base) -and
    ($exts -contains ([IO.Path]::GetExtension($_).ToLower()))
  })
  $via = "exact"
  if (-not $hit) {
    $num = Get-FileNumber $csvName
    if ($num) {
      $hit = @($dirFiles | Where-Object {
        (Get-FileNumber $_) -eq $num -and ($exts -contains ([IO.Path]::GetExtension($_).ToLower()))
      })
    }
    if ($hit.Count -eq 1) { $via = "#$num" } else { $hit = @() }
  }
  if ($hit.Count -gt 1) {
    # Ambigu (mis. base ganda): pilih yang nama persis dulu bila ada.
    $ex = @($hit | Where-Object { $_ -ieq $csvName })
    if ($ex.Count -eq 1) { $hit = $ex; $via = "exact" }
  }
  return @{ File = if ($hit.Count -ge 1) { $hit[0] } else { $null }; Via = $via }
}

function Test-JpgReal([string]$path) {
  $fs = [IO.File]::OpenRead($path); $mg = New-Object byte[] 4
  [void]$fs.Read($mg, 0, 4); $fs.Close()
  return ($mg[0] -eq 0xFF -and $mg[1] -eq 0xD8)
}

function Test-VecReal([string]$path, [string]$kind) {
  if ($kind -eq "eps") {
    $fs = [IO.File]::OpenRead($path); $mg = New-Object byte[] 4
    [void]$fs.Read($mg, 0, 4); $fs.Close()
    return ($mg[0] -eq 0x25 -and $mg[1] -eq 0x21 -and $mg[2] -eq 0x50 -and $mg[3] -eq 0x53)
  }
  try {
    $head = (Get-Content -LiteralPath $path -TotalCount 8 -ErrorAction Stop) -join "`n"
    return ($head -match "<svg")
  } catch { return $false }
}

function Invoke-ExifJpg($file, $r, $kws) {
  $reset = @("-XMP-dc:Title=", "-IPTC:ObjectName=", "-XMP-photoshop:Headline=",
    "-XMP-dc:Description=", "-IPTC:Caption-Abstract=", "-EXIF:ImageDescription=",
    "-IPTC:Keywords=", "-XMP-dc:Subject=")
  if ($r.Copyright) { $reset += "-XMP-dc:Rights=", "-IPTC:CopyrightNotice=", "-EXIF:Copyright=" }
  if ($r.Creator) { $reset += "-XMP-dc:Creator=", "-IPTC:By-line=", "-EXIF:Artist=" }
  if (-not $KeepBackup) { $reset = @("-overwrite_original") + $reset }
  & $ExifTool ($reset + @("-P", "-m", $file)) | Out-Null
  $args = @()
  if (-not $KeepBackup) { $args += "-overwrite_original" }
  $args += "-P", "-m", "-IPTC:CodedCharacterSet=UTF8"
  $args += "-XMP-dc:Title=$($r.Title)", "-IPTC:ObjectName=$($r.Title)", "-XMP-photoshop:Headline=$($r.Title)"
  $args += "-XMP-dc:Description=$($r.Description)", "-IPTC:Caption-Abstract=$($r.Description)", "-EXIF:ImageDescription=$($r.Description)"
  foreach ($k in $kws) { $args += "-IPTC:Keywords+=$k"; $args += "-XMP-dc:Subject+=$k" }
  if ($r.Copyright) { $args += "-XMP-dc:Rights=$($r.Copyright)", "-IPTC:CopyrightNotice=$($r.Copyright)", "-EXIF:Copyright=$($r.Copyright)" }
  if ($r.Creator) { $args += "-XMP-dc:Creator=$($r.Creator)", "-IPTC:By-line=$($r.Creator)", "-EXIF:Artist=$($r.Creator)" }
  $args += $file
  & $ExifTool @args | Out-Null
  return ($LASTEXITCODE -eq 0)
}

function Invoke-ExifEps($file, $r, $kws) {
  # EPS: hanya XMP-dc (IPTC/EXIF tidak valid untuk PostScript).
  $reset = @("-XMP-dc:Title=", "-XMP-dc:Description=", "-XMP-dc:Subject=")
  if ($r.Copyright) { $reset += "-XMP-dc:Rights=" }
  if ($r.Creator) { $reset += "-XMP-dc:Creator=" }
  if (-not $KeepBackup) { $reset = @("-overwrite_original") + $reset }
  & $ExifTool ($reset + @("-P", "-m", $file)) | Out-Null
  $args = @()
  if (-not $KeepBackup) { $args += "-overwrite_original" }
  $args += "-P", "-m"
  $args += "-XMP-dc:Title=$($r.Title)", "-XMP-dc:Description=$($r.Description)"
  foreach ($k in $kws) { $args += "-XMP-dc:Subject+=$k" }
  if ($r.Copyright) { $args += "-XMP-dc:Rights=$($r.Copyright)" }
  if ($r.Creator) { $args += "-XMP-dc:Creator=$($r.Creator)" }
  $args += $file
  & $ExifTool @args | Out-Null
  return ($LASTEXITCODE -eq 0)
}

function Set-SvgMetadata($file, $r, $kws) {
  # Injeksi XML native: <title>, <desc>, paket RDF/XMP di <metadata>.
  $svgNs = "http://www.w3.org/2000/svg"
  $rdfNs = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  $dcNs = "http://purl.org/dc/elements/1.1/"
  $xml = New-Object System.Xml.XmlDocument
  $xml.PreserveWhitespace = $true
  $xml.Load($file)
  $root = $xml.DocumentElement
  if ($root.LocalName -ne "svg") { throw "akar XML bukan <svg>." }
  $ns = $root.NamespaceURI
  if ([string]::IsNullOrWhiteSpace($ns)) { $ns = $svgNs }
  foreach ($tag in @("title", "desc", "metadata")) {
    foreach ($n in @($root.ChildNodes | Where-Object { $_ -is [System.Xml.XmlElement] -and $_.LocalName -eq $tag })) {
      [void]$root.RemoveChild($n)
    }
  }
  $title = $xml.CreateElement("title", $ns); $title.InnerText = $r.Title
  $desc = $xml.CreateElement("desc", $ns)
  $desc.InnerText = if ($r.Description) { $r.Description } else { $r.Title }
  $meta = $xml.CreateElement("metadata", $ns)
  $rdf = $xml.CreateElement("rdf", "RDF", $rdfNs)
  $rdesc = $xml.CreateElement("rdf", "Description", $rdfNs)
  $rdesc.SetAttribute("about", $rdfNs, "")
  $t2 = $xml.CreateElement("dc", "title", $dcNs); $t2.InnerText = $r.Title
  $d2 = $xml.CreateElement("dc", "description", $dcNs)
  $d2.InnerText = if ($r.Description) { $r.Description } else { $r.Title }
  $subj = $xml.CreateElement("dc", "subject", $dcNs)
  $bag = $xml.CreateElement("rdf", "Bag", $rdfNs)
  foreach ($k in $kws) {
    $li = $xml.CreateElement("rdf", "li", $rdfNs); $li.InnerText = $k
    [void]$bag.AppendChild($li)
  }
  [void]$subj.AppendChild($bag)
  [void]$rdesc.AppendChild($t2); [void]$rdesc.AppendChild($d2); [void]$rdesc.AppendChild($subj)
  if ($r.Copyright) {
    $rt = $xml.CreateElement("dc", "rights", $dcNs); $rt.InnerText = $r.Copyright
    [void]$rdesc.AppendChild($rt)
  }
  if ($r.Creator) {
    $cr = $xml.CreateElement("dc", "creator", $dcNs); $cr.InnerText = $r.Creator
    [void]$rdesc.AppendChild($cr)
  }
  [void]$rdf.AppendChild($rdesc); [void]$meta.AppendChild($rdf)
  # Sisip di depan agar title/desc/metadata jadi anak pertama (urutan rekomendasi SVG).
  [void]$root.InsertBefore($meta, $root.FirstChild)
  [void]$root.InsertBefore($desc, $root.FirstChild)
  [void]$root.InsertBefore($title, $root.FirstChild)
  $tmp = "$file.tmp"
  $xml.Save($tmp)
  Move-Item -LiteralPath $tmp -Destination $file -Force
}

function Test-SvgMetadata($file, $title, $kwCount) {
  try {
    $xml = New-Object System.Xml.XmlDocument
    $xml.Load($file)
    $root = $xml.DocumentElement
    $t = $root.SelectSingleNode("*[local-name()='title']")
    if (-not $t -or $t.InnerText -ne $title) { return $false }
    $lis = $root.SelectNodes("*[local-name()='metadata']//*[local-name()='li']")
    return ($lis.Count -eq $kwCount)
  } catch { return $false }
}

# ---------- Proses utama ----------
$rows = @(Import-Csv $CsvPath -Encoding UTF8)
$jpgFiles = @(Get-ChildItem $JpgDir -File | Select-Object -ExpandProperty Name)
$vecFiles = @(Get-ChildItem $VecDir -File | Select-Object -ExpandProperty Name)
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$vecExts = if ($VecKind -eq "svg") { @(".svg") } elseif ($VecKind -eq "eps") { @(".eps") } else { @(".svg", ".eps") }
$ok = 0; $fail = 0; $i = 0

Write-Host "CSV : $CsvPath ($($rows.Count) baris)"
Write-Host "JPG : $JpgDir"
Write-Host "VEC : $VecDir ($VecKind)"
Write-Host "Ke  : $OutDir"
if ($DryRun) { Write-Host "*** DRYRUN - tidak ada file yang ditulis ***" -ForegroundColor Cyan }
Write-Host ""

$isDream = $CsvPath -match "dreamstime"
foreach ($r in $rows) {
  $i++
  $pair1 = Find-Pair $jpgFiles $r.SourceFile @(".jpg", ".jpeg")
  $pair2 = Find-Pair $vecFiles $r.SourceFile $vecExts
  if (-not $pair1.File) { Write-Warning "SKIP (JPG tak cocok): $($r.SourceFile)"; $fail++; Show-Bar $i $rows.Count $r.SourceFile; continue }
  if (-not $pair2.File) { Write-Warning "SKIP (vektor tak cocok): $($r.SourceFile)"; $fail++; Show-Bar $i $rows.Count $r.SourceFile; continue }
  $vk = [IO.Path]::GetExtension($pair2.File).TrimStart(".").ToLower()

  if (-not (Test-JpgReal (Join-Path $JpgDir $pair1.File))) {
    Write-Warning "SKIP (JPG bukan jpeg asli): $($pair1.File)"; $fail++; Show-Bar $i $rows.Count $pair1.File; continue
  }
  if (-not (Test-VecReal (Join-Path $VecDir $pair2.File) $vk)) {
    Write-Warning "SKIP (vektor tidak valid): $($pair2.File)"; $fail++; Show-Bar $i $rows.Count $pair2.File; continue
  }

  $kws = @($r.Keywords -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ }) | Select-Object -Unique
  if (-not $isDream -and $r.Title.Length -gt 70) { Write-Warning "$($pair1.File) : Title $($r.Title.Length)ch > 70 (Adobe ideal)" }
  if ($r.Title.Length -gt 200) { Write-Warning "$($pair1.File) : Title $($r.Title.Length)ch > 200 (Dreamstime maks)" }
  if (-not $isDream -and $kws.Count -gt 49) { Write-Warning "$($pair1.File) : $($kws.Count) keywords > 49 (Adobe maks)" }
  if ($isDream -and $kws.Count -gt 80) { Write-Warning "$($pair1.File) : $($kws.Count) keywords > 80 (Dreamstime maks kata tunggal)" }
  if (-not $r.Description) { Write-Warning "$($pair1.File) : Description kosong" }

  $base = [IO.Path]::GetFileNameWithoutExtension($pair1.File)
  $dstJpg = Join-Path $OutDir ($base + [IO.Path]::GetExtension($pair1.File))
  $dstVec = Join-Path $OutDir ($base + "." + $vk)
  Show-Bar $i $rows.Count $base
  if ($DryRun) { continue }
  Copy-Item (Join-Path $JpgDir $pair1.File) $dstJpg -Force
  Copy-Item (Join-Path $VecDir $pair2.File) $dstVec -Force

  if (-not (Invoke-ExifJpg $dstJpg $r $kws)) { Write-Warning "GAGAL embed JPG: $base"; $fail++; continue }
  $jpgTitle = (& $ExifTool -s -s -s -XMP-dc:Title $dstJpg)
  if ($jpgTitle -ne $r.Title) { Write-Warning "PERIKSA JPG $base (Title tak cocok baca-balik)"; $fail++; continue }

  if ($vk -eq "eps") {
    if (-not (Invoke-ExifEps $dstVec $r $kws)) { Write-Warning "GAGAL embed EPS: $base"; $fail++; continue }
    $eTitle = (& $ExifTool -s -s -s -XMP-dc:Title $dstVec)
    $eKw = @((& $ExifTool -s -s -s -XMP-dc:Subject $dstVec) -split ',\s*' | Where-Object { $_ })
    if ($eTitle -ne $r.Title -or $eKw.Count -ne $kws.Count) {
      Write-Warning "PERIKSA EPS $base [KW=$($eKw.Count)/$($kws.Count), Title OK: $($eTitle -eq $r.Title)]"; $fail++; continue
    }
  } else {
    try {
      Set-SvgMetadata $dstVec $r $kws
    } catch {
      Write-Warning "GAGAL embed SVG ${base}: $($_.Exception.Message)"; $fail++; continue
    }
    if (-not (Test-SvgMetadata $dstVec $r.Title $kws.Count)) {
      Write-Warning "PERIKSA SVG $base (verifikasi baca-balik gagal)"; $fail++; continue
    }
  }
  $tag = if ($pair1.Via -eq "exact" -and $pair2.Via -eq "exact") { "OK" } else { "OK[auto]" }
  Write-Output "$tag $base [JPG+${vk}, KW=$($kws.Count)]"
  $ok++
}

if (-not $DryRun) {
  Copy-Item $CsvPath (Join-Path $OutDir (Split-Path $CsvPath -Leaf)) -Force
  Write-Host "  CSV pendamping disalin ke: $OutDir" -ForegroundColor Gray
}

Write-Host ""
Write-Host ""
if ($fail -eq 0) {
  Write-Host "  Selesai: $ok OK dari $($rows.Count) baris." -ForegroundColor Green
} else {
  Write-Host ("  Selesai: {0} OK, {1} gagal/skip dari {2} baris." -f $ok, $fail, $rows.Count) -ForegroundColor Yellow
}
if ($DryRun) { Write-Host "  (DryRun - ulangi tanpa -DryRun untuk tulis asli)" -ForegroundColor Cyan }
if ($fail -gt 0) { exit 1 }
