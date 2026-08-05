#!/usr/bin/env python3
"""
Regenerate every SVG in assets/ from data/graph.json.

data/graph.json comes from `bash scripts/refresh.sh`, which scans every local
agent store and merges the results. Every number rendered below is read from
that file — nothing here is hand-written.

Design rules for GitHub READMEs — each one learned the hard way:
  * KEEP EVERY ASSET STATIC. Animation elements do not survive into the README
    render, so anything that starts at opacity="0" and fades in via <animate>
    is invisible forever. That silently ate the headline number, the stat chips
    and every coloured skyline tower on the first deploy.
  * Images are proxied and CACHED BY URL. Same path + new bytes = the old
    picture served indefinitely. inject_images() appends a content hash to each
    <img src> so a rebuild always lands on a URL the proxy has never seen.
  * <a> and hover tooltips inside the SVG do nothing. Keep anything clickable
    in markdown instead.
  * prefers-color-scheme is unreliable through the proxy, so every card paints
    its own dark panel and reads the same in both GitHub themes.
  * No external fonts, no external anything — the proxy blocks it.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "graph.json"
OUT = ROOT / "assets"

# GitHub's profile README column is ~690px. Anything wider gets scaled down and
# the type shrinks with it — 1280 rendered at 0.54x and was unreadable. Draw at
# the real display width so 13px type stays 13px.
W = 700

# ---------------------------------------------------------------- palette
INK = "#04050a"
PANEL = "#080b13"
LINE = "#161d2e"
TEXT = "#e9edf7"
MUTED = "#78839c"
DIM = "#414c62"

CYAN = "#22d3ee"
VIOLET = "#a78bfa"
PINK = "#f472b6"
LIME = "#a3e635"
AMBER = "#fbbf24"

HEAT = ["#132447", "#155e75", "#0891b2", "#22d3ee", "#7dd3fc", "#f0abfc"]

CLIENT_COLOR = {
    "codex": "#10b981",
    "claude": "#d97757",
    "hermes": "#a78bfa",
    "opencode": "#f472b6",
    "gjc": "#fbbf24",
    "kilo": "#38bdf8",
    "antigravity-cli": "#94a3b8",
}
CLIENT_LABEL = {
    "codex": "Codex CLI",
    "claude": "Claude Code",
    "hermes": "Hermes",
    "opencode": "OpenCode",
    "gjc": "Gajae-Code",
    "kilo": "Kilo CLI",
    "antigravity-cli": "Antigravity",
}

# Korean needs a system font that actually exists on the viewer's machine — the
# image proxy blocks webfonts. Mono is kept for digits only; Hangul in a mono
# stack falls back unpredictably and looks broken.
SANS = ("'Pretendard','Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',"
        "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif")
MONO = "ui-monospace,'SF Mono','JetBrains Mono',Menlo,Consolas,monospace"


# ---------------------------------------------------------------- helpers
def shade(hex_color: str, factor: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    if factor <= 1:
        r, g, b = (int(c * factor) for c in (r, g, b))
    else:
        t = factor - 1
        r, g, b = (int(c + (255 - c) * t) for c in (r, g, b))
    return "#%02x%02x%02x" % tuple(max(0, min(255, v)) for v in (r, g, b))


def human(n: float) -> str:
    """Korean reading units — 조/억/만 — not B/M/K."""
    for unit, div in (("조", 1e12), ("억", 1e8), ("만", 1e4)):
        if n >= div:
            v = n / div
            # 2912.7만 reads worse than 2913만; keep a decimal only when small
            s = f"{v:,.0f}" if v >= 100 else f"{v:.1f}".rstrip("0").rstrip(".")
            return s + unit
    return f"{n:,.0f}"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write(name: str, body: str) -> None:
    (OUT / name).write_text(body, encoding="utf-8")
    print(f"  assets/{name:<16} {len(body):>7,} bytes")


def grid_defs(uid: str) -> str:
    return (
        f'<pattern id="grid{uid}" width="32" height="32" patternUnits="userSpaceOnUse">'
        f'<path d="M32 0H0V32" fill="none" stroke="{LINE}" stroke-width="0.6" opacity="0.55"/>'
        f"</pattern>"
    )


# ---------------------------------------------------------------- overrides
def apply_overrides(g):
    """Anchor a client's lifetime total to an externally reported figure.

    Local logs get pruned, so a local scan undercounts. The daily *shape* stays
    exactly as measured; one constant scales it to meet the provider's number.
    """
    path = ROOT / "data" / "overrides.json"
    if not path.exists():
        return {}
    ov = json.loads(path.read_text(encoding="utf-8"))
    factors = {}

    for client, cfg in ov.items():
        if client.startswith("_") or not isinstance(cfg, dict):
            continue
        target = cfg.get("reportedTotalTokens")
        if not target:
            continue
        local = sum(
            sum(e["tokens"].values())
            for d in g["contributions"]
            for e in d["clients"]
            if e["client"] == client
        )
        if local <= 0:
            continue
        f = target / local
        factors[client] = {"factor": f, "measured": local, "target": target}
        for d in g["contributions"]:
            delta = 0
            for e in d["clients"]:
                if e["client"] != client:
                    continue
                for k in e["tokens"]:
                    scaled = int(round(e["tokens"][k] * f))
                    delta += scaled - e["tokens"][k]
                    e["tokens"][k] = scaled
            d["totals"]["tokens"] += delta
        g["summary"]["totalTokens"] = sum(d["totals"]["tokens"] for d in g["contributions"])
        print(f"  anchor {client}: {local:,} -> {target:,}  (x{f:.5f}, {local/target*100:.2f}% measured)")

    return factors


# ---------------------------------------------------------------- load
def load():
    g = json.loads(DATA.read_text(encoding="utf-8"))
    factors = apply_overrides(g)
    days = g["contributions"]

    by_client, by_model = defaultdict(int), defaultdict(int)
    for d in days:
        for e in d["clients"]:
            t = sum(e["tokens"].values())
            by_client[e["client"]] += t
            by_model[e["modelId"]] += t

    by_month = defaultdict(lambda: [0, 0.0, 0])
    for d in days:
        k = d["date"][:7]
        by_month[k][0] += d["totals"]["tokens"]
        by_month[k][1] += d["totals"]["cost"]
        by_month[k][2] += d["totals"]["messages"]

    return {
        "raw": g,
        "factors": factors,
        "days": days,
        "summary": g["summary"],
        "time": g.get("timeMetrics", {}),
        "range": g["meta"]["dateRange"],
        "by_client": dict(by_client),
        "by_model": dict(by_model),
        "by_month": dict(by_month),
        "messages": sum(d["totals"]["messages"] for d in days),
    }


# ---------------------------------------------------------------- 1. hero
def build_hero(D):
    H = 300
    s, tm = D["summary"], D["time"]
    total = s["totalTokens"]
    digits = f"{total:,}"

    days = D["days"]
    mx = max(d["totals"]["tokens"] for d in days) or 1
    bw = W / len(days)
    bars = []
    for i, d in enumerate(days):
        h = 6 + (d["totals"]["tokens"] / mx) ** 0.5 * 92
        bars.append(
            f'<rect x="{i * bw:.2f}" y="{H - h:.2f}" width="{bw - 0.9:.2f}" '
            f'height="{h:.2f}" rx="1" fill="url(#sky)"/>'
        )

    chips = [
        (f'{s["activeDays"]}/{s["totalDays"]}', "활동일", LIME),
        (f'{len(s["clients"])}', "런타임", CYAN),
        (f'{len(s["models"])}', "모델", VIOLET),
        (f'{tm.get("sessionCount", 0):,}', "세션", PINK),
        (f'{tm.get("totalActiveTimeMs", 0) / 3.6e6:,.0f}시간', "가동", AMBER),
    ]
    cw, cx = 128.0, 30.0
    chip_svg = []
    for i, (big, lab, col) in enumerate(chips):
        x = cx + i * cw
        chip_svg.append(
            f'<g transform="translate({x:.0f},232)">'
            f'<rect x="0" y="0" width="2.5" height="32" fill="{col}"/>'
            f'<text x="11" y="15" font-family="{MONO}" font-size="17" font-weight="700" fill="{TEXT}">{big}</text>'
            f'<text x="11" y="29" font-family="{SANS}" font-size="11.5" fill="{MUTED}">{lab}</text>'
            f"</g>"
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="총 소비한 AI 토큰 {digits}">
<defs>
  {grid_defs("h")}
  <linearGradient id="void" x1="0" y1="0" x2="0.85" y2="1">
    <stop offset="0%" stop-color="#0a1024"/><stop offset="45%" stop-color="#0b0a1e"/><stop offset="100%" stop-color="#040508"/>
  </linearGradient>
  <linearGradient id="sky" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0%" stop-color="{CYAN}" stop-opacity="0.05"/>
    <stop offset="55%" stop-color="{CYAN}" stop-opacity="0.30"/>
    <stop offset="100%" stop-color="{VIOLET}" stop-opacity="0.85"/>
  </linearGradient>
  <linearGradient id="num" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#ffffff"/><stop offset="30%" stop-color="{CYAN}"/>
    <stop offset="66%" stop-color="{VIOLET}"/><stop offset="100%" stop-color="{PINK}"/>
  </linearGradient>
  <linearGradient id="scrim" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{INK}" stop-opacity="0"/>
    <stop offset="26%" stop-color="{INK}" stop-opacity="0.84"/>
    <stop offset="100%" stop-color="{INK}" stop-opacity="0.93"/>
  </linearGradient>
  <radialGradient id="bloom" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0%" stop-color="{VIOLET}" stop-opacity="0.30"/><stop offset="100%" stop-color="{VIOLET}" stop-opacity="0"/>
  </radialGradient>
</defs>

<rect width="{W}" height="{H}" rx="14" fill="url(#void)"/>
<rect width="{W}" height="{H}" rx="14" fill="url(#grid_h)" opacity="0.5"/>
<ellipse cx="500" cy="105" rx="290" ry="160" fill="url(#bloom)"/>
<g>{"".join(bars)}</g>

<text x="30" y="42" font-family="{MONO}" font-size="12" fill="{MUTED}" letter-spacing="2">kiminho · @inhodev</text>
<text x="{W - 30}" y="42" text-anchor="end" font-family="{MONO}" font-size="12" fill="{DIM}">{D["range"]["start"]} → {D["range"]["end"]}</text>

<text x="30" y="86" font-family="{SANS}" font-size="14" font-weight="700" fill="{CYAN}" letter-spacing="1.5">총 소비한 AI 토큰</text>
<text x="30" y="146" font-family="{MONO}" font-size="46" font-weight="700" fill="url(#num)" letter-spacing="-1">{digits}</text>
<text x="30" y="176" font-family="{SANS}" font-size="13" fill="{MUTED}">{human(total)}개 · 세션 로그를 전부 훑어서 센 값이다. 추정치가 아니다</text>

<rect x="0" y="208" width="{W}" height="92" fill="url(#scrim)"/>
<rect x="30" y="212" width="{W - 60}" height="1" fill="{LINE}"/>
{"".join(chip_svg)}
</svg>"""
    write("hero.svg", svg)


# ---------------------------------------------------------------- 3. skyline
def build_skyline(D):
    days = D["days"]
    first = date.fromisoformat(days[0]["date"])
    last = date.fromisoformat(days[-1]["date"])
    by_date = {d["date"]: d for d in days}

    origin = date.fromordinal(first.toordinal() - first.weekday())
    cols = (last.toordinal() - origin.toordinal()) // 7 + 1
    rows = 7
    mx = max(d["totals"]["tokens"] for d in days)

    TW, TH = 46.0, 23.0
    HW, HH = TW / 2, TH / 2
    MAXH = 230.0
    PAD, HEAD, FOOT = 26, 82, 58

    cells = []
    for col in range(cols):
        for row in range(rows):
            d = origin.fromordinal(origin.toordinal() + col * 7 + row)
            rec = by_date.get(d.isoformat())
            if not rec and not (first <= d <= last):
                continue
            cells.append((col + row, col, row, d, rec["totals"]["tokens"] if rec else 0, rec))
    cells.sort(key=lambda c: (c[0], c[2]))

    bbox = [1e9, 1e9, -1e9, -1e9]

    def track(x0, y0, x1, y1):
        bbox[0], bbox[1] = min(bbox[0], x0), min(bbox[1], y0)
        bbox[2], bbox[3] = max(bbox[2], x1), max(bbox[3], y1)

    boxes = []
    for n, (_, col, row, d, tok, rec) in enumerate(cells):
        sx, sy = (col - row) * HW, (col + row) * HH
        track(sx - HW, sy, sx + HW, sy + TH)

        if tok <= 0:
            boxes.append(
                f'<path d="M{sx:.1f},{sy:.1f} l{HW:.1f},{HH:.1f} l{-HW:.1f},{HH:.1f} l{-HW:.1f},{-HH:.1f} Z" '
                f'fill="#0b1120" stroke="#131b2b" stroke-width="0.5"/>'
            )
            continue

        ratio = (tok / mx) ** 0.42
        h = 3.0 + ratio * MAXH
        base = HEAT[min(len(HEAT) - 1, int(ratio * (len(HEAT) - 0.001)))]
        top_c, left_c, right_c = shade(base, 1.20), shade(base, 0.44), shade(base, 0.70)
        ty = sy - h
        track(sx - HW, ty, sx + HW, sy + TH)

        boxes.append(
            f"<g>"
            f'<path d="M{sx - HW:.1f},{ty + HH:.1f} l{HW:.1f},{HH:.1f} l0,{h:.1f} l{-HW:.1f},{-HH:.1f} Z" fill="{left_c}"/>'
            f'<path d="M{sx + HW:.1f},{ty + HH:.1f} l{-HW:.1f},{HH:.1f} l0,{h:.1f} l{HW:.1f},{-HH:.1f} Z" fill="{right_c}"/>'
            f'<path d="M{sx:.1f},{ty:.1f} l{HW:.1f},{HH:.1f} l{-HW:.1f},{HH:.1f} l{-HW:.1f},{-HH:.1f} Z" '
            f'fill="{top_c}" stroke="{shade(base, 1.5)}" stroke-width="0.6"/>'
            f"</g>"
        )

    month_pts, seen = [], set()
    for _, col, row, d, tok, _ in cells:
        key = d.strftime("%Y-%m")
        if key in seen or not (first <= d <= last) or d.day > 7:
            continue
        seen.add(key)
        sx = (col - rows + 1) * HW
        sy = (col + rows - 1) * HH
        month_pts.append((sx + 6, sy + 30, int(d.strftime("%m"))))

    # The calendar grid is as wide as the date range makes it. If that exceeds
    # the card, scale the whole plot down rather than letting towers run off the
    # edge — a clipped skyline reads as a bug.
    gw, gh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    k = min(1.0, (W - PAD * 2) / gw)
    H = int(gh * k + HEAD + FOOT)
    dx = (W - gw * k) / 2 - bbox[0] * k
    dy = HEAD - bbox[1] * k

    # Labels sit outside the scaled group, so shrinking the plot to fit never
    # shrinks the type with it.
    months = []
    for sx, sy, mm in month_pts:
        tx, ty2 = sx * k + dx, sy * k + dy
        months.append(
            f'<text x="{tx:.1f}" y="{ty2:.1f}" font-family="{SANS}" font-size="11.5" fill="{DIM}" '
            f'transform="rotate(26.57 {tx:.1f} {ty2:.1f})">{mm}월</text>'
        )

    legend = []
    lx0 = W - 92 - len(HEAT) * 20
    for i, c in enumerate(HEAT):
        x = lx0 + i * 20
        legend.append(f'<path d="M{x},{H - 29} l8,4 l-8,4 l-8,-4 Z" fill="{shade(c, 1.2)}"/>')

    s, tm = D["summary"], D["time"]
    peak = max(days, key=lambda d: d["totals"]["tokens"])

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="일자별 AI 토큰 사용량 아이소메트릭 스카이라인">
<defs>
  {grid_defs("s")}
  <linearGradient id="deep" x1="0" y1="0" x2="0.7" y2="1">
    <stop offset="0%" stop-color="#080d1a"/><stop offset="100%" stop-color="#040509"/>
  </linearGradient>
  <radialGradient id="halo" cx="0.5" cy="0.5" r="0.6">
    <stop offset="0%" stop-color="{CYAN}" stop-opacity="0.14"/><stop offset="100%" stop-color="{CYAN}" stop-opacity="0"/>
  </radialGradient>
</defs>

<rect width="{W}" height="{H}" rx="14" fill="url(#deep)" stroke="{LINE}"/>
<rect width="{W}" height="{H}" rx="14" fill="url(#grid_s)" opacity="0.4"/>
<rect width="{W}" height="{H}" rx="14" fill="url(#halo)"/>

<text x="28" y="40" font-family="{SANS}" font-size="17" font-weight="800" fill="{TEXT}">토큰 스카이라인</text>
<text x="28" y="60" font-family="{SANS}" font-size="12.5" fill="{MUTED}">탑 하나가 하루다 · 높이는 로그 스케일</text>
<text x="{W - 28}" y="40" text-anchor="end" font-family="{SANS}" font-size="19" font-weight="800" fill="{CYAN}">{human(s["totalTokens"])}</text>
<text x="{W - 28}" y="60" text-anchor="end" font-family="{SANS}" font-size="12" fill="{DIM}">{s["activeDays"]}/{s["totalDays"]}일 활동 · {tm.get("sessionCount", 0):,}세션</text>

<g transform="translate({dx:.2f},{dy:.2f}) scale({k:.4f})">{"".join(boxes)}</g>
{"".join(months)}

<text x="28" y="{H - 26}" font-family="{SANS}" font-size="12.5" fill="{MUTED}">가장 많이 쓴 날 {peak["date"]} · 하루에 {human(peak["totals"]["tokens"])}</text>
<text x="{lx0 - 20}" y="{H - 25}" text-anchor="end" font-family="{SANS}" font-size="11.5" fill="{DIM}">한산</text>
{"".join(legend)}
<text x="{W - 28}" y="{H - 25}" text-anchor="end" font-family="{SANS}" font-size="11.5" fill="{DIM}">폭주</text>
</svg>"""
    write("skyline.svg", svg)


# ---------------------------------------------------------------- 4. HUD
def build_hud(D):
    """Runtime split on top, monthly burn underneath.

    Two columns inside 700px left each chart ~330px, which is too narrow for
    eight month labels and a legible token figure. Stacked full-width reads far
    better at profile-column size.
    """
    order = sorted(D["by_client"].items(), key=lambda kv: -kv[1])
    total = sum(v for _, v in order)
    months = sorted(D["by_month"].items())

    pad = 28.0
    cw = W - pad * 2
    row_h = 34
    top_h = 74 + len(order) * row_h + 16
    m_top = top_h + 76
    m_ph = 132
    H = int(m_top + m_ph + 62)

    out = [
        f'<text x="{pad}" y="36" font-family="{SANS}" font-size="16" font-weight="800" fill="{TEXT}">토큰이 어디로 갔나</text>',
        f'<text x="{W - pad}" y="36" text-anchor="end" font-family="{SANS}" font-size="12" fill="{DIM}">런타임 {len(order)}개 · 모델 {len(D["by_model"])}종</text>',
    ]

    sx = pad
    for k, v in order:
        seg = cw * v / total
        out.append(
            f'<rect x="{sx:.2f}" y="52" width="{max(seg - 1.5, 1.2):.2f}" height="9" rx="3" fill="{CLIENT_COLOR.get(k, MUTED)}"/>'
        )
        sx += seg

    mxc = order[0][1]
    bar_x = pad + 118
    bar_w = cw - 118 - 118
    for i, (k, v) in enumerate(order):
        y = 86 + i * row_h
        color = CLIENT_COLOR.get(k, MUTED)
        w = max(3.0, bar_w * v / mxc)
        out.append(
            f'<g><circle cx="{pad + 5}" cy="{y + 8}" r="4" fill="{color}"/>'
            f'<text x="{pad + 17}" y="{y + 12}" font-family="{SANS}" font-size="13" fill="{TEXT}">{esc(CLIENT_LABEL.get(k, k))}</text>'
            f'<rect x="{bar_x}" y="{y + 3}" width="{bar_w}" height="11" rx="5.5" fill="#0e1524"/>'
            f'<rect x="{bar_x}" y="{y + 3}" width="{w:.1f}" height="11" rx="5.5" fill="{color}"/>'
            f'<text x="{W - pad}" y="{y + 12}" text-anchor="end" font-family="{MONO}" font-size="12.5" fill="{MUTED}">'
            f'{human(v)}  {v / total * 100:.1f}%</text></g>'
        )

    out.append(f'<line x1="{pad}" y1="{top_h + 14}" x2="{W - pad}" y2="{top_h + 14}" stroke="{LINE}"/>')
    out.append(
        f'<text x="{pad}" y="{top_h + 44}" font-family="{SANS}" font-size="16" font-weight="800" fill="{TEXT}">월별 소비량</text>'
    )
    out.append(
        f'<text x="{pad}" y="{top_h + 62}" font-family="{SANS}" font-size="11.5" fill="{DIM}">막대는 토큰, 아래 숫자는 추정 비용</text>'
    )

    mxm = max(v[0] for _, v in months)
    slot = cw / len(months)
    bw = min(46.0, slot * 0.58)
    for i, (m, v) in enumerate(months):
        cx = pad + slot * (i + 0.5)
        h = m_ph * (v[0] / mxm)
        y = m_top + m_ph - h
        out.append(
            f'<g><rect x="{cx - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" '
            f'height="{max(h, 2):.1f}" rx="4" fill="url(#mg)"/>'
            f'<text x="{cx:.1f}" y="{y - 7:.1f}" text-anchor="middle" font-family="{MONO}" font-size="11" fill="{CYAN}">{human(v[0])}</text>'
            f'<text x="{cx:.1f}" y="{m_top + m_ph + 19:.1f}" text-anchor="middle" font-family="{SANS}" font-size="12" fill="{MUTED}">{int(m[5:])}월</text>'
            f'<text x="{cx:.1f}" y="{m_top + m_ph + 35:.1f}" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{DIM}">${v[1]:,.0f}</text>'
            f"</g>"
        )
    out.append(f'<line x1="{pad}" y1="{m_top + m_ph:.1f}" x2="{W - pad}" y2="{m_top + m_ph:.1f}" stroke="{LINE}"/>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="런타임별 토큰 분포와 월별 소비량">
<defs>
  <linearGradient id="mg" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0%" stop-color="{VIOLET}" stop-opacity="0.30"/><stop offset="100%" stop-color="{CYAN}"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{H}" rx="14" fill="{PANEL}" stroke="{LINE}"/>
{"".join(out)}
</svg>"""
    write("hud.svg", svg)


# ---------------------------------------------------------------- README
START, END = "<!-- STATS:START -->", "<!-- STATS:END -->"
IMG_START, IMG_END = "<!-- IMAGES:START -->", "<!-- IMAGES:END -->"

# GitHub proxies README images through camo, which caches by URL. Same path +
# new content = the old picture served indefinitely. Appending a content hash
# gives every rebuild a fresh URL.
CARDS = [
    ("hero.svg", "총 소비한 AI 토큰, 추정치가 아니라 직접 센 값"),
    ("skyline.svg", "토큰 스카이라인, 탑 하나가 하루"),
    ("hud.svg", "런타임별 분포와 월별 소비량"),
]


def inject_images():
    path = ROOT / "README.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if IMG_START not in text or IMG_END not in text:
        print("  README image markers missing — skipped")
        return

    tags = []
    for name, alt in CARDS:
        f = OUT / name
        if not f.exists():
            continue
        h = hashlib.sha1(f.read_bytes()).hexdigest()[:10]
        tags.append(f'<img src="./assets/{name}?v={h}" alt="{alt}" width="100%">')

    block = f"{IMG_START}\n\n" + "\n\n".join(tags) + f"\n\n{IMG_END}"
    head, _, rest = text.partition(IMG_START)
    _, _, tail = rest.partition(IMG_END)
    path.write_text(head + block + tail, encoding="utf-8")
    print(f"  README image tags rehashed ({len(tags)} cards)")


def inject_readme(D, stats):
    path = ROOT / "README.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print("  README markers missing — skipped")
        return

    peak = max(D["days"], key=lambda d: d["totals"]["tokens"])
    r, hours = stats["range"], stats["activeHours"]
    cf = D["factors"].get("codex")

    rows = [
        ("기간", f'`{r["start"]} → {r["end"]}` · {stats["totalDays"]}일 중 **{stats["activeDays"]}일 활동**'),
        ("총 토큰", f'**{stats["totalTokens"]:,}** ({human(stats["totalTokens"])})'),
        ("메시지", f'{stats["messages"]:,}'),
        ("세션", f'{stats["sessions"]:,}'),
        ("에이전트 가동시간", f'{hours:,.0f}시간 · 달력으로는 {stats["totalDays"]}일인데 실제 연산은 **약 {hours / 24:.0f}일치**'),
        ("최장 연속 가동", f'{stats["longestContinuousHours"]:,.1f}시간'),
        ("최대 동시 세션", f'{stats["maxConcurrentSessions"]}개'),
        ("가장 많이 쓴 날", f'`{peak["date"]}` · {human(peak["totals"]["tokens"])}'),
        ("모델 / 런타임", f'{stats["models"]}종 / {len(stats["clients"])}개'),
    ]
    if cf:
        rows.append(
            ("Codex 실측 커버리지",
             f'**{cf["measured"] / cf["target"] * 100:.2f}%** · 공식 집계 {cf["target"]:,} 중 '
             f'{cf["measured"]:,}을 로컬 로그에서 날짜별로 복원했다')
        )
    table = "| | |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in rows)

    block = (
        f"{START}\n\n{table}\n\n"
        f"<sub>이 표는 <code>scripts/build_assets.py</code>가 만든다. 직접 고쳐도 다음 빌드에 덮어쓴다.</sub>\n\n"
        f"{END}"
    )
    head, _, rest = text.partition(START)
    _, _, tail = rest.partition(END)
    path.write_text(head + block + tail, encoding="utf-8")
    print("  README.md stats block updated")


# ---------------------------------------------------------------- main
def main():
    print(f"reading {DATA.relative_to(ROOT)}")
    D = load()
    OUT.mkdir(exist_ok=True)
    build_hero(D)
    build_skyline(D)
    build_hud(D)

    s, tm = D["summary"], D["time"]
    stats = {
        "range": D["range"],
        "totalTokens": s["totalTokens"],
        "totalCostUsd": round(s["totalCost"], 2),
        "activeDays": s["activeDays"],
        "totalDays": s["totalDays"],
        "sessions": tm.get("sessionCount"),
        "messages": D["messages"],
        "activeHours": round(tm.get("totalActiveTimeMs", 0) / 3.6e6, 1),
        "longestContinuousHours": round(tm.get("longestContinuousMs", 0) / 3.6e6, 1),
        "maxConcurrentSessions": tm.get("maxConcurrentSessions"),
        "models": len(s["models"]),
        "clients": s["clients"],
        "byClient": D["by_client"],
        "codexAnchor": D["factors"].get("codex"),
    }
    (ROOT / "data" / "stats.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("  data/stats.json")
    inject_readme(D, stats)
    inject_images()
    print(f"\n  {human(s['totalTokens'])} tokens · {s['activeDays']} active days · {len(s['models'])} models")


if __name__ == "__main__":
    main()
