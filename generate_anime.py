#!/usr/bin/env python3
"""Generate an animated anime-style GitHub contribution SVG.

The SVG is designed to be embedded directly in a GitHub profile README.
It uses only SVG/CSS animation (no JavaScript), so GitHub can render it as an image.

The last ~12 months of real contribution data are pulled from GitHub GraphQL.
The contribution grid is overlaid with exactly three stretched ECG/heartbeat
segments. Each segment covers roughly four months and its amplitude is driven by
that period's real contribution volume. The heartbeat is drawn left-to-right,
then remains visible for ~3 seconds before the drawing repeats.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import io
import subprocess
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

LEVEL = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

LANG = {
    "en": {
        "title": "Anime Contribution Graph",
        "subtitle": "A year of code, drawn as a heartbeat.",
        "normal": "NORMAL",
        "overdrive": "OVERDRIVE",
        "normal_quote": "Steady progress today as well.",
        "overdrive_quote": "Today's coding energy is maxed out!",
        "affection": "Affection",
        "today": "Today",
        "streak": "Streak",
        "total": "Total",
        "days": "days",
        "less": "Less",
        "more": "More",
        "updated": "Updated",
        "group": "4 months = 1 heartbeat · 3 beats per year",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    },
    "zh": {
        "title": "二次元贡献图",
        "subtitle": "把一年的代码，画成三次心跳。",
        "normal": "普通",
        "overdrive": "爆肝模式",
        "normal_quote": "今天也稳稳推进了一点。",
        "overdrive_quote": "今天的 coding energy 拉满啦！",
        "affection": "好感度",
        "today": "今天",
        "streak": "连续",
        "total": "总贡献",
        "days": "天",
        "less": "少",
        "more": "多",
        "updated": "更新于",
        "group": "4 个月 = 1 次长心跳 · 全年 3 次",
        "months": ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
    },
    "ja": {
        "title": "Anime Contribution Graph",
        "subtitle": "1年のコードを、3つの心拍として描く。",
        "normal": "通常",
        "overdrive": "オーバードライブ",
        "normal_quote": "今日も少しずつ進めたね。",
        "overdrive_quote": "今日のコーディングエネルギー、MAXだよ！",
        "affection": "好感度",
        "today": "今日",
        "streak": "連続",
        "total": "合計",
        "days": "日",
        "less": "少",
        "more": "多",
        "updated": "更新",
        "group": "4か月 = 1つの長い心拍 · 1年で3拍",
        "months": ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
    },
}


def token() -> str:
    for key in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.getenv(key):
            return os.environ[key]
    try:
        return subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=False
        ).stdout.strip()
    except FileNotFoundError:
        return ""


def fetch_weeks(user: str, tok: str):
    now = datetime.now(timezone.utc)
    frm = (now - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    query = """
    query($login:String!,$from:DateTime!){
      user(login:$login){
        contributionsCollection(from:$from){
          contributionCalendar{
            weeks{contributionDays{date contributionCount contributionLevel}}
          }
        }
      }
    }
    """
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": user, "from": frm}}).encode(),
        headers={
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
            "User-Agent": "Anime-Contribution-Graph",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.load(response)
    if data.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {data['errors']}")
    u = data.get("data", {}).get("user")
    if not u:
        raise RuntimeError(f"GitHub user not found: {user}")
    return u["contributionsCollection"]["contributionCalendar"]["weeks"]


def image_data_uri(path: Path) -> str:
    """Embed a compact portrait. Pillow keeps the generated SVG small enough
    to load comfortably through GitHub's image proxy."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((480, 480), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=88, optimize=True, progressive=True)
            raw = buf.getvalue()
        return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
    except Exception:
        raw = path.read_bytes()
        return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def flatten_days(weeks):
    out = []
    for week in weeks:
        for day in week.get("contributionDays", []):
            out.append(
                {
                    "date": day["date"],
                    "count": int(day["contributionCount"]),
                    "level": LEVEL.get(day["contributionLevel"], 0),
                }
            )
    return out


def current_streak(days) -> int:
    if not days:
        return 0
    ordered = sorted(days, key=lambda d: d["date"])
    i = len(ordered) - 1
    if i >= 0 and ordered[i]["count"] == 0:
        i -= 1
    streak = 0
    while i >= 0 and ordered[i]["count"] > 0:
        streak += 1
        i -= 1
    return streak


def stats(weeks):
    days = flatten_days(weeks)
    total = sum(d["count"] for d in days)
    today = days[-1]["count"] if days else 0
    last7 = sum(d["count"] for d in days[-7:])
    streak = current_streak(days)
    mode = "overdrive" if today >= 4 or last7 >= 18 else "normal"
    affection = max(18, min(100, round(35 + total * 0.42 + min(streak, 30) * 0.7)))
    return days, total, today, last7, streak, mode, affection


def month_labels(weeks, labels):
    result = []
    seen = None
    for col, week in enumerate(weeks):
        ds = week.get("contributionDays", [])
        if not ds:
            continue
        month = int(ds[0]["date"].split("-")[1])
        if month != seen:
            result.append((col, labels[month - 1]))
            seen = month
    if len(result) > 1 and result[1][0] <= 2:
        result = result[1:]
    return result


def heartbeat_path(weekly_totals, x0, y0, width, height):
    n = len(weekly_totals)
    if n == 0:
        return f"M {x0} {y0 + height/2} L {x0+width} {y0+height/2}", [0, 0, 0]
    cuts = [0, round(n / 3), round(2 * n / 3), n]
    groups = [sum(weekly_totals[cuts[i]:cuts[i + 1]]) for i in range(3)]
    gmax = max(max(groups), 1)
    base = y0 + height / 2
    seg = width / 3
    pts = [(x0, base)]
    for idx, value in enumerate(groups):
        start = x0 + idx * seg
        rel = value / gmax
        absolute = min(1.0, value / 80.0)
        strength = 0.45 * rel + 0.55 * absolute
        amp = 18 + 43 * strength
        dip = 8 + 18 * strength
        tiny = 2.5 + 4 * strength
        shape = [
            (0.00, 0), (0.16, 0),
            (0.235, -tiny), (0.285, 0),
            (0.40, 0), (0.465, 5 + 3 * strength),
            (0.525, -amp), (0.585, dip),
            (0.655, -amp * 0.22), (0.72, 0),
            (0.86, 0), (1.00, 0),
        ]
        for j, (t, dy) in enumerate(shape):
            if idx and j == 0:
                continue
            pts.append((start + t * seg, base + dy))
    d = " ".join(("M" if i == 0 else "L") + f" {x:.1f} {y:.1f}" for i, (x, y) in enumerate(pts))
    return d, groups


def render(user: str, weeks, lang: str, normal_uri: str, overdrive_uri: str) -> str:
    t = LANG[lang]
    days, total, today, last7, streak, mode, affection = stats(weeks)
    weekly_totals = [sum(int(d["contributionCount"]) for d in w.get("contributionDays", [])) for w in weeks]

    W, H = 1120, 360
    gx, gy = 38, 94
    cell, gap = 10, 3
    pitch = cell + gap
    gw = len(weeks) * pitch - gap
    gh = 7 * pitch - gap
    heartbeat, groups = heartbeat_path(weekly_totals, gx, gy - 10, gw, gh + 22)

    portrait_uri = overdrive_uri if mode == "overdrive" else normal_uri
    status = t["overdrive"] if mode == "overdrive" else t["normal"]
    quote = t["overdrive_quote"] if mode == "overdrive" else t["normal_quote"]

    cells = []
    for c, week in enumerate(weeks):
        ds = week.get("contributionDays", [])
        for r, day in enumerate(ds[:7]):
            x = gx + c * pitch
            y = gy + r * pitch
            level = LEVEL.get(day["contributionLevel"], 0)
            cells.append(
                f'<rect class="c{level}" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.3"><title>{esc(day["date"])} · {day["contributionCount"]} contributions</title></rect>'
            )

    labels = []
    for col, name in month_labels(weeks, t["months"]):
        labels.append(f'<text class="month" x="{gx + col*pitch}" y="{gy - 13}">{esc(name)}</text>')

    legend_x = gx + max(0, gw - 178)
    legend_y = gy + gh + 28
    legend_rects = []
    for i in range(5):
        legend_rects.append(f'<rect class="c{i}" x="{legend_x + 36 + i*18}" y="{legend_y-9}" width="12" height="12" rx="3"/>')

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    group_text = " / ".join(str(v) for v in groups)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1120 360" role="img" aria-labelledby="title desc">
<title id="title">{esc(t['title'])} — {esc(user)}</title>
<desc id="desc">Animated GitHub contribution graph with three contribution-driven heartbeat segments.</desc>
<style>
  :root {{ color-scheme: light dark; }}
  .bg {{ fill:#fffdfc; stroke:#e9e5e7; }}
  .panel {{ fill:#fff8fa; stroke:#eadde3; }}
  .text {{ fill:#17213e; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',sans-serif; }}
  .muted {{ fill:#7b8496; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',sans-serif; }}
  .title {{ font-size:24px; font-weight:800; letter-spacing:-.5px; }}
  .sub {{ font-size:12px; }}
  .month {{ fill:#7b8496; font:10px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
  .small {{ font-size:10px; }}
  .label {{ font-size:11px; font-weight:700; }}
  .value {{ font-size:19px; font-weight:800; }}
  .quote {{ font-size:12px; font-weight:650; }}
  .c0 {{ fill:#ebedf0; }} .c1 {{ fill:#9be9a8; }} .c2 {{ fill:#40c463; }} .c3 {{ fill:#30a14e; }} .c4 {{ fill:#216e39; }}
  .heart-glow {{ fill:none; stroke:#ffc3d5; stroke-width:9; opacity:.22; stroke-linecap:round; stroke-linejoin:round; }}
  .heart {{ fill:none; stroke:#ef6696; stroke-width:3.4; stroke-linecap:round; stroke-linejoin:round; filter:drop-shadow(0 0 5px rgba(239,102,150,.38)); }}
  .heart,.heart-glow {{ path-length:1; stroke-dasharray:1; stroke-dashoffset:1; animation:draw-heart 6s linear infinite; }}
  @keyframes draw-heart {{
    0%,4% {{ stroke-dashoffset:1; opacity:0; }}
    7% {{ opacity:1; }}
    47% {{ stroke-dashoffset:0; opacity:1; }}
    96% {{ stroke-dashoffset:0; opacity:1; }}
    100% {{ stroke-dashoffset:1; opacity:0; }}
  }}
  .pulse {{ animation:soft-pulse 1.5s ease-in-out infinite; transform-origin:center; transform-box:fill-box; }}
  @keyframes soft-pulse {{ 0%,100%{{opacity:.78}} 50%{{opacity:1}} }}
  @media (prefers-color-scheme: dark) {{
    .bg {{ fill:#0d1117; stroke:#30363d; }} .panel {{ fill:#161b22; stroke:#30363d; }}
    .text {{ fill:#f0f3f6; }} .muted,.month {{ fill:#8b949e; }}
    .c0 {{ fill:#161b22; }} .c1 {{ fill:#0e4429; }} .c2 {{ fill:#006d32; }} .c3 {{ fill:#26a641; }} .c4 {{ fill:#39d353; }}
  }}
  @media (prefers-reduced-motion) {{ .heart,.heart-glow,.pulse {{ animation:none !important; stroke-dashoffset:0 !important; opacity:1 !important; }} }}
</style>
<rect class="bg" x="1" y="1" width="1118" height="358" rx="24"/>
<text class="text title" x="38" y="42">{esc(t['title'])}</text>
<text class="muted sub" x="38" y="62">@{esc(user)} · {esc(t['subtitle'])}</text>
<text class="muted small" x="720" y="40" text-anchor="end">{esc(t['group'])}</text>

{''.join(labels)}
{''.join(cells)}
<path class="heart-glow" pathLength="1" d="{heartbeat}"/>
<path class="heart" pathLength="1" d="{heartbeat}"/>

<text class="muted small" x="{legend_x}" y="{legend_y}">{esc(t['less'])}</text>
{''.join(legend_rects)}
<text class="muted small" x="{legend_x + 132}" y="{legend_y}">{esc(t['more'])}</text>
<text class="muted small" x="38" y="{legend_y}">3 heartbeat volumes: {group_text}</text>

<rect class="panel" x="748" y="24" width="346" height="312" rx="22"/>
<defs><clipPath id="portraitClip"><rect x="770" y="48" width="136" height="136" rx="24"/></clipPath></defs>
<image href="{portrait_uri}" x="770" y="48" width="136" height="136" preserveAspectRatio="xMidYMid slice" clip-path="url(#portraitClip)"/>
<rect x="779" y="57" width="{100 if mode=='normal' else 126}" height="24" rx="12" fill="{'#e8f3ec' if mode=='normal' else '#ffe0ea'}" opacity=".95"/>
<text x="790" y="73" font-size="10" font-weight="800" fill="{'#27864b' if mode=='normal' else '#d93e76'}" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">{'● ' if mode=='normal' else '⚡ '}{esc(status)}</text>

<text class="text quote" x="928" y="65">“{esc(quote)}”</text>
<text class="muted small" x="928" y="95">{esc(t['affection'])}</text>
<text class="text label" x="1068" y="95" text-anchor="end">{affection}%</text>
<rect x="928" y="106" width="140" height="8" rx="4" fill="#f2d9e2"/>
<rect class="pulse" x="928" y="106" width="{1.4*affection:.1f}" height="8" rx="4" fill="#ef6f9e"/>

<rect class="bg" x="770" y="205" width="96" height="78" rx="15"/>
<rect class="bg" x="878" y="205" width="96" height="78" rx="15"/>
<rect class="bg" x="986" y="205" width="86" height="78" rx="15"/>
<text class="muted small" x="784" y="226">{esc(t['today'])}</text><text class="text value" x="784" y="254">{today}</text>
<text class="muted small" x="892" y="226">{esc(t['streak'])}</text><text class="text value" x="892" y="254">{streak}</text><text class="muted small" x="930" y="254">{esc(t['days'])}</text>
<text class="muted small" x="1000" y="226">{esc(t['total'])}</text><text class="text value" x="1000" y="254">{total:,}</text>

<text class="muted small" x="770" y="309">{esc(t['updated'])}: {generated}</text>
<text class="muted small" x="1072" y="309" text-anchor="end">♡ Anime Contribution Graph</text>
</svg>'''


def demo_weeks():
    now = datetime.now(timezone.utc).date()
    start = now - timedelta(days=364)
    weeks = []
    cursor = start
    for c in range(53):
        ds = []
        for r in range(7):
            d = cursor + timedelta(days=c * 7 + r)
            if d > now:
                break
            count = max(0, int((1 + __import__('math').sin(c * .37 + r)) * 2.2 + ((c * 13 + r * 7) % 5) - 2))
            level = "NONE" if count == 0 else ("FIRST_QUARTILE" if count < 2 else "SECOND_QUARTILE" if count < 4 else "THIRD_QUARTILE" if count < 6 else "FOURTH_QUARTILE")
            ds.append({"date": d.isoformat(), "contributionCount": count, "contributionLevel": level})
        if ds:
            weeks.append({"contributionDays": ds})
    return weeks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.getenv("GITHUB_REPOSITORY_OWNER"), help="GitHub username")
    ap.add_argument("--output", default="dist/anime-contribution.svg")
    ap.add_argument("--lang", choices=sorted(LANG), default="en")
    ap.add_argument("--normal", default="assets/character_normal.png")
    ap.add_argument("--overdrive", default="assets/character_overdrive.png")
    ap.add_argument("--demo", action="store_true", help="use offline demo data")
    args = ap.parse_args()

    if not args.user:
        ap.error("--user is required outside GitHub Actions")
    normal = Path(args.normal)
    overdrive = Path(args.overdrive)
    for p in (normal, overdrive):
        if not p.exists():
            raise SystemExit(f"missing asset: {p}")

    if args.demo:
        weeks = demo_weeks()
    else:
        tok = token()
        if not tok:
            raise SystemExit("no GitHub token found; set GH_TOKEN or GITHUB_TOKEN")
        weeks = fetch_weeks(args.user, tok)

    svg = render(args.user, weeks, args.lang, image_data_uri(normal), image_data_uri(overdrive))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"wrote {out} ({len(svg):,} bytes, {len(weeks)} weeks)")


if __name__ == "__main__":
    main()
