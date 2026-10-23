# Run with the 32-bit Windows PowerShell for the x86 overlay assembly.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$exe = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\bin\Overlay.exe'))
$assembly = [Reflection.Assembly]::LoadFile($exe)
$draw = $assembly.GetType('PvzEsp.Renderer').GetMethod('Draw')
$images = @()
foreach ($origin in @([Drawing.Point]::new(0,0), [Drawing.Point]::new(317,159), [Drawing.Point]::new(-600,80))) {
    $bitmap = [Drawing.Bitmap]::new(880,600)
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    $stream = [IO.MemoryStream]::new()
    try {
        $graphics.Clear([Drawing.Color]::Black)
        $rect = [Drawing.Rectangle]::new($origin.X,$origin.Y,880,600)
        $draw.Invoke($null, @($graphics,$rect,$null,[double]60,$false)) | Out-Null
        if (-not $graphics.Transform.IsIdentity) { throw 'Graphics state was not restored' }
        $bitmap.Save($stream,[Drawing.Imaging.ImageFormat]::Png)
        $images += [Convert]::ToBase64String($stream.ToArray())
    }
    finally {
        $stream.Dispose()
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}
if ($images[0] -ne $images[1] -or $images[0] -ne $images[2]) { throw 'Rendering depends on screen origin' }
Write-Output 'PASS: rendering is independent of screen origin; graphics state restored.'
