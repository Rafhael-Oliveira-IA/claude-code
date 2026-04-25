$env:PATH = "C:\Users\rafha\.bun\bin;" + $env:PATH
Set-Location f:\claude-code

$created = @()
$attempt = 0

while ($attempt -lt 80) {
    $attempt++
    $out = bun run src/main.tsx --version 2>&1 | Out-String
    
    if ($out -match "Cannot find module '([^']+)' from '([^']+)'") {
        $missingModule = $Matches[1]
        $fromFile = $Matches[2]
        
        Write-Host "[$attempt] Missing: $missingModule from $fromFile"
        
        if ($missingModule -match '^\.') {
            $fromDir = Split-Path $fromFile -Parent
            # Try .ts extension first
            $modulePath = $missingModule -replace '\.js$', '.ts'
            $absPath = Join-Path $fromDir $modulePath
            $absPath = [System.IO.Path]::GetFullPath($absPath)
            
            # Also try .tsx
            $absPathTsx = $absPath -replace '\.ts$', '.tsx'
            
            if (-not (Test-Path $absPath) -and -not (Test-Path $absPathTsx)) {
                $dir = Split-Path $absPath -Parent
                if (-not (Test-Path $dir)) {
                    New-Item -ItemType Directory -Path $dir -Force | Out-Null
                }
                
                # Check if it's an .md file
                if ($missingModule -match '\.md$') {
                    $absPath = Join-Path $fromDir $missingModule
                    $absPath = [System.IO.Path]::GetFullPath($absPath)
                    Set-Content -Path $absPath -Value "# Stub`n"
                } else {
                    Set-Content -Path $absPath -Value "// Auto-generated stub`nexport {}`n"
                }
                $created += $absPath
                Write-Host "  Created: $absPath"
            } else {
                Write-Host "  Already exists: $absPath - might be wrong extension or circular"
                break
            }
        } else {
            Write-Host "  EXTERNAL PACKAGE: $missingModule"
            break
        }
    } elseif ($out -match "error:") {
        Write-Host "Other error:"
        Write-Host ($out | Select-String "error:" | Select-Object -First 5)
        break
    } else {
        Write-Host "SUCCESS - no more missing modules!"
        Write-Host $out
        break
    }
}

Write-Host "`nTotal stubs created: $($created.Count)"
$created | ForEach-Object { Write-Host "  $_" }
