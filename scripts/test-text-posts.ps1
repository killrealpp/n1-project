$ErrorActionPreference = "Stop"

param(
  [string]$EnvPath = ".env"
)

function Read-DotEnv {
  param([string]$Path)

  if (!(Test-Path $Path)) {
    throw "Env file not found: $Path"
  }

  $vars = @{}
  Get-Content $Path | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }

    $idx = $line.IndexOf("=")
    if ($idx -lt 1) { return }

    $key = $line.Substring(0, $idx).Trim()
    $value = $line.Substring($idx + 1).Trim()
    $vars[$key] = $value
  }

  return $vars
}

function Add-Result {
  param(
    [System.Collections.Generic.List[object]]$Results,
    [string]$Platform,
    [bool]$Ok,
    [string]$Detail
  )

  $Results.Add([pscustomobject]@{
    platform = $Platform
    ok = $Ok
    detail = $Detail
  })
}

$vars = Read-DotEnv -Path $EnvPath
$results = New-Object System.Collections.Generic.List[object]
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"

if ($vars["TELEGRAM_BOT_TOKEN"] -and $vars["TELEGRAM_TARGET_CHAT_ID"]) {
  try {
    $body = @{
      chat_id = $vars["TELEGRAM_TARGET_CHAT_ID"]
      text = "Test autopost: Telegram text message. $stamp"
    } | ConvertTo-Json -Compress

    $url = "https://api.telegram.org/bot$($vars["TELEGRAM_BOT_TOKEN"])/sendMessage"
    $resp = Invoke-RestMethod -Uri $url -Method Post -ContentType "application/json" -Body $body -TimeoutSec 30
    Add-Result $results "telegram" $true "message_id=$($resp.result.message_id)"
  } catch {
    $err = $_.Exception.Message
    if ($_.ErrorDetails.Message) { $err = $_.ErrorDetails.Message }
    $err = $err -replace [Regex]::Escape($vars["TELEGRAM_BOT_TOKEN"]), "<redacted>"
    Add-Result $results "telegram" $false $err
  }
} else {
  Add-Result $results "telegram" $false "missing TELEGRAM_BOT_TOKEN or TELEGRAM_TARGET_CHAT_ID"
}

if ($vars["VK_TOKEN"] -and $vars["VK_ID"]) {
  try {
    $ownerId = $vars["VK_ID"].Trim()
    $num = 0L
    if ([long]::TryParse($ownerId, [ref]$num) -and $num -gt 0) {
      $ownerId = (-1 * $num).ToString()
    }

    $body = @{
      owner_id = $ownerId
      from_group = "1"
      message = "Test autopost: VK text message. $stamp"
      access_token = $vars["VK_TOKEN"]
      v = "5.199"
    }

    $resp = Invoke-RestMethod -Uri "https://api.vk.com/method/wall.post" -Method Post -Body $body -TimeoutSec 30
    if ($resp.response -and $resp.response.post_id) {
      Add-Result $results "vk" $true "post_id=$($resp.response.post_id)"
    } elseif ($resp.error) {
      Add-Result $results "vk" $false "error_code=$($resp.error.error_code); error_msg=$($resp.error.error_msg)"
    } else {
      Add-Result $results "vk" $false "unexpected response without response.post_id or error"
    }
  } catch {
    $err = $_.Exception.Message
    if ($_.ErrorDetails.Message) { $err = $_.ErrorDetails.Message }
    $err = $err -replace [Regex]::Escape($vars["VK_TOKEN"]), "<redacted>"
    Add-Result $results "vk" $false $err
  }
} else {
  Add-Result $results "vk" $false "missing VK_TOKEN or VK_ID"
}

if ($vars["MAX_ACCESS_TOKEN"] -and $vars["MAX_CHAT_ID"]) {
  try {
    $base = "https://platform-api2.max.ru"
    if ($vars["MAX_API_BASE_URL"]) {
      $base = $vars["MAX_API_BASE_URL"].TrimEnd("/")
    }

    $body = @{
      text = "Test autopost: MAX text message. $stamp"
    } | ConvertTo-Json -Compress

    $url = "$base/messages?chat_id=$([uri]::EscapeDataString($vars["MAX_CHAT_ID"]))"
    $resp = Invoke-RestMethod -Uri $url -Method Post -Headers @{ Authorization = $vars["MAX_ACCESS_TOKEN"] } -ContentType "application/json" -Body $body -TimeoutSec 30
    $detail = "request accepted"
    if ($resp.message) { $detail = "message returned" }
    Add-Result $results "max" $true $detail
  } catch {
    $err = $_.Exception.Message
    if ($_.ErrorDetails.Message) { $err = $_.ErrorDetails.Message }
    $err = $err -replace [Regex]::Escape($vars["MAX_ACCESS_TOKEN"]), "<redacted>"
    Add-Result $results "max" $false $err
  }
} else {
  Add-Result $results "max" $false "missing MAX_ACCESS_TOKEN or MAX_CHAT_ID"
}

$results | Format-Table -AutoSize
