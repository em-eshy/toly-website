param(
  [int]$Port = 5173,
  [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$rootPath = [System.IO.Path]::GetFullPath($Root)
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
$listener.Start()
Write-Host "Serving $rootPath at http://localhost:$Port/"

$contentTypes = @{
  ".html" = "text/html; charset=utf-8"
  ".css" = "text/css; charset=utf-8"
  ".js" = "application/javascript; charset=utf-8"
  ".json" = "application/json; charset=utf-8"
  ".svg" = "image/svg+xml"
  ".png" = "image/png"
  ".jpg" = "image/jpeg"
  ".jpeg" = "image/jpeg"
  ".webp" = "image/webp"
}

function Send-Response($Stream, [int]$Status, [string]$ContentType, [byte[]]$Body) {
  $reason = if ($Status -eq 200) { "OK" } elseif ($Status -eq 403) { "Forbidden" } else { "Not Found" }
  $header = "HTTP/1.1 $Status $reason`r`nContent-Type: $ContentType`r`nContent-Length: $($Body.Length)`r`nConnection: close`r`n`r`n"
  $headerBytes = [System.Text.Encoding]::ASCII.GetBytes($header)
  $Stream.Write($headerBytes, 0, $headerBytes.Length)
  $Stream.Write($Body, 0, $Body.Length)
}

try {
  while ($true) {
    $client = $listener.AcceptTcpClient()
    try {
      $stream = $client.GetStream()
      $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::ASCII, $false, 1024, $true)
      $requestLine = $reader.ReadLine()

      if (-not $requestLine) {
        $client.Close()
        continue
      }

      $parts = $requestLine.Split(" ")
      $path = if ($parts.Length -gt 1) { $parts[1] } else { "/" }
      $path = $path.Split("?")[0].TrimStart("/")
      $relative = [System.Uri]::UnescapeDataString($path)
      if ([string]::IsNullOrWhiteSpace($relative)) {
        $relative = "index.html"
      }

      $target = Join-Path $rootPath $relative
      $resolved = [System.IO.Path]::GetFullPath($target)

      if (-not $resolved.StartsWith($rootPath)) {
        Send-Response $stream 403 "text/plain; charset=utf-8" ([System.Text.Encoding]::UTF8.GetBytes("Forbidden"))
        $client.Close()
        continue
      }

      if ([System.IO.Directory]::Exists($resolved)) {
        $resolved = Join-Path $resolved "index.html"
      }

      if (-not [System.IO.File]::Exists($resolved)) {
        Send-Response $stream 404 "text/plain; charset=utf-8" ([System.Text.Encoding]::UTF8.GetBytes("Not found"))
        $client.Close()
        continue
      }

      $ext = [System.IO.Path]::GetExtension($resolved).ToLowerInvariant()
      $contentType = $contentTypes[$ext]
      if (-not $contentType) {
        $contentType = "application/octet-stream"
      }

      Send-Response $stream 200 $contentType ([System.IO.File]::ReadAllBytes($resolved))
      $client.Close()
    }
    catch {
      $client.Close()
    }
  }
}
finally {
  $listener.Stop()
}
