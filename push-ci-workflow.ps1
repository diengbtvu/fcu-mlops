# Quick Push Script - Push CI workflow to GitHub
# Windows PowerShell Script

Write-Host "Pushing GitHub Actions CI Workflow to GitHub..." -ForegroundColor Cyan
Write-Host ""

# Check git status
Write-Host "Checking git status..." -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "Adding files to git..." -ForegroundColor Yellow

# Add workflow files
git add .github/
git add README.md
git add predict-service/.flake8
git add predict-service/pyproject.toml
git add predict-service/tests/

Write-Host "Files added!" -ForegroundColor Green
Write-Host ""

# Show what will be committed
Write-Host "Files to be committed:" -ForegroundColor Yellow
git status --short

Write-Host ""
$confirm = Read-Host "Do you want to commit and push? (y/n)"

if ($confirm -eq 'y' -or $confirm -eq 'Y') {
    Write-Host ""
    Write-Host "Committing..." -ForegroundColor Yellow
    
    git commit -m "feat: Add GitHub Actions CI workflow with testing & quality checks

- Add CI workflow with 5 jobs (Laravel, Python, Docker, Security, Summary)
- Add Flake8, Black, isort configurations for Python
- Add example pytest tests structure
- Add comprehensive workflow documentation
- Update README with CI status badges
- Add setup guides and troubleshooting docs"

    Write-Host ""
    Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
    git push origin main
    
    Write-Host ""
    Write-Host "DONE! Check Actions tab on GitHub:" -ForegroundColor Green
    Write-Host "   https://github.com/nguyenhuuluan1702/PCS_MLops/actions" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Your CI workflow is now active!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Push cancelled. You can run this script again later." -ForegroundColor Red
}
