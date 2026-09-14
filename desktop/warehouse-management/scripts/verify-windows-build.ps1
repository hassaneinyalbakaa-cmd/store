param(
  [Parameter(Mandatory = $true)]
  [string]$Path,

  [string]$ExpectedPublisherSubject,

  [string]$ExpectedCertificateThumbprint
)

$ErrorActionPreference = "Stop"
$expectedProductName = "نظام إدارة المخزن"
$expectedCompanyName = "Warehouse Management"
$expectedVersion = (Get-Content (Join-Path $PSScriptRoot "..\package.json") | ConvertFrom-Json).version

if (-not $ExpectedPublisherSubject -and -not $ExpectedCertificateThumbprint) {
  throw "Provide ExpectedPublisherSubject or ExpectedCertificateThumbprint."
}

$files = $Path.Split(",", [System.StringSplitOptions]::RemoveEmptyEntries) |
  ForEach-Object { $_.Trim() }

foreach ($file in $files) {
  $item = Get-Item $file
  $signature = Get-AuthenticodeSignature $item.FullName
  $version = $item.VersionInfo

  Write-Host "File: $($item.FullName)"
  Write-Host "Publisher: $($signature.SignerCertificate.Subject)"
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
    $signature.SignerCertificate.Thumbprint -ne $ExpectedCertificateThumbprint
  ) {
    throw "Unexpected signing certificate thumbprint: $($signature.SignerCertificate.Thumbprint)"
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