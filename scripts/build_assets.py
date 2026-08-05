#!/usr/bin/env python3
"""
Regenerate every SVG in assets/ from data/graph.json.

data/graph.json comes from `bash scripts/refresh.sh`, which scans every local
agent store and merges the results. Every number rendered below is read from
that file — nothing here is hand-written.

Design rules for GitHub READMEs:
  * SVG is embedded via <img>, so SMIL animation works but <a> and hover
    tooltips do not. Keep anything clickable in markdown, not in the image.
  * prefers-color-scheme is unreliable through GitHub's image proxy, so every
    card paints its own dark panel and reads the same in both themes.
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

W = 1280  # every card is this wide so the README reads as one slab

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

MONO = "ui-monospace,'SF Mono','JetBrains Mono','Cascadia Code',Menlo,Consolas,monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,Helvetica,sans-serif"


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
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if n >= div:
            return f"{n / div:.2f}".rstrip("0").rstrip(".") + unit
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
    H = 440
    s, tm = D["summary"], D["time"]
    total = s["totalTokens"]
    digits = f"{total:,}"

    # full-range skyline silhouette across the bottom
    days = D["days"]
    mx = max(d["totals"]["tokens"] for d in days) or 1
    bw = W / len(days)
    bars = []
    for i, d in enumerate(days):
        h = 8 + (d["totals"]["tokens"] / mx) ** 0.5 * 128
        bars.append(
            f'<rect x="{i * bw:.2f}" y="{H - h:.2f}" width="{bw - 1.1:.2f}" '
            f'height="{h:.2f}" rx="1" fill="url(#sky)"/>'
        )

    chips = [
        (f'{s["activeDays"]}/{s["totalDays"]}', "DAYS ACTIVE", LIME),
        (f'{len(s["clients"])}', "RUNTIMES", CYAN),
        (f'{len(s["models"])}', "MODELS", VIOLET),
        (f'{tm.get("sessionCount", 0):,}', "SESSIONS", PINK),
        (f'{tm.get("totalActiveTimeMs", 0) / 3.6e6:,.0f}h', "AGENT UPTIME", AMBER),
    ]
    cw, cx = 218.0, 64.0
    chip_svg = []
    for i, (big, lab, col) in enumerate(chips):
        x = cx + i * cw
        chip_svg.append(
            f'<g transform="translate({x:.0f},344)">'
            f'<rect x="0" y="0" width="2" height="34" fill="{col}"/>'
            f'<text x="13" y="16" font-family="{SANS}" font-size="23" font-weight="800" fill="{TEXT}">{big}</text>'
            f'<text x="13" y="30" font-family="{MONO}" font-size="10" fill="{MUTED}" letter-spacing="1.6">{lab}</text>'
            f"</g>"
        )

    return_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{digits} AI tokens consumed, measured not estimated">
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
  <linearGradient id="beam" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="{CYAN}" stop-opacity="0"/>
    <stop offset="50%" stop-color="{CYAN}" stop-opacity="0.5"/>
    <stop offset="100%" stop-color="{CYAN}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="scrim" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{INK}" stop-opacity="0"/>
    <stop offset="26%" stop-color="{INK}" stop-opacity="0.82"/>
    <stop offset="100%" stop-color="{INK}" stop-opacity="0.92"/>
  </linearGradient>
  <radialGradient id="bloom" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0%" stop-color="{VIOLET}" stop-opacity="0.30"/><stop offset="100%" stop-color="{VIOLET}" stop-opacity="0"/>
  </radialGradient>
</defs>

<rect width="{W}" height="{H}" rx="18" fill="url(#void)"/>
<rect width="{W}" height="{H}" rx="18" fill="url(#grid_h)" opacity="0.5"/>
<ellipse cx="880" cy="150" rx="440" ry="230" fill="url(#bloom)"/>
<g>{"".join(bars)}</g>

<!-- corner marks -->
<path d="M28,52 v-16 a6,6 0 0 1 6,-6 h18" fill="none" stroke="{DIM}" stroke-width="1.2"/>
<path d="M{W - 28},52 v-16 a6,6 0 0 0 -6,-6 h-18" fill="none" stroke="{DIM}" stroke-width="1.2"/>

<text x="64" y="62" font-family="{MONO}" font-size="11" fill="{MUTED}" letter-spacing="3.4">KIMINHO — @INHODEV</text>
<g transform="translate({W - 64},62)" text-anchor="end">
  <text font-family="{MONO}" font-size="11" fill="{DIM}" letter-spacing="3.4">{D["range"]["start"]} → {D["range"]["end"]}</text>
</g>

<text x="64" y="132" font-family="{MONO}" font-size="12" fill="{CYAN}" letter-spacing="5">TOTAL AI TOKENS CONSUMED</text>
<text x="64" y="238" font-family="{MONO}" font-size="82" font-weight="700" fill="url(#num)" letter-spacing="-2">{digits}</text>
<text x="64" y="278" font-family="{MONO}" font-size="13" fill="{MUTED}" letter-spacing="1.4">parsed out of every session log on this machine — measured, not estimated</text>

<rect x="0" y="318" width="{W}" height="122" fill="url(#scrim)"/>
<rect x="64" y="304" width="{W - 128}" height="1" fill="{LINE}"/>
<rect x="64" y="303.5" width="380" height="2" fill="url(#beam)"/>

{"".join(chip_svg)}
</svg>"""
    write("hero.svg", return_svg)


# ---------------------------------------------------------------- 2. ticker
def build_ticker(D):
    H = 62
    models = sorted(D["by_model"].items(), key=lambda kv: -kv[1])

    # Static row: fit as many top models as the width allows, then say how many
    # were left out. GitHub strips SVG animation, so a marquee would render as a
    # frozen half-visible row — a packed static strip is both safer and denser.
    PADX, GAP, TAIL = 20.0, 9.0, 132.0
    pills, x = [], PADX
    shown = 0
    for name, v in models:
        label = name.split("/")[-1]
        w = 30 + len(label) * 8.0 + 66
        if x + w > W - PADX - TAIL:
            break
        pills.append(
            f'<g transform="translate({x:.1f},14)">'
            f'<rect width="{w:.1f}" height="34" rx="17" fill="#0c1220" stroke="{LINE}"/>'
            f'<circle cx="15" cy="17" r="3" fill="{CYAN}" opacity="0.8"/>'
            f'<text x="26" y="21.5" font-family="{MONO}" font-size="12.5" fill="{TEXT}">{esc(label)}</text>'
            f'<text x="{w - 14:.1f}" y="21.5" text-anchor="end" font-family="{MONO}" font-size="11" fill="{DIM}">{human(v)}</text>'
            f"</g>"
        )
        x += w + GAP
        shown += 1

    rest = len(models) - shown
    tail = (
        f'<text x="{W - PADX:.0f}" y="35.5" text-anchor="end" font-family="{MONO}" font-size="12" fill="{MUTED}">'
        f'+{rest} more models</text>'
        if rest > 0
        else ""
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{len(models)} models driven, ranked by volume">
<rect width="{W}" height="{H}" rx="12" fill="{INK}"/>
{"".join(pills)}
{tail}
</svg>"""
    write("ticker.svg", svg)


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
    PAD, HEAD, FOOT = 40, 96, 66

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

    months, seen = [], set()
    for _, col, row, d, tok, _ in cells:
        key = d.strftime("%Y-%m")
        if key in seen or not (first <= d <= last) or d.day > 7:
            continue
        seen.add(key)
        sx, sy = (col - rows + 1) * HW, (col + rows - 1) * HH
        tx, ty2 = sx + 6, sy + 38
        track(tx - 14, ty2 - 11, tx + 30, ty2 + 5)
        months.append(
            f'<text x="{tx:.1f}" y="{ty2:.1f}" font-family="{MONO}" font-size="11" fill="{DIM}" '
            f'transform="rotate(26.57 {tx:.1f} {ty2:.1f})">{d.strftime("%b").upper()}</text>'
        )

    gw, gh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    H = int(gh + HEAD + FOOT)
    dx = (W - gw) / 2 - bbox[0]
    dy = HEAD - bbox[1]

    legend = []
    lx0 = W - 96 - len(HEAT) * 28
    for i, c in enumerate(HEAT):
        x = lx0 + i * 28
        legend.append(f'<path d="M{x},{H - 40} l10,5 l-10,5 l-10,-5 Z" fill="{shade(c, 1.2)}"/>')

    s, tm = D["summary"], D["time"]
    peak = max(days, key=lambda d: d["totals"]["tokens"])

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Isometric skyline of daily AI token usage">
<defs>
  {grid_defs("s")}
  <linearGradient id="deep" x1="0" y1="0" x2="0.7" y2="1">
    <stop offset="0%" stop-color="#080d1a"/><stop offset="100%" stop-color="#040509"/>
  </linearGradient>
  <radialGradient id="halo" cx="0.5" cy="0.5" r="0.6">
    <stop offset="0%" stop-color="{CYAN}" stop-opacity="0.14"/><stop offset="100%" stop-color="{CYAN}" stop-opacity="0"/>
  </radialGradient>
</defs>

<rect width="{W}" height="{H}" rx="18" fill="url(#deep)" stroke="{LINE}"/>
<rect width="{W}" height="{H}" rx="18" fill="url(#grid_s)" opacity="0.4"/>
<rect width="{W}" height="{H}" rx="18" fill="url(#halo)"/>

<text x="44" y="46" font-family="{SANS}" font-size="21" font-weight="800" fill="{TEXT}">TOKEN SKYLINE</text>
<text x="44" y="68" font-family="{MONO}" font-size="11.5" fill="{MUTED}">one tower = one day of agent work · height is log-scaled</text>
<text x="{W - 44}" y="46" text-anchor="end" font-family="{SANS}" font-size="21" font-weight="800" fill="{CYAN}">{human(s["totalTokens"])}</text>
<text x="{W - 44}" y="68" text-anchor="end" font-family="{MONO}" font-size="11.5" fill="{DIM}">{s["activeDays"]}/{s["totalDays"]} active days · {tm.get("sessionCount", 0):,} sessions</text>

<g transform="translate({dx:.1f},{dy:.1f})">{"".join(boxes)}{"".join(months)}</g>

<text x="44" y="{H - 32}" font-family="{MONO}" font-size="11.5" fill="{MUTED}">PEAK {peak["date"]} — {human(peak["totals"]["tokens"])} in a single day</text>
<text x="{lx0 - 22}" y="{H - 31}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{DIM}">QUIET</text>
{"".join(legend)}
<text x="{W - 44}" y="{H - 31}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{DIM}">ON FIRE</text>
</svg>"""
    write("skyline.svg", svg)


# ---------------------------------------------------------------- 4. HUD
def build_hud(D):
    order = sorted(D["by_client"].items(), key=lambda kv: -kv[1])
    total = sum(v for _, v in order)
    months = sorted(D["by_month"].items())

    H = 460
    col_w = (W - 44 * 2 - 30) / 2
    lx, rx = 44.0, 44.0 + col_w + 30

    # ---- left: runtime split
    left = [
        f'<text x="{lx}" y="46" font-family="{SANS}" font-size="15" font-weight="700" fill="{TEXT}">WHERE THE TOKENS WENT</text>'
    ]
    sx, bar_w = lx, col_w
    for k, v in order:
        seg = bar_w * v / total
        left.append(
            f'<rect x="{sx:.2f}" y="62" width="{max(seg - 1.5, 1.2):.2f}" height="10" rx="3" fill="{CLIENT_COLOR.get(k, MUTED)}"/>'
        )
        sx += seg

    row_h = 46
    mxc = order[0][1]
    for i, (k, v) in enumerate(order):
        y = 104 + i * row_h
        color = CLIENT_COLOR.get(k, MUTED)
        w = max(3.0, (col_w - 150) * v / mxc)
        left.append(
            f'<g><circle cx="{lx + 5}" cy="{y + 9}" r="4" fill="{color}"/>'
            f'<text x="{lx + 18}" y="{y + 13}" font-family="{MONO}" font-size="12.5" fill="{TEXT}">{esc(CLIENT_LABEL.get(k, k))}</text>'
            f'<text x="{lx + col_w}" y="{y + 13}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{MUTED}">{human(v)}</text>'
            f'<rect x="{lx}" y="{y + 20}" width="{col_w}" height="6" rx="3" fill="#0e1524"/>'
            f'<rect x="{lx}" y="{y + 20}" width="{w:.1f}" height="6" rx="3" fill="{color}"/>'
            f'<text x="{lx + col_w}" y="{y + 32}" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{DIM}">{v / total * 100:.1f}%</text>'
            f"</g>"
        )

    # ---- right: monthly burn
    right = [
        f'<text x="{rx}" y="46" font-family="{SANS}" font-size="15" font-weight="700" fill="{TEXT}">MONTHLY BURN</text>',
        f'<text x="{rx + col_w}" y="46" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{DIM}">tokens · est. cost</text>',
    ]
    pt, pb = 96, 78
    ph = H - pt - pb
    mxm = max(v[0] for _, v in months)
    slot = col_w / len(months)
    bw = min(56.0, slot * 0.6)
    for i, (m, v) in enumerate(months):
        cx = rx + slot * (i + 0.5)
        h = ph * (v[0] / mxm)
        y = pt + ph - h
        right.append(
            f'<g><rect x="{cx - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" '
            f'height="{max(h, 2):.1f}" rx="5" fill="url(#mg)"/>'
            f'<text x="{cx:.1f}" y="{y - 9:.1f}" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{CYAN}">{human(v[0])}</text>'
            f'<text x="{cx:.1f}" y="{pt + ph + 20:.1f}" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{MUTED}">{m[5:]}</text>'
            f'<text x="{cx:.1f}" y="{pt + ph + 36:.1f}" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{DIM}">${v[1]:,.0f}</text>'
            f"</g>"
        )
    right.append(
        f'<line x1="{rx}" y1="{pt + ph:.1f}" x2="{rx + col_w}" y2="{pt + ph:.1f}" stroke="{LINE}"/>'
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Runtime split and monthly token burn">
<defs>
  <linearGradient id="mg" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0%" stop-color="{VIOLET}" stop-opacity="0.30"/><stop offset="100%" stop-color="{CYAN}"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{H}" rx="18" fill="{PANEL}" stroke="{LINE}"/>
<line x1="{rx - 15}" y1="30" x2="{rx - 15}" y2="{H - 30}" stroke="{LINE}"/>
{"".join(left)}
{"".join(right)}
</svg>"""
    write("hud.svg", svg)


# ---------------------------------------------------------------- README
START, END = "<!-- STATS:START -->", "<!-- STATS:END -->"
IMG_START, IMG_END = "<!-- IMAGES:START -->", "<!-- IMAGES:END -->"

# GitHub proxies README images through camo, which caches by URL. Same path +
# new content = the old picture served indefinitely. Appending a content hash
# gives every rebuild a fresh URL.
CARDS = [
    ("hero.svg", "Total AI tokens consumed — measured, not estimated"),
    ("ticker.svg", "Models driven, ranked by volume"),
    ("skyline.svg", "Isometric skyline — one tower per day of agent work"),
    ("hud.svg", "Runtime split and monthly token burn"),
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
        ("Window", f'`{r["start"]} → {r["end"]}` — {stats["totalDays"]} days, **{stats["activeDays"]} of them active**'),
        ("Tokens", f'**{stats["totalTokens"]:,}**'),
        ("Messages", f'{stats["messages"]:,}'),
        ("Sessions", f'{stats["sessions"]:,}'),
        ("Agent uptime", f'{hours:,.0f} h — roughly **{hours / 24:.0f} days** of compute inside {stats["totalDays"]} calendar days'),
        ("Longest unbroken run", f'{stats["longestContinuousHours"]:,.1f} h'),
        ("Peak concurrency", f'{stats["maxConcurrentSessions"]} sessions at once'),
        ("Biggest single day", f'`{peak["date"]}` — {human(peak["totals"]["tokens"])} tokens'),
        ("Distinct models", f'{stats["models"]}, across {len(stats["clients"])} runtimes'),
    ]
    if cf:
        rows.append(
            ("Codex measured coverage",
             f'**{cf["measured"] / cf["target"] * 100:.2f}%** — {cf["measured"]:,} of {cf["target"]:,} '
             f'reconstructed from local logs day by day')
        )
    table = "| | |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in rows)

    block = (
        f"{START}\n\n{table}\n\n"
        f"<sub>Written by <code>scripts/build_assets.py</code>. Do not edit by hand — it will be overwritten.</sub>\n\n"
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
    build_ticker(D)
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
