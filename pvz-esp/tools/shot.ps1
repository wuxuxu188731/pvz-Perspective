param(
  [string]$Out = "D:\ge\pvzHE\pvzHE\pvz-esp\shots\shot.png",
  [string]$ProcName = "PlantsVsZombies",
  [switch]$Screen
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class W {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr hWnd, out RECT lpRect);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr hWnd, ref POINT lpPoint);
  [DllImport("shcore.dll")] public static extern int SetProcessDpiAwareness(int v);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);
  [DllImport("user32.dll")] public static extern IntPtr GetWindowDC(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);
}
"@
try { [W]::SetProcessDpiAwareness(2) | Out-Null } catch { }

$p = Get-Process $ProcName -ErrorAction Stop | Select-Object -First 1
$h = $p.MainWindowHandle
if ($h -eq [IntPtr]::Zero) { throw "no main window" }

$c = New-Object W+RECT
[W]::GetClientRect($h, [ref]$c) | Out-Null
$cw = $c.Right
$ch = $c.Bottom
$pt = New-Object W+POINT
[W]::ClientToScreen($h, [ref]$pt) | Out-Null

$bmp = New-Object System.Drawing.Bitmap($cw, $ch)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
$ok = [W]::PrintWindow($h, $hdc, 3)
$g.ReleaseHdc($hdc)
$g.Dispose()

if (-not $ok) {
  # fallback: screen copy of the client area
  $bmp2 = New-Object System.Drawing.Bitmap($cw, $ch)
  $g2 = [System.Drawing.Graphics]::FromImage($bmp2)
  $g2.CopyFromScreen($pt.X, $pt.Y, 0, 0, (New-Object System.Drawing.Size($cw, $ch)))
  $g2.Dispose()
  $bmp.Dispose()
  $bmp = $bmp2
  $mode = "screen-fallback"
} else {
  $mode = "printwindow"
}

if ($Screen) {
  $bmp3 = New-Object System.Drawing.Bitmap($cw, $ch)
  $g3 = [System.Drawing.Graphics]::FromImage($bmp3)
  $g3.CopyFromScreen($pt.X, $pt.Y, 0, 0, (New-Object System.Drawing.Size($cw, $ch)))
  $g3.Dispose()
  $bmp.Dispose()
  $bmp = $bmp3
  $mode = "screen-forced"
}

$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
"client={0}x{1} origin={2},{3} mode={4} -> {5}" -f $cw, $ch, $pt.X, $pt.Y, $mode, $Out
