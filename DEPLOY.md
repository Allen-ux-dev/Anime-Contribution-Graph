# One-click deployment

## macOS

1. Unzip this folder.
2. Double-click `Deploy.command`.
3. If GitHub CLI is not installed, the script can install it through Homebrew.
4. Sign in to GitHub when the browser opens.
5. The script creates `Anime-Contribution-Graph`, pushes the demo, enables GitHub Pages with Actions, and starts the deployment.

Expected URL:

```text
https://YOUR_GITHUB_USERNAME.github.io/Anime-Contribution-Graph/
```

## Terminal

```bash
chmod +x deploy.sh
./deploy.sh
```

Optional custom repository name:

```bash
REPO_NAME=My-Anime-Graph ./deploy.sh
```

Optional private repository:

```bash
VISIBILITY=private ./deploy.sh
```

## GitHub Action

`.github/workflows/demo-pages.yml` deploys the static site every time `main` is pushed and can also be run manually from Actions.
