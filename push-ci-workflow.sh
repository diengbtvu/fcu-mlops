#!/bin/bash
# Quick Push Script - Push CI workflow to GitHub
# Linux/Mac Bash Script

echo "Pushing GitHub Actions CI Workflow to GitHub..."
echo ""

# Check git status
echo "Checking git status..."
git status

echo ""
echo "Adding files to git..."

# Add workflow files
git add .github/
git add GITHUB_ACTIONS_SETUP.md
git add SETUP_COMPLETE.md
git add README.md
git add predict-service/.flake8
git add predict-service/pyproject.toml
git add predict-service/tests/

echo "Files added!"
echo ""

# Show what will be committed
echo "Files to be committed:"
git status --short

echo ""
read -p "Do you want to commit and push? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo ""
    echo "Committing..."
    
    git commit -m "feat: Add GitHub Actions CI workflow with testing & quality checks

- Add CI workflow with 5 jobs (Laravel, Python, Docker, Security, Summary)
- Add Flake8, Black, isort configurations for Python
- Add example pytest tests structure
- Add comprehensive workflow documentation
- Update README with CI status badges
- Add setup guides and troubleshooting docs"

    echo ""
    echo "Pushing to GitHub..."
    git push origin main
    
    echo ""
    echo "DONE! Check Actions tab on GitHub:"
    echo "   https://github.com/nguyenhuuluan1702/PCS_MLops/actions"
    echo ""
    echo "Your CI workflow is now active!"
else
    echo ""
    echo "Push cancelled. You can run this script again later."
fi
