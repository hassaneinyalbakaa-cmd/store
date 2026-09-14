param(
  [Parameter(Mandatory = $true)]
  [string]$Path,

  [string]$ExpectedPublisherSubject,

  [string]$ExpectedCertificateThumbprint,

  [ValidateRange(1, 3650)]
  [int]$CertificateExpiryWarningDays = 60,

  [ValidateRange(0, 3650)]
  [int]$CertificateExpiryErrorDays = 30
)

$ErrorActionPreference = "Stop"
$expectedProductName = "نظام إدارة المخزن"
$expectedCompanyName = "Warehouse Management"
$expectedVersion = (Get-Content (Join-Path $PSScriptRoot "..\package.json") | ConvertFrom-Json).version

if (-not $ExpectedPublisherSubject -and -not $ExpectedCertificateThumbprint) {
  throw "Provide ExpectedPublisherSubject or ExpectedCertificateThumbprint."
}
if ($CertificateExpiryWarningDays -lt $CertificateExpiryErrorDays) {
  throw "CertificateExpiryWarningDays must be greater than or equal to CertificateExpiryErrorDays."
}

$normalizedExpectedThumbprint = $ExpectedCertificateThumbprint -replace "\s", ""

$files = $Path.Split(",", [System.StringSplitOptions]::RemoveEmptyEntries) |
  ForEach-Object { $_.Trim() }

foreach ($file in $files) {
  $item = Get-Item $file
  $signature = Get-AuthenticodeSignature $item.FullName
  $version = $item.VersionInfo

  Write-Host "File: $($item.FullName)"
  Write-Host "Publisher: $($signature.SignerCertificate.Subject)"
  Write-Host "Certificate thumbprint: $($signature.SignerCertificate.Thumbprint)"
  Write-Host "Certificate expires (UTC): $($signature.SignerCertificate.NotAfter.ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss'))"
  Write-Host "Signature: $($signature.Status)"
  Write-Host "Product: $($version.ProductName)"
  Write-Host "Company: $($version.CompanyName)"
  Write-Host "Version: $($version.ProductVersion)"

  if ($signature.Status -ne "Valid") {
    throw "Invalid Authenticode signature: $($signature.Status) - $($signature.StatusMessage)"
  }
  if (
    $ExpectedPublisherSubject -and
    $signature.SignerCertificate.Subject -ne $ExpectedPublisherSubject
  ) {
    throw "Unexpected publisher: $($signature.SignerCertificate.Subject)"
  }
  if (
    $ExpectedCertificateThumbprint -and
    ($signature.SignerCertificate.Thumbprint -replace "\s", "") -ne $normalizedExpectedThumbprint
  ) {
    throw "Unexpected signing certificate thumbprint: $($signature.SignerCertificate.Thumbprint)"
  }

  $expiresAt = $signature.SignerCertificate.NotAfter.ToUniversalTime()
  $remaining = $expiresAt - [DateTime]::UtcNow
  $remainingDays = [Math]::Floor($remaining.TotalDays)
  Write-Host "Certificate remaining validity: $remainingDays day(s)"

  if ($remaining.TotalDays -le $CertificateExpiryErrorDays) {
    throw "Signing certificate expires in $remainingDays day(s), at or below the $CertificateExpiryErrorDays-day release blocking threshold."
  }
  if ($remaining.TotalDays -le $CertificateExpiryWarningDays) {
    Write-Warning "Signing certificate expires in $remainingDays day(s), within the $CertificateExpiryWarningDays-day warning threshold. Start certificate renewal now."
  }
  if (-not $signature.TimeStamperCertificate) {
    throw "The executable has no trusted timestamp."
  }
  if ($version.ProductName -ne $expectedProductName) {
    throw "Unexpected product name: $($version.ProductName)"
  }
  if ($version.CompanyName -ne $expectedCompanyName) {
    throw "Unexpected company name: $($version.CompanyName)"
  }
  if ($version.ProductVersion -ne $expectedVersion) {
    throw "Unexpected product version: $($version.ProductVersion)"
  }
}

Write-Host "All Windows packages have a valid signature, timestamp, and file identity."