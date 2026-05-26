$src = "E:\claude_Proj\BMI\ChipSeeker"
$dst = "E:\claude_Proj\BMI\ChipSeeker_Release"

# Remove old release if exists
if (Test-Path $dst) {
    Remove-Item $dst -Recurse -Force
    Write-Host "[build] Removed old release folder"
}

# Copy with exclusions
robocopy $src $dst /E /NFL /NDL /NJS /NJH `
    /XD .git __pycache__ .pytest_cache .kiro local_data .venv venv node_modules .claude `
    /XF config.local.json config.json *.pyc

# Remove any __pycache__ that slipped through
Get-ChildItem -Path $dst -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

# Count files
$fileCount = (Get-ChildItem -Path $dst -Recurse -File).Count
Write-Host ""
Write-Host "[build] Release built at: $dst"
Write-Host "[build] Total files: $fileCount"
