<#
.SYNOPSIS
Regenerates the logo and banner files the app and the README use, from the
originals in branding/.

.DESCRIPTION
Windows only: resizing goes through System.Drawing (GDI+), high-quality
bicubic, PNG output. Runs in Windows PowerShell 5.1 and PowerShell 7.
Output names carry the size: a new artwork gets new names, so browsers and
phones never keep the old image from their cache.

Run from anywhere:
  powershell -ExecutionPolicy Bypass -File scripts/generate_brand_assets.ps1
#>
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$repo = Split-Path -Parent $PSScriptRoot
$branding = Join-Path $repo 'branding'
$publicIcons = Join-Path $repo 'frontend/public/assets/icons'
$inlineIcons = Join-Path $repo 'frontend/src/assets/icons'

# Bounds of the artwork inside its transparent margin. Every original is a
# centred disk or a plain band, so its edges show on the middle row and column.
function Get-ArtworkBounds([System.Drawing.Bitmap]$image) {
  $midX = [int]($image.Width / 2)
  $midY = [int]($image.Height / 2)
  $left = 0
  while ($image.GetPixel($left, $midY).A -lt 128) { $left++ }
  $right = $image.Width - 1
  while ($image.GetPixel($right, $midY).A -lt 128) { $right-- }
  $top = 0
  while ($image.GetPixel($midX, $top).A -lt 128) { $top++ }
  $bottom = $image.Height - 1
  while ($image.GetPixel($midX, $bottom).A -lt 128) { $bottom-- }
  New-Object System.Drawing.Rectangle $left, $top, ($right - $left + 1), ($bottom - $top + 1)
}

# Draws the cropped artwork at $width x $height, centred on a $canvasWidth x
# $canvasHeight canvas, transparent unless a background colour is given.
function New-Derivative {
  param(
    [System.Drawing.Bitmap]$Source,
    [System.Drawing.Rectangle]$Crop,
    [int]$Width,
    [int]$Height,
    [int]$CanvasWidth = $Width,
    [int]$CanvasHeight = $Height,
    $Background = $null
  )
  $format = if ($Background) { 'Format24bppRgb' } else { 'Format32bppArgb' }
  $canvas = New-Object System.Drawing.Bitmap $CanvasWidth, $CanvasHeight, ([System.Drawing.Imaging.PixelFormat]::$format)
  $graphics = [System.Drawing.Graphics]::FromImage($canvas)
  $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
  $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
  $graphics.Clear($(if ($Background) { $Background } else { [System.Drawing.Color]::Transparent }))
  # The crop gets its own image and its edge pixels are mirrored: the resize
  # never samples the transparent margin, so no faded rim.
  $artwork = $Source.Clone($Crop, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $attributes = New-Object System.Drawing.Imaging.ImageAttributes
  $attributes.SetWrapMode([System.Drawing.Drawing2D.WrapMode]::TileFlipXY)
  $target = New-Object System.Drawing.Rectangle ([int](($CanvasWidth - $Width) / 2)), ([int](($CanvasHeight - $Height) / 2)), $Width, $Height
  $graphics.DrawImage($artwork, $target, 0, 0, $artwork.Width, $artwork.Height, [System.Drawing.GraphicsUnit]::Pixel, $attributes)
  $attributes.Dispose()
  $artwork.Dispose()
  $graphics.Dispose()
  $canvas
}

function Save-Png([System.Drawing.Bitmap]$image, [string]$path) {
  $image.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  '{0,-55} {1,4}x{2,-4} {3,9:N0} bytes' -f $path.Substring($repo.Length + 1), $image.Width, $image.Height, (Get-Item $path).Length
  $image.Dispose()
}

# Even diameter, so the disk sits exactly in the middle of the square.
function Get-InnerSize([int]$size, [double]$share) { [int][math]::Round($size * $share / 2) * 2 }

# --- Logo: the dark disk (mk_logo_clair), picked for the app's dark theme -----
$logo = [System.Drawing.Bitmap]::FromFile((Join-Path $branding 'mk_logo_clair.png'))
$disk = Get-ArtworkBounds $logo

# Transparent around the disk: browser tab, app logo, reconnect screen.
Save-Png (New-Derivative $logo $disk 32 32) (Join-Path $publicIcons 'mk-favicon-32.png')
Save-Png (New-Derivative $logo $disk 48 48) (Join-Path $publicIcons 'mk-favicon-48.png')
# 128: the largest on-screen logo is 56 px (sign-in wait), twice that for sharp screens.
Save-Png (New-Derivative $logo $disk 128 128) (Join-Path $publicIcons 'mk-logo-128.png')
# Inlined in the JS bundle (reconnect screen, 48 px): kept small.
Save-Png (New-Derivative $logo $disk 96 96) (Join-Path $inlineIcons 'mk-logo-96.png')

# Opaque squares (iOS paints transparency black): the corners take the disk's own
# colour, read just inside its top edge, so the disk melts into a full tile. The
# disk sits at 90 % (standard icons) or inside the 80 % safe zone launchers never
# crop (maskable).
$iconBackground = $logo.GetPixel($disk.X + [int]($disk.Width / 2), $disk.Y + [int]($disk.Height / 20))
$iconBackground = [System.Drawing.Color]::FromArgb(255, $iconBackground.R, $iconBackground.G, $iconBackground.B)
$tileBrush = New-Object System.Drawing.SolidBrush $iconBackground
foreach ($icon in @(
    @{ Name = 'mk-apple-touch-icon-180.png'; Size = 180; Share = 0.90 },
    @{ Name = 'mk-icon-192.png'; Size = 192; Share = 0.90 },
    @{ Name = 'mk-icon-512.png'; Size = 512; Share = 0.90 },
    @{ Name = 'mk-icon-maskable-512.png'; Size = 512; Share = 0.80 }
  )) {
  $inner = Get-InnerSize $icon.Size $icon.Share
  $tile = New-Derivative $logo $disk $inner $inner $icon.Size $icon.Size $iconBackground
  # The disk's anti-aliased rim is a shade darker than the disk: painted over with
  # the tile colour (everything outside a circle 3 % inside it), it leaves no ring.
  # The owl stays well inside that circle.
  $inset = [math]::Max(2, [int]($inner * 0.03))
  $offset = [int](($icon.Size - $inner) / 2) + $inset
  $rim = New-Object System.Drawing.Drawing2D.GraphicsPath
  $rim.AddRectangle((New-Object System.Drawing.Rectangle 0, 0, $icon.Size, $icon.Size))
  $rim.AddEllipse($offset, $offset, $inner - 2 * $inset, $inner - 2 * $inset)
  $graphics = [System.Drawing.Graphics]::FromImage($tile)
  $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $graphics.FillPath($tileBrush, $rim)
  $graphics.Dispose()
  $rim.Dispose()
  Save-Png $tile (Join-Path $publicIcons $icon.Name)
}
$tileBrush.Dispose()

$logo.Dispose()

# Notification badge: Android only keeps the alpha channel, so a disk would show
# as a plain dot. The owl alone becomes the shape, taken from the white-disk
# version: the further a pixel is from white, the more opaque.
$logo = [System.Drawing.Bitmap]::FromFile((Join-Path $branding 'mk_logo_sombre.png'))
$disk = Get-ArtworkBounds $logo
$badge = New-Derivative $logo $disk 96 96
for ($y = 0; $y -lt $badge.Height; $y++) {
  for ($x = 0; $x -lt $badge.Width; $x++) {
    $pixel = $badge.GetPixel($x, $y)
    $ink = 255 - [math]::Min($pixel.R, [math]::Min($pixel.G, $pixel.B))
    $alpha = [int]([math]::Min(1, $ink / 160) * $pixel.A)
    $badge.SetPixel($x, $y, [System.Drawing.Color]::FromArgb($alpha, 255, 255, 255))
  }
}
Save-Png $badge (Join-Path $publicIcons 'mk-badge-96.png')
$logo.Dispose()

# --- Banners ------------------------------------------------------------------
function Save-Banner([string]$original, [int]$width, [string]$path) {
  $banner = [System.Drawing.Bitmap]::FromFile((Join-Path $branding $original))
  $band = Get-ArtworkBounds $banner
  $height = [int][math]::Round($width * $band.Height / $band.Width)
  Save-Png (New-Derivative $banner $band $width $height) $path
  $banner.Dispose()
}

# Sign-in page: shown at 350 px at most, twice that for sharp screens.
Save-Banner 'mk_banner_clair.png' 700 (Join-Path $publicIcons 'mk-banner-700.png')
# README: shown at 640 px, one version per GitHub theme.
Save-Banner 'mk_banner_sombre.png' 1280 (Join-Path $branding 'mk_banner_sombre-1280.png')
Save-Banner 'mk_banner_clair.png' 1280 (Join-Path $branding 'mk_banner_clair-1280.png')
