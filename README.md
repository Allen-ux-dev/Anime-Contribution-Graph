# Anime Contribution Graph

Turn your real GitHub contribution history into an animated anime-style profile card.

The generated SVG uses your live contribution data, draws exactly **three long heartbeat segments** across the year, and scales each heartbeat peak from the contribution volume in that roughly four-month period. The ECG line is drawn **left → right**, stays visible for about **3 seconds**, then redraws automatically.

## Profile README

Once the Action has generated the `output` branch, embed the English version in your profile README:

```html
<p align="center">
  <img width="100%" alt="Anime Contribution Graph" src="https://raw.githubusercontent.com/YOUR_NAME/Anime-Contribution-Graph/output/anime-contribution.svg" />
</p>
```

For this repository owner:

```html
<p align="center">
  <img width="100%" alt="Anime Contribution Graph" src="https://raw.githubusercontent.com/Allen-ux-dev/Anime-Contribution-Graph/output/anime-contribution.svg" />
</p>
```

## Automatic updates

`.github/workflows/anime.yml` regenerates the SVG from GitHub's GraphQL contribution calendar:

- every 3 hours;
- whenever the generator, workflow, or character assets change;
- whenever you press **Run workflow** manually.

The Action publishes these files to the `output` branch:

- `anime-contribution.svg` — English (default)
- `anime-contribution-zh.svg` — 简体中文
- `anime-contribution-ja.svg` — 日本語

## How the profile setup works

GitHub's built-in green contribution panel cannot be replaced or injected into. Projects such as `Platane/snk` work by generating an animated SVG and embedding that SVG in the **profile README**. This project follows the same deployment model.

Your profile README must live in the special repository named exactly after your GitHub username, for example `Allen-ux-dev/Allen-ux-dev`.

After creating that profile repository, its `README.md` only needs to reference this project's generated `output` SVG.

## Local generation

```bash
python -m pip install -r requirements.txt
GH_TOKEN="$(gh auth token)" python generate_anime.py \
  --user YOUR_NAME \
  --output anime-contribution.svg
```

Offline smoke test:

```bash
python generate_anime.py --user YOUR_NAME --demo --output demo.svg
```
