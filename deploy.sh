#!/usr/bin/env bash
set -euo pipefail

REPO_NAME="${REPO_NAME:-Anime-Contribution-Graph}"
VISIBILITY="${VISIBILITY:-public}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT"

echo "============================================================"
echo " Anime Contribution Graph — GitHub one-click deploy"
echo "============================================================"
echo

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "❌ Missing command: $1"
    return 1
  fi
}

if ! need_cmd git; then
  echo
  echo "Install Apple's Command Line Tools first:"
  echo "  xcode-select --install"
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "❌ GitHub CLI (gh) is not installed."
  echo
  if command -v brew >/dev/null 2>&1; then
    read -r -p "Install GitHub CLI with Homebrew now? [Y/n] " ans
    ans="${ans:-Y}"
    if [[ "$ans" =~ ^[Yy]$ ]]; then
      brew install gh
    else
      exit 1
    fi
  else
    echo "Install Homebrew or GitHub CLI first, then run this script again."
    echo "GitHub CLI: https://cli.github.com/"
    exit 1
  fi
fi

if ! gh auth status >/dev/null 2>&1; then
  echo
  echo "GitHub login is required."
  gh auth login --web --git-protocol https
fi

OWNER="$(gh api user --jq .login)"
FULL_REPO="$OWNER/$REPO_NAME"

echo
echo "GitHub account : $OWNER"
echo "Repository     : $FULL_REPO"
echo "Visibility     : $VISIBILITY"
echo

if gh repo view "$FULL_REPO" >/dev/null 2>&1; then
  echo "✓ Repository already exists."
else
  echo "Creating repository..."
  if [[ "$VISIBILITY" == "private" ]]; then
    gh repo create "$FULL_REPO" --private --description "Anime-style animated GitHub contribution graph"
  else
    gh repo create "$FULL_REPO" --public --description "Anime-style animated GitHub contribution graph"
  fi
  echo "✓ Repository created."
fi

if [[ ! -d .git ]]; then
  git init
fi

git checkout -B main >/dev/null 2>&1 || git branch -M main

# Keep generated/local junk out of the repository.
cat > .gitignore <<'EOF'
.DS_Store
*.log
node_modules/
dist/
__pycache__/
EOF

git add -A

if ! git diff --cached --quiet; then
  git -c user.name="${GIT_AUTHOR_NAME:-Anime Contribution Graph}" \
      -c user.email="${GIT_AUTHOR_EMAIL:-actions@users.noreply.github.com}" \
      commit -m "Deploy Anime Contribution Graph web demo"
else
  echo "✓ No local file changes to commit."
fi

REMOTE_URL="https://github.com/$FULL_REPO.git"
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
fi

echo "Pushing main branch..."
git push -u origin main --force-with-lease 2>/dev/null || git push -u origin main
echo "✓ Source pushed."

echo
echo "Enabling GitHub Pages with Actions..."
set +e
gh api -X POST "repos/$FULL_REPO/pages" -f build_type=workflow >/dev/null 2>&1
POST_STATUS=$?
if [[ $POST_STATUS -ne 0 ]]; then
  gh api -X PUT "repos/$FULL_REPO/pages" -f build_type=workflow >/dev/null 2>&1
fi
set -e

echo "Triggering deployment workflow..."
sleep 3
if gh workflow run "Deploy Web Demo" --repo "$FULL_REPO" >/dev/null 2>&1; then
  echo "✓ Workflow started."
else
  echo "ℹ The push should already have triggered the workflow automatically."
fi

PAGES_URL="https://${OWNER}.github.io/${REPO_NAME}/"

echo
echo "============================================================"
echo " Deployment started"
echo "============================================================"
echo "Repository:"
echo "  https://github.com/$FULL_REPO"
echo
echo "Expected Pages URL:"
echo "  $PAGES_URL"
echo
echo "Watch deployment:"
echo "  https://github.com/$FULL_REPO/actions"
echo
echo "It usually becomes available after the GitHub Pages workflow finishes."
echo "============================================================"
