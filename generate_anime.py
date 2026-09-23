#!/usr/bin/env python3
"""Generate an animated anime-style GitHub contribution SVG.

Designed for direct embedding in a GitHub profile README. The SVG contains only
SVG/CSS animation (no JavaScript), reads real GitHub contribution data, draws
three long contribution-driven ECG segments from left to right, and shows an OC
status panel below the graph.
"""

from __future__ import annotations

import argparse
import base64
import html
import io
import json
import os
import random
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

STATE_META = {
    "idle": {
        "icon": "◌",
        "heart": "#9ca6b5",
        "glow": "#dce2ea",
        "badge_bg": "#eef1f5",
        "badge_fg": "#667084",
        "portrait": "normal",
    },
    "focus": {
        "icon": "◆",
        "heart": "#9c7aea",
        "glow": "#d8c8ff",
        "badge_bg": "#eee8ff",
        "badge_fg": "#7552c9",
        "portrait": "normal",
    },
    "happy": {
        "icon": "♥",
        "heart": "#ef78a2",
        "glow": "#ffc9da",
        "badge_bg": "#ffe7ef",
        "badge_fg": "#d65382",
        "portrait": "overdrive",
    },
    "overdrive": {
        "icon": "⚡",
        "heart": "#ff4f86",
        "glow": "#ffb8cf",
        "badge_bg": "#ffdbe7",
        "badge_fg": "#d92f6a",
        "portrait": "overdrive",
    },
}

LANG = {
    "en": {
        "title": "Anime Contribution Graph",
        "subtitle": "A year of code, drawn as a heartbeat.",
        "affection": "Affection",
        "today": "Today",
        "streak": "Streak",
        "total": "Total",
        "days": "days",
        "less": "Less",
        "more": "More",
        "updated": "Updated",
        "group": "4 months = 1 heartbeat · 3 beats per year",
        "combo": "COMBO",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "state": {
            "idle": "IDLE",
            "focus": "FOCUS",
            "happy": "HAPPY",
            "overdrive": "OVERDRIVE",
        },
        "quotes": {
            "idle": [
                "Quiet day. A small step still counts.",
                "The graph is calm today. No rush.",
                "A blank square is just room for the next idea.",
                "Rest mode is part of the coding loop too.",
            ],
            "focus": [
                "Steady progress. The rhythm feels good.",
                "One commit at a time. Keep the pace.",
                "Focused mode on. Nice and clean.",
                "Small commits are building something bigger.",
            ],
            "happy": [
                "Nice! The contribution graph is glowing.",
                "Good momentum today. Keep your own rhythm.",
                "That was a productive run. Looking good!",
                "The heartbeat is getting brighter today.",
            ],
            "overdrive": [
                "Today's coding energy is maxed out!",
                "Overdrive detected. That's a lot of commits!",
                "The graph is practically sparkling now.",
                "Big coding day. Remember to take a break too.",
            ],
        },
    },
    "zh": {
        "title": "二次元贡献图",
        "subtitle": "把一年的代码，画成三次心跳。",
        "affection": "好感度",
        "today": "今天",
        "streak": "连续",
        "total": "总贡献",
        "days": "天",
        "less": "少",
        "more": "多",
        "updated": "更新于",
        "group": "4 个月 = 1 次长心跳 · 全年 3 次",
        "combo": "连击",
        "months": ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
        "state": {
            "idle": "休息",
            "focus": "专注",
            "happy": "开心",
            "overdrive": "爆肝模式",
        },
        "quotes": {
            "idle": [
                "今天比较安静，慢一点也没关系。",
                "贡献图休息一下，下一次再继续。",
                "空着的格子，也是在给新点子留位置。",
                "休息也是开发流程的一部分。",
            ],
            "focus": [
                "今天推进得很稳，保持这个节奏。",
                "一小步一小步，已经在往前走了。",
                "专注模式开启，今天的状态不错。",
                "小小的提交，也在慢慢堆成作品。",
            ],
            "happy": [
                "不错诶，今天的贡献图亮起来了。",
                "今天很有手感，保持自己的节奏就好。",
                "这一轮写得很顺，贡献图很好看。",
                "今天的心跳比平时更亮一点。",
            ],
            "overdrive": [
                "今天的 coding energy 拉满啦！",
                "爆肝模式检测到，今天提交了好多。",
                "贡献图都快闪起来了，太能写了。",
                "高强度 coding 日，记得也休息一下。",
            ],
        },
    },
    "ja": {
        "title": "Anime Contribution Graph",
        "subtitle": "1年のコードを、3つの心拍として描く。",
        "affection": "好感度",
        "today": "今日",
        "streak": "連続",
        "total": "合計",
        "days": "日",
        "less": "少",
        "more": "多",
        "updated": "更新",
        "group": "4か月 = 1つの長い心拍 · 1年で3拍",
        "combo": "COMBO",
        "months": ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
        "state": {
            "idle": "休憩",
            "focus": "集中",
            "happy": "HAPPY",
            "overdrive": "オーバードライブ",
        },
        "quotes": {
            "idle": [
                "今日は静かめ。ゆっくりでも大丈夫。",
                "グラフも少し休憩中。また次へ進もう。",
                "空いているマスは次のアイデアのため。",
                "休むことも開発の一部だよ。",
            ],
            "focus": [
                "いいペース。少しずつ進んでるね。",
                "一つずつコミットしていこう。",
                "集中モード。今日のリズムはいい感じ。",
                "小さなコミットが作品を作っていく。",
            ],
            "happy": [
                "いい感じ！グラフが明るくなってきた。",
                "今日はかなり順調。自分のペースでね。",
                "いい開発タイムだったね。",
                "今日の心拍はいつもより明るい。",
            ],
            "overdrive": [
                "今日のコーディングエネルギー、MAXだよ！",
                "オーバードライブ！コミットがいっぱい。",
                "グラフがキラキラするくらい動いてる。",
                "今日は高出力。休憩も忘れずにね。",
            ],
        },
    },
}


def token() -> str:
    for key in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.getenv(key):
            return os.environ[key]
    try:
        return subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=False,
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
        data=json.dumps(
            {"query": query, "variables": {"login": user, "from": frm}}
        ).encode(),
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
    user_data = data.get("data", {}).get("user")
    if not user_data:
        raise RuntimeError(f"GitHub user not found: {user}")
    return user_data["contributionsCollection"]["contributionCalendar"]["weeks"]


def image_data_uri(path: Path) -> str:
    """Embed a compact portrait so the output stays GitHub-proxy friendly."""
    try:
        from PIL import Image

        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail((480, 480), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            image.save(
                buf,
                format="JPEG",
                quality=88,
                optimize=True,
                progressive=True,
            )
            raw = buf.getvalue()
        return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
    except Exception:
        raw = path.read_bytes()
        return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def flatten_days(weeks):
    days = []
    for week in weeks:
        for day in week.get("contributionDays", []):
            days.append(
                {
                    "date": day["date"],
                    "count": int(day["contributionCount"]),
                    "level": LEVEL.get(day["contributionLevel"], 0),
                }
            )
    return days


def current_streak(days) -> int:
    if not days:
        return 0
    ordered = sorted(days, key=lambda item: item["date"])
    index = len(ordered) - 1
    if ordered[index]["count"] == 0:
        index -= 1
    streak = 0
    while index >= 0 and ordered[index]["count"] > 0:
        streak += 1
        index -= 1
    return streak


def choose_state(today: int, last7: int, streak: int) -> str:
    """Four-state OC routing based on live contribution activity."""
    if today == 0 and last7 <= 3:
        return "idle"
    if today <= 2 and last7 < 15:
        return "focus"
    if today <= 7 and last7 < 35:
        return "happy"
    return "overdrive"


def stats(weeks):
    days = flatten_days(weeks)
    total = sum(day["count"] for day in days)
    today = days[-1]["count"] if days else 0
    last7 = sum(day["count"] for day in days[-7:])
    streak = current_streak(days)
    state = choose_state(today, last7, streak)
    affection = max(
        18,
        min(
            100,
            round(
                30
                + total * 0.40
                + min(streak, 30) * 0.8
                + min(last7, 35) * 0.45
            ),
        ),
    )
    return days, total, today, last7, streak, state, affection


def pick_quote(user: str, state: str, lang: str) -> str:
    """Choose a quote that changes with each hourly Action refresh."""
    now = datetime.now(timezone.utc)
    seed = f"{user}:{state}:{lang}:{now:%Y-%m-%d-%H}"
    rng = random.Random(seed)
    return rng.choice(LANG[lang]["quotes"][state])


def month_labels(weeks, labels):
    result = []
    seen = None
    for col, week in enumerate(weeks):
        days = week.get("contributionDays", [])
        if not days:
            continue
        month = int(days[0]["date"].split("-")[1])
        if month != seen:
            result.append((col, labels[month - 1]))
            seen = month
    if len(result) > 1 and result[1][0] <= 2:
        result = result[1:]
    return result


def heartbeat_path(weekly_totals, x0, y0, width, height):
    n = len(weekly_totals)
    if n == 0:
        return (
            f"M {x0} {y0 + height / 2} L {x0 + width} {y0 + height / 2}",
            [0, 0, 0],
        )

    cuts = [0, round(n / 3), round(2 * n / 3), n]
    groups = [
        sum(weekly_totals[cuts[index]:cuts[index + 1]])
        for index in range(3)
    ]
    group_max = max(max(groups), 1)
    baseline = y0 + height / 2
    segment_width = width / 3
    points = [(x0, baseline)]

    for index, value in enumerate(groups):
        start = x0 + index * segment_width
        relative = value / group_max
        absolute = min(1.0, value / 80.0)
        strength = 0.45 * relative + 0.55 * absolute

        amplitude = 18 + 43 * strength
        dip = 8 + 18 * strength
        tiny = 2.5 + 4 * strength

        shape = [
            (0.00, 0),
            (0.16, 0),
            (0.235, -tiny),
            (0.285, 0),
            (0.40, 0),
            (0.465, 5 + 3 * strength),
            (0.525, -amplitude),
            (0.585, dip),
            (0.655, -amplitude * 0.22),
            (0.72, 0),
            (0.86, 0),
            (1.00, 0),
        ]

        for shape_index, (ratio, offset_y) in enumerate(shape):
            if index and shape_index == 0:
                continue
            points.append(
                (
                    start + ratio * segment_width,
                    baseline + offset_y,
                )
            )

    path = " ".join(
        ("M" if index == 0 else "L") + f" {x:.1f} {y:.1f}"
        for index, (x, y) in enumerate(points)
    )
    return path, groups


def wrap_quote(text: str, lang: str, max_chars: int = 31) -> list[str]:
    if lang in ("zh", "ja"):
        if len(text) <= max_chars:
            return [text]
        return [text[:max_chars], text[max_chars:max_chars * 2]]

    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if current and len(candidate) > max_chars:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)

    if len(lines) <= 2:
        return lines
    return [lines[0], " ".join(lines[1:])]


def palette_css(theme: str) -> tuple[str, str]:
    light = """
  .bg { fill:#fffdfc; stroke:#e9e5e7; }
  .panel { fill:#fff8fa; stroke:#eadde3; }
  .text { fill:#17213e; }
  .muted,.month { fill:#7b8496; }
  .statbox { fill:#fffdfc; stroke:#e9e5e7; }
  .c0 { fill:#ebedf0; } .c1 { fill:#9be9a8; } .c2 { fill:#40c463; } .c3 { fill:#30a14e; } .c4 { fill:#216e39; }
  .bar-bg { fill:#f2d9e2; }
"""
    dark = """
  .bg { fill:#0d1117; stroke:#30363d; }
  .panel { fill:#161b22; stroke:#30363d; }
  .text { fill:#f0f3f6; }
  .muted,.month { fill:#8b949e; }
  .statbox { fill:#0d1117; stroke:#30363d; }
  .c0 { fill:#161b22; } .c1 { fill:#0e4429; } .c2 { fill:#006d32; } .c3 { fill:#26a641; } .c4 { fill:#39d353; }
  .bar-bg { fill:#3a2831; }
"""
    if theme == "dark":
        return dark, ""
    if theme == "light":
        return light, ""
    return light, f"@media (prefers-color-scheme: dark) {{{dark}}}"


def render(
    user: str,
    weeks,
    lang: str,
    normal_uri: str,
    overdrive_uri: str,
    theme: str = "auto",
) -> str:
    text = LANG[lang]
    days, total, today, last7, streak, state, affection = stats(weeks)
    state_meta = STATE_META[state]

    weekly_totals = [
        sum(
            int(day["contributionCount"])
            for day in week.get("contributionDays", [])
        )
        for week in weeks
    ]

    width, height = 1120, 480
    graph_x, graph_y = 38, 94
    cell, gap = 12, 6
    pitch = cell + gap
    graph_width = len(weeks) * pitch - gap
    graph_height = 7 * pitch - gap

    heartbeat, groups = heartbeat_path(
        weekly_totals,
        graph_x,
        graph_y - 10,
        graph_width,
        graph_height + 22,
    )

    portrait_uri = (
        overdrive_uri
        if state_meta["portrait"] == "overdrive"
        else normal_uri
    )
    status = text["state"][state]
    quote = pick_quote(user, state, lang)
    quote_lines = wrap_quote(quote, lang)
    quote_tspans = "".join(
        f'<tspan x="230" y="{300 + index * 19}">'
        f'{"“" if index == 0 else ""}{esc(line)}'
        f'{"”" if index == len(quote_lines) - 1 else ""}'
        f'</tspan>'
        for index, line in enumerate(quote_lines)
    )

    cells = []
    for col, week in enumerate(weeks):
        for row, day in enumerate(week.get("contributionDays", [])[:7]):
            x = graph_x + col * pitch
            y = graph_y + row * pitch
            level = LEVEL.get(day["contributionLevel"], 0)
            cells.append(
                f'<rect class="c{level}" x="{x}" y="{y}" '
                f'width="{cell}" height="{cell}" rx="2.5">'
                f'<title>{esc(day["date"])} · '
                f'{day["contributionCount"]} contributions</title></rect>'
            )

    month_parts = []
    for col, name in month_labels(weeks, text["months"]):
        month_parts.append(
            f'<text class="month" x="{graph_x + col * pitch}" '
            f'y="{graph_y - 13}">{esc(name)}</text>'
        )

    legend_x = graph_x + max(0, graph_width - 178)
    legend_y = graph_y + graph_height + 28
    legend_rects = "".join(
        f'<rect class="c{level}" x="{legend_x + 36 + level * 18}" '
        f'y="{legend_y - 9}" width="12" height="12" rx="3"/>'
        for level in range(5)
    )

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    group_text = " / ".join(str(value) for value in groups)
    combo = (
        f'<rect x="438" y="278" width="112" height="30" rx="15" '
        f'fill="{state_meta["badge_bg"]}"/>'
        f'<text x="494" y="298" text-anchor="middle" font-size="10" '
        f'font-weight="800" fill="{state_meta["badge_fg"]}" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif">'
        f'{esc(text["combo"])} × {streak}</text>'
        if streak >= 2
        else ""
    )

    badge_width = {
        "idle": 88,
        "focus": 96,
        "happy": 96,
        "overdrive": 126,
    }[state]

    theme_rules, auto_dark_rules = palette_css(theme)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{esc(text['title'])} — {esc(user)}</title>
<desc id="desc">Animated GitHub contribution graph with three contribution-driven heartbeat segments and four OC states.</desc>
<style>
  :root {{ color-scheme: light dark; }}
  text {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',sans-serif; }}
  {theme_rules}
  .title {{ font-size:24px; font-weight:800; letter-spacing:-.5px; }}
  .sub {{ font-size:12px; }}
  .month {{ font-size:10px; }}
  .small {{ font-size:10px; }}
  .label {{ font-size:11px; font-weight:700; }}
  .value {{ font-size:19px; font-weight:800; }}
  .quote {{ font-size:12px; font-weight:650; }}
  .heart-glow {{ fill:none; stroke:{state_meta['glow']}; stroke-width:9; opacity:.24; stroke-linecap:round; stroke-linejoin:round; }}
  .heart {{ fill:none; stroke:{state_meta['heart']}; stroke-width:3.4; stroke-linecap:round; stroke-linejoin:round; filter:drop-shadow(0 0 5px {state_meta['glow']}); }}
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
  {auto_dark_rules}
  @media (prefers-reduced-motion) {{
    .heart,.heart-glow,.pulse {{
      animation:none !important;
      stroke-dashoffset:0 !important;
      opacity:1 !important;
    }}
  }}
</style>

<rect class="bg" x="1" y="1" width="{width - 2}" height="{height - 2}" rx="24"/>

<text class="text title" x="38" y="42">{esc(text['title'])}</text>
<text class="muted sub" x="38" y="62">@{esc(user)} · {esc(text['subtitle'])}</text>
<text class="muted small" x="{width - 38}" y="40" text-anchor="end">{esc(text['group'])}</text>

{''.join(month_parts)}
{''.join(cells)}
<path class="heart-glow" pathLength="1" d="{heartbeat}"/>
<path class="heart" pathLength="1" d="{heartbeat}"/>

<text class="muted small" x="{legend_x}" y="{legend_y}">{esc(text['less'])}</text>
{legend_rects}
<text class="muted small" x="{legend_x + 132}" y="{legend_y}">{esc(text['more'])}</text>
<text class="muted small" x="38" y="{legend_y}">3 heartbeat volumes: {group_text}</text>

<rect class="panel" x="38" y="246" width="1044" height="204" rx="22"/>

<defs>
  <clipPath id="portraitClip">
    <rect x="60" y="268" width="146" height="146" rx="24"/>
  </clipPath>
</defs>

<image href="{portrait_uri}" x="60" y="268" width="146" height="146"
       preserveAspectRatio="xMidYMid slice" clip-path="url(#portraitClip)"/>

<rect x="70" y="280" width="{badge_width}" height="24" rx="12"
      fill="{state_meta['badge_bg']}" opacity=".96"/>
<text x="82" y="296" font-size="10" font-weight="800"
      fill="{state_meta['badge_fg']}"
      font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  {state_meta['icon']} {esc(status)}
</text>

<text class="text quote">{quote_tspans}</text>

<text class="muted small" x="230" y="354">{esc(text['affection'])}</text>
<text class="text label" x="420" y="354" text-anchor="end">{affection}%</text>
<rect class="bar-bg" x="230" y="366" width="190" height="8" rx="4"/>
<rect class="pulse" x="230" y="366" width="{1.9 * affection:.1f}" height="8" rx="4"
      fill="{state_meta['heart']}"/>

{combo}

<rect class="statbox" x="670" y="278" width="118" height="92" rx="15"/>
<rect class="statbox" x="802" y="278" width="118" height="92" rx="15"/>
<rect class="statbox" x="934" y="278" width="118" height="92" rx="15"/>

<text class="muted small" x="686" y="302">{esc(text['today'])}</text>
<text class="text value" x="686" y="337">{today}</text>

<text class="muted small" x="818" y="302">{esc(text['streak'])}</text>
<text class="text value" x="818" y="337">{streak}</text>
<text class="muted small" x="858" y="337">{esc(text['days'])}</text>

<text class="muted small" x="950" y="302">{esc(text['total'])}</text>
<text class="text value" x="950" y="337">{total:,}</text>

<text class="muted small" x="60" y="430">{esc(text['updated'])}: {generated}</text>
<text class="muted small" x="1060" y="430" text-anchor="end">
  ♡ Anime Contribution Graph · {esc(text['state'][state])}
</text>
</svg>'''


def demo_weeks():
    now = datetime.now(timezone.utc).date()
    start = now - timedelta(days=364)
    weeks = []

    for col in range(53):
        days = []
        for row in range(7):
            day = start + timedelta(days=col * 7 + row)
            if day > now:
                break

            count = max(
                0,
                int(
                    (1 + __import__("math").sin(col * 0.37 + row)) * 2.2
                    + ((col * 13 + row * 7) % 5)
                    - 2
                ),
            )

            level = (
                "NONE"
                if count == 0
                else "FIRST_QUARTILE"
                if count < 2
                else "SECOND_QUARTILE"
                if count < 4
                else "THIRD_QUARTILE"
                if count < 6
                else "FOURTH_QUARTILE"
            )

            days.append(
                {
                    "date": day.isoformat(),
                    "contributionCount": count,
                    "contributionLevel": level,
                }
            )

        if days:
            weeks.append({"contributionDays": days})

    return weeks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--user",
        default=os.getenv("GITHUB_REPOSITORY_OWNER"),
        help="GitHub username",
    )
    parser.add_argument(
        "--output",
        default="dist/anime-contribution.svg",
    )
    parser.add_argument(
        "--lang",
        choices=sorted(LANG),
        default="en",
    )
    parser.add_argument(
        "--theme",
        choices=("auto", "light", "dark"),
        default="auto",
    )
    parser.add_argument(
        "--normal",
        default="assets/character_normal.png",
    )
    parser.add_argument(
        "--overdrive",
        default="assets/character_overdrive.png",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="use offline demo data",
    )
    args = parser.parse_args()

    if not args.user:
        parser.error("--user is required outside GitHub Actions")

    normal = Path(args.normal)
    overdrive = Path(args.overdrive)

    for path in (normal, overdrive):
        if not path.exists():
            raise SystemExit(f"missing asset: {path}")

    if args.demo:
        weeks = demo_weeks()
    else:
        tok = token()
        if not tok:
            raise SystemExit(
                "no GitHub token found; set GH_TOKEN or GITHUB_TOKEN"
            )
        weeks = fetch_weeks(args.user, tok)

    svg = render(
        args.user,
        weeks,
        args.lang,
        image_data_uri(normal),
        image_data_uri(overdrive),
        args.theme,
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")
    print(
        f"wrote {output} "
        f"({len(svg):,} bytes, {len(weeks)} weeks, {args.theme})"
    )


if __name__ == "__main__":
    main()
