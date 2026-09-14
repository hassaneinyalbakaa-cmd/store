param(
  [Parameter(Mandatory = $true)]
  [string]$CertificatePath,

  [SecureString]$CertificatePassword,

  [ValidateRange(1, 3650)]
  [int]$CertificateExpiryWarningDays = 60,

  [ValidateRange(0, 3650)]
  [int]$CertificateExpiryErrorDays = 30
)

$ErrorActionPreference = "Stop"

function Test-CertificateExpiry {
  param(
    [Parameter(Mandatory = $true)]
    [Security.Cryptography.X509Certificates.X509Certificate2]$Certificate
  )

  if ($CertificateExpiryWarningDays -lt $CertificateExpiryErrorDays) {
    throw "CertificateExpiryWarningDays must be greater than or equal to CertificateExpiryErrorDays."
  }

  $expiresAt = $Certificate.NotAfter.ToUniversalTime()
  $remaining = $expiresAt - [DateTime]::UtcNow
  $remainingDays = [Math]::Floor($remaining.TotalDays)

  Write-Host "Signing certificate expires (UTC): $($expiresAt.ToString('yyyy-MM-dd HH:mm:ss'))"
  Write-Host "Signing certificate remaining validity: $remainingDays day(s)"

  if ($remaining.TotalDays -le $CertificateExpiryErrorDays) {
    throw "Signing certificate expires in $remainingDays day(s), at or below the $CertificateExpiryErrorDays-day release blocking threshold. Replace the certificate before building."
  }
  if ($remaining.TotalDays -le $CertificateExpiryWarningDays) {
    Write-Warning "Signing certificate expires in $remainingDays day(s), within the $CertificateExpiryWarningDays-day warning threshold. Start certificate renewal now."
  }
}

if (-not $IsWindows -and $PSVersionTable.PSEdition -eq "Core") {
  throw "This release command must run on Windows."
}

$certificateFile = (Resolve-Path $CertificatePath).Path
if (-not $CertificatePassword) {
  $CertificatePassword = Read-Host "Certificate password" -AsSecureString
}

$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR(
  $CertificatePassword
)

try {
  $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
    $passwordPointer
  )
  $certificate = [Security.Cryptography.X509Certificates.X509Certificate2]::new(
    $certificateFile,
    $plainPassword,
    [Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet
  )

  if (-not $certificate.HasPrivateKey) {
    throw "The certificate does not contain a private key."
  }
  Test-CertificateExpiry -Certificate $certificate

  $env:WIN_CSC_LINK = $certificateFile
  $env:WIN_CSC_KEY_PASSWORD = $plainPassword

  $projectDirectory = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  $releaseDirectory = Join-Path $projectDirectory "release"
  $package = Get-Content (Join-Path $projectDirectory "package.json") |
    ConvertFrom-Json

  Push-Location $projectDirectory
  try {
    & pnpm run dist:win:signed
    if ($LASTEXITCODE -ne 0) {
      throw "Portable build failed with exit code $LASTEXITCODE."
    }

    & pnpm run dist:win:installer:signed
    if ($LASTEXITCODE -ne 0) {
      throw "NSIS installer build failed with exit code $LASTEXITCODE."
    }

    $portable = Join-Path $releaseDirectory (
      "Warehouse-Management-Portable-{0}.exe" -f $package.version
    )
    $installer = Join-Path $releaseDirectory (
      "Warehouse-Management-Setup-{0}.exe" -f $package.version
    )

    & (Join-Path $PSScriptRoot "verify-windows-build.ps1") `
      -Path "$portable,$installer" `
      -ExpectedPublisherSubject $certificate.Subject `
      -ExpectedCertificateThumbprint $certificate.Thumbprint `
      -CertificateExpiryWarningDays $CertificateExpiryWarningDays `
      -CertificateExpiryErrorDays $CertificateExpiryErrorDays

    if ($LASTEXITCODE -ne 0) {
      throw "Windows package verification failed with exit code $LASTEXITCODE."
    }

    Write-Host ""
    Write-Host "Signed Windows release completed successfully."
    Write-Host "Publisher: $($certificate.Subject)"
    Write-Host "Certificate thumbprint: $($certificate.Thumbprint)"
    Write-Host "Portable: $portable"
    Write-Host "Installer: $installer"
  }
  finally {
    Pop-Location
  }
}
finally {
  $env:WIN_CSC_LINK = $null
  $env:WIN_CSC_KEY_PASSWORD = $null
  $plainPassword = $null
  if ($passwordPointer -ne [IntPtr]::Zero) {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
  }
}