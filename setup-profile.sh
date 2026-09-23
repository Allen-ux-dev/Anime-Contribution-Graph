#!/usr/bin/env bash
set -euo pipefail

OWNER="${1:-$(gh api user --jq .login)}"
PROFILE_REPO="$OWNER/$OWNER"
GRAPH_URL="https://raw.githubusercontent.com/$OWNER/Anime-Contribution-Graph/output/anime-contribution.svg"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required. Install it with: brew install gh"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  gh auth login --web --git-protocol https
fi

if ! gh repo view "$PROFILE_REPO" >/dev/null 2>&1; then
  echo "Creating profile repository $PROFILE_REPO ..."
  gh repo create "$PROFILE_REPO" --public --description "GitHub profile README"
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

gh repo clone "$PROFILE_REPO" "$TMP/profile" >/dev/null 2>&1 || true
cd "$TMP/profile"

if [[ -f README.md ]]; then
  cp README.md README.md.backup
fi

cat > README.md <<EOF
<p align="center">
  <img width="100%" alt="Anime Contribution Graph" src="$GRAPH_URL" />
</p>
EOF

git add README.md
if git diff --cached --quiet; then
  echo "Profile README is already up to date."
  exit 0
fi

git -c user.name="$OWNER" -c user.email="${OWNER}@users.noreply.github.com" commit -m "Add Anime Contribution Graph"
git push origin HEAD:main

echo
echo "Done. Open: https://github.com/$OWNER"
