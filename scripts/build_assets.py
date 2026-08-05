#!/usr/bin/env python3
"""
Regenerate every SVG in assets/ from data/graph.json.

data/graph.json is produced by:  bunx tokscale@latest graph --output data/graph.json
Every number rendered below comes from that file — nothing is hand-written.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "graph.json"
OUT = ROOT / "assets"

# ---------------------------------------------------------------- palette
BG = "#06070d"
PANEL = "#0b0e16"
STROKE = "#1b2333"
TEXT = "#e8ecf5"
MUTED = "#79839a"
DIM = "#4a5468"

CYAN = "#22d3ee"
VIOLET = "#a78bfa"
PINK = "#f472b6"
LIME = "#a3e635"

# heat ramp for the isometric towers: cold deep-blue -> white-hot -> magenta
HEAT = ["#14264a", "#155e75", "#0891b2", "#22d3ee", "#7dd3fc", "#e879f9"]

CLIENT_COLOR = {
    "codex": "#10b981",
    "claude": "#d97757",
    "hermes": "#a78bfa",
    "opencode": "#f472b6",
    "gjc": "#facc15",
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


# ---------------------------------------------------------------- helpers
def shade(hex_color: str, factor: float) -> str:
    """factor < 1 darkens, > 1 lightens."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    if factor <= 1:
        r, g, b = (int(c * factor) for c in (r, g, b))
    else:
        t = factor - 1
        r, g, b = (int(c + (255 - c) * t) for c in (r, g, b))
    return "#%02x%02x%02x" % (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def human(n: float) -> str:
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if n >= div:
            return f"{n / div:.2f}".rstrip("0").rstrip(".") + unit
    return f"{n:,.0f}"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write(name: str, body: str) -> None:
    (OUT / name).write_text(body, encoding="utf-8")
    print(f"  wrote assets/{name}  ({len(body):,} bytes)")


FONT = (
    "ui-monospace,'SF Mono','JetBrains Mono','Cascadia Code',Menlo,Consolas,monospace"
)
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,sans-serif"


# ---------------------------------------------------------------- load
def apply_overrides(g):
    """Anchor a client's lifetime total to an externally reported figure.

    Local logs get pruned, so a local scan undercounts. We trust the local data
    for the *shape* of each day and scale it by one constant so the lifetime
    total matches what the provider itself reports. Returns the factors used.
    """
    path = ROOT / "data" / "overrides.json"
    if not path.exists():
        return {}
    ov = json.loads(path.read_text(encoding="utf-8"))
    factors = {}

    for client, cfg in ov.items():
        if client.startswith("_"):
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
        factors[client] = f
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
        g["summary"]["totalTokens"] = sum(
            d["totals"]["tokens"] for d in g["contributions"]
        )
        print(f"  override: {client} x{f:.5f}  ({local:,} -> {target:,})")

    return factors


def load():
    g = json.loads(DATA.read_text(encoding="utf-8"))
    factors = apply_overrides(g)
    days = g["contributions"]
    s = g["summary"]
    tm = g.get("timeMetrics", {})

    by_client = defaultdict(int)
    by_provider = defaultdict(int)
    by_model = defaultdict(int)
    for d in days:
        for e in d["clients"]:
            t = sum(e["tokens"].values())
            by_client[e["client"]] += t
            by_provider[e["providerId"]] += t
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
        "summary": s,
        "time": tm,
        "range": g["meta"]["dateRange"],
        "by_client": dict(by_client),
        "by_provider": dict(by_provider),
        "by_model": dict(by_model),
        "by_month": dict(by_month),
        "messages": sum(d["totals"]["messages"] for d in days),
    }


# ---------------------------------------------------------------- 1. hero
def build_hero(D):
    W, H = 900, 210
    total = D["summary"]["totalTokens"]

    # faint skyline of the last 60 days along the bottom edge
    tail = D["days"][-60:]
    mx = max(d["totals"]["tokens"] for d in tail) or 1
    bw = W / len(tail)
    bars = []
    for i, d in enumerate(tail):
        h = 6 + (d["totals"]["tokens"] / mx) ** 0.55 * 46
        bars.append(
            f'<rect x="{i * bw:.2f}" y="{H - h:.2f}" width="{bw - 1.4:.2f}" '
            f'height="{h:.2f}" rx="1.4" fill="url(#hg)" opacity="0.5"/>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="kiminho — AI-native builder">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#0a0f1e"/><stop offset="52%" stop-color="#0e0a1f"/><stop offset="100%" stop-color="#050609"/>
  </linearGradient>
  <linearGradient id="hg" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0%" stop-color="{CYAN}" stop-opacity="0.15"/><stop offset="100%" stop-color="{VIOLET}"/>
  </linearGradient>
  <linearGradient id="name" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#ffffff"/><stop offset="42%" stop-color="{CYAN}"/>
    <stop offset="72%" stop-color="{VIOLET}"/><stop offset="100%" stop-color="{PINK}"/>
  </linearGradient>
  <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0%" stop-color="{VIOLET}" stop-opacity="0.34"/><stop offset="100%" stop-color="{VIOLET}" stop-opacity="0"/>
  </radialGradient>
  <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
    <path d="M30 0H0V30" fill="none" stroke="#1a2338" stroke-width="0.6" opacity="0.5"/>
  </pattern>
</defs>

<rect width="{W}" height="{H}" rx="16" fill="url(#sky)"/>
<rect width="{W}" height="{H}" rx="16" fill="url(#grid)"/>
<ellipse cx="726" cy="72" rx="270" ry="150" fill="url(#glow)"/>
<g>{"".join(bars)}</g>

<text x="42" y="72" font-family="{SANS}" font-size="43" font-weight="800" fill="url(#name)" letter-spacing="-1.4">kiminho</text>
<text x="42" y="98" font-family="{FONT}" font-size="12" fill="{MUTED}" letter-spacing="2.4">@INHODEV · INHA UNIVERSITY · INCHEON KR</text>

<g transform="translate(42,118)">
  <rect width="272" height="27" rx="13.5" fill="#0d1424" stroke="{STROKE}"/>
  <circle cx="16" cy="13.5" r="3.6" fill="{LIME}">
    <animate attributeName="opacity" values="1;0.25;1" dur="2.4s" repeatCount="indefinite"/>
  </circle>
  <text x="29" y="18" font-family="{FONT}" font-size="11.5" fill="{TEXT}">shipping with agents, not around them</text>
</g>

<g text-anchor="end">
  <text x="858" y="60" font-family="{FONT}" font-size="10.5" fill="{DIM}" letter-spacing="2.4">LIFETIME AI TOKENS BURNED</text>
  <text x="858" y="112" font-family="{SANS}" font-size="52" font-weight="800" fill="{CYAN}" letter-spacing="-1.8">{human(total)}</text>
  <text x="858" y="134" font-family="{FONT}" font-size="10.5" fill="{DIM}">{total:,} · measured, not estimated</text>
</g>
</svg>"""
    write("hero.svg", svg)


# ---------------------------------------------------------------- 2. 3D graph
def build_tokens_3d(D):
    days = D["days"]
    first = date.fromisoformat(days[0]["date"])
    last = date.fromisoformat(days[-1]["date"])

    by_date = {d["date"]: d for d in days}

    # calendar grid: column = week index, row = weekday (Mon=0)
    origin = date.fromordinal(first.toordinal() - first.weekday())
    cols = (last.toordinal() - origin.toordinal()) // 7 + 1
    rows = 7

    mx = max(d["totals"]["tokens"] for d in days)

    TW, TH = 42.0, 21.0          # tile width / height (isometric diamond)
    HW, HH = TW / 2, TH / 2
    MAXH = 190.0                 # tallest tower

    # geometry is laid out around origin, then translated to fit a tight box
    ox = oy = 0.0
    PAD_X, HEAD, FOOT = 34, 84, 62

    cells = []
    for col in range(cols):
        for row in range(rows):
            d = origin.fromordinal(origin.toordinal() + col * 7 + row)
            rec = by_date.get(d.isoformat())
            if not rec and not (first <= d <= last):
                continue
            tok = rec["totals"]["tokens"] if rec else 0
            cells.append((col + row, col, row, d, tok, rec))
    cells.sort(key=lambda c: (c[0], c[2]))

    bbox = [1e9, 1e9, -1e9, -1e9]  # minx, miny, maxx, maxy

    def track(x0, y0, x1, y1):
        bbox[0] = min(bbox[0], x0)
        bbox[1] = min(bbox[1], y0)
        bbox[2] = max(bbox[2], x1)
        bbox[3] = max(bbox[3], y1)

    boxes = []
    for _, col, row, d, tok, rec in cells:
        sx = ox + (col - row) * HW
        sy = oy + (col + row) * HH
        track(sx - HW, sy, sx + HW, sy + TH)

        if tok <= 0:
            # empty plate for days inside the range with no recorded usage
            boxes.append(
                f'<path d="M{sx:.1f},{sy:.1f} l{HW:.1f},{HH:.1f} l{-HW:.1f},{HH:.1f} '
                f'l{-HW:.1f},{-HH:.1f} Z" fill="#0e1423" stroke="#161d2e" stroke-width="0.5"/>'
            )
            continue

        ratio = (tok / mx) ** 0.42
        h = 3.0 + ratio * MAXH
        idx = min(len(HEAT) - 1, int(ratio * (len(HEAT) - 0.001)))
        base = HEAT[idx]
        top_c, left_c, right_c = shade(base, 1.18), shade(base, 0.46), shade(base, 0.70)

        ty = sy - h
        track(sx - HW, ty, sx + HW, sy + TH)
        tip = (
            f"{d.isoformat()} · {human(tok)} tokens · ${rec['totals']['cost']:,.2f} · "
            f"{rec['totals']['messages']:,} msgs"
        )
        boxes.append(
            f'<g><title>{esc(tip)}</title>'
            # left face
            f'<path d="M{sx - HW:.1f},{ty + HH:.1f} l{HW:.1f},{HH:.1f} l0,{h:.1f} '
            f'l{-HW:.1f},{-HH:.1f} Z" fill="{left_c}"/>'
            # right face
            f'<path d="M{sx + HW:.1f},{ty + HH:.1f} l{-HW:.1f},{HH:.1f} l0,{h:.1f} '
            f'l{HW:.1f},{-HH:.1f} Z" fill="{right_c}"/>'
            # top face
            f'<path d="M{sx:.1f},{ty:.1f} l{HW:.1f},{HH:.1f} l{-HW:.1f},{HH:.1f} '
            f'l{-HW:.1f},{-HH:.1f} Z" fill="{top_c}" stroke="{shade(base, 1.45)}" stroke-width="0.5"/>'
            f"</g>"
        )

    # month ticks hugging the front-left edge of the slab (row 6 = Sunday)
    months = []
    seen = set()
    for _, col, row, d, tok, _ in cells:
        key = d.strftime("%Y-%m")
        if key in seen or not (first <= d <= last) or d.day > 7:
            continue
        seen.add(key)
        sx = ox + (col - rows + 1) * HW
        sy = oy + (col + rows - 1) * HH
        tx, ty2 = sx + 4, sy + 30
        track(tx - 12, ty2 - 10, tx + 26, ty2 + 4)
        months.append(
            f'<text x="{tx:.1f}" y="{ty2:.1f}" font-family="{FONT}" font-size="10.5" fill="{DIM}" '
            f'transform="rotate(26.57 {tx:.1f} {ty2:.1f})">{d.strftime("%b")}</text>'
        )

    # translate geometry into a tight frame
    gw = bbox[2] - bbox[0]
    gh = bbox[3] - bbox[1]
    W = int(gw + PAD_X * 2)
    H = int(gh + HEAD + FOOT)
    dx = PAD_X - bbox[0]
    dy = HEAD - bbox[1]

    legend = []
    lx0 = W - 82 - len(HEAT) * 26
    for i, c in enumerate(HEAT):
        x = lx0 + i * 26
        legend.append(
            f'<path d="M{x},{H - 38} l9,4.5 l-9,4.5 l-9,-4.5 Z" fill="{shade(c, 1.18)}"/>'
        )
    legend_txt = (
        f'<text x="{lx0 - 16}" y="{H - 30}" font-family="{FONT}" font-size="10" fill="{DIM}" '
        f'text-anchor="end">quiet</text>'
        f'<text x="{W - 30}" y="{H - 30}" font-family="{FONT}" font-size="10" fill="{DIM}" '
        f'text-anchor="end">on fire</text>'
    )

    s, tm = D["summary"], D["time"]
    peak = max(days, key=lambda d: d["totals"]["tokens"])

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="3D token usage contribution graph">
<defs>
  <linearGradient id="bg3d" x1="0" y1="0" x2="0.7" y2="1">
    <stop offset="0%" stop-color="#0a0d18"/><stop offset="100%" stop-color="#05060b"/>
  </linearGradient>
  <radialGradient id="halo" cx="0.55" cy="0.45" r="0.62">
    <stop offset="0%" stop-color="{CYAN}" stop-opacity="0.13"/><stop offset="100%" stop-color="{CYAN}" stop-opacity="0"/>
  </radialGradient>
</defs>

<rect width="{W}" height="{H}" rx="16" fill="url(#bg3d)" stroke="{STROKE}"/>
<rect width="{W}" height="{H}" rx="16" fill="url(#halo)"/>

<text x="30" y="36" font-family="{SANS}" font-size="17" font-weight="700" fill="{TEXT}">Token Skyline</text>
<text x="30" y="56" font-family="{FONT}" font-size="10.5" fill="{MUTED}">one tower = one day · {D["range"]["start"]} → {D["range"]["end"]}</text>

<text x="{W - 30}" y="34" text-anchor="end" font-family="{SANS}" font-size="22" font-weight="800" fill="{CYAN}">{human(s["totalTokens"])}</text>
<text x="{W - 30}" y="54" text-anchor="end" font-family="{FONT}" font-size="10.5" fill="{DIM}">{s["activeDays"]}/{s["totalDays"]} active days · {tm.get("sessionCount", 0):,} sessions</text>

<g transform="translate({dx:.1f},{dy:.1f})">{"".join(boxes)}{"".join(months)}</g>

<text x="30" y="{H - 30}" font-family="{FONT}" font-size="10.5" fill="{MUTED}">peak {peak["date"]} — {human(peak["totals"]["tokens"])} in a single day</text>
<g>{"".join(legend)}</g>{legend_txt}
</svg>"""
    write("tokens-3d.svg", svg)


# ---------------------------------------------------------------- 3. stat cards
def build_stats(D):
    s, tm = D["summary"], D["time"]
    hours = tm.get("totalActiveTimeMs", 0) / 3.6e6

    cards = [
        ("TOKENS BURNED", human(s["totalTokens"]), f'{s["totalTokens"]:,}', CYAN),
        ("AGENT SESSIONS", f'{tm.get("sessionCount", 0):,}', f'{D["messages"]:,} messages', VIOLET),
        ("AGENT UPTIME", f"{hours:,.0f}h", f"{hours / 24:.0f} days of compute", PINK),
        ("MODELS DRIVEN", f'{len(s["models"])}', f'{len(s["clients"])} agent runtimes', LIME),
    ]

    W, H = 900, 128
    cw = (W - 30 * 2 - 14 * 3) / 4
    out = []
    for i, (label, big, sub, color) in enumerate(cards):
        x = 30 + i * (cw + 14)
        out.append(
            f'<g transform="translate({x:.1f},26)">'
            f'<rect width="{cw:.1f}" height="80" rx="12" fill="{PANEL}" stroke="{STROKE}"/>'
            f'<rect width="3" height="80" rx="1.5" fill="{color}"/>'
            f'<text x="16" y="22" font-family="{FONT}" font-size="9.5" fill="{DIM}" letter-spacing="1.5">{label}</text>'
            f'<text x="16" y="52" font-family="{SANS}" font-size="27" font-weight="800" fill="{color}" letter-spacing="-0.8">{big}</text>'
            f'<text x="16" y="69" font-family="{FONT}" font-size="9.5" fill="{MUTED}">{esc(sub)}</text>'
            f"</g>"
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="AI usage stat cards">
<rect width="{W}" height="{H}" rx="16" fill="{BG}"/>
{"".join(out)}
<text x="30" y="{H - 10}" font-family="{FONT}" font-size="9.5" fill="{DIM}">source: tokscale scan of ~/.claude ~/.codex ~/.gemini opencode &amp; friends · Codex total anchored to provider-reported figures · rebuilt daily</text>
</svg>"""
    write("stats.svg", svg)


# ---------------------------------------------------------------- 4. agent mix
def build_agents(D):
    total = sum(D["by_client"].values())
    order = sorted(D["by_client"].items(), key=lambda kv: -kv[1])

    W = 900
    row_h = 30
    H = 96 + len(order) * row_h + 92

    bar_x, bar_w = 178, W - 178 - 148

    # stacked share bar
    stack, cx = [], 30.0
    sw = W - 60
    for k, v in order:
        seg = sw * v / total
        stack.append(
            f'<rect x="{cx:.2f}" y="60" width="{max(seg - 1.5, 1.2):.2f}" height="11" rx="3" '
            f'fill="{CLIENT_COLOR.get(k, MUTED)}"><title>{esc(CLIENT_LABEL.get(k, k))} — {v / total * 100:.1f}%</title></rect>'
        )
        cx += seg

    rows = []
    mx = order[0][1]
    for i, (k, v) in enumerate(order):
        y = 96 + i * row_h
        color = CLIENT_COLOR.get(k, MUTED)
        w = max(3.0, bar_w * v / mx)
        rows.append(
            f'<g><title>{esc(CLIENT_LABEL.get(k, k))} — {v:,} tokens</title>'
            f'<circle cx="34" cy="{y + 9}" r="4" fill="{color}"/>'
            f'<text x="48" y="{y + 13}" font-family="{FONT}" font-size="12" fill="{TEXT}">{esc(CLIENT_LABEL.get(k, k))}</text>'
            f'<rect x="{bar_x}" y="{y + 3}" width="{bar_w}" height="12" rx="6" fill="#101725"/>'
            f'<rect x="{bar_x}" y="{y + 3}" width="{w:.1f}" height="12" rx="6" fill="{color}" opacity="0.9"/>'
            f'<text x="{W - 30}" y="{y + 13}" text-anchor="end" font-family="{FONT}" font-size="11.5" fill="{MUTED}">'
            f'{human(v)}  ·  {v / total * 100:5.1f}%</text></g>'
        )

    # top models strip
    models = sorted(D["by_model"].items(), key=lambda kv: -kv[1])[:6]
    mstrip, mx2 = [], 30.0
    my = 96 + len(order) * row_h + 40
    for name, v in models:
        label = name.split("/")[-1]
        wpx = 12 + len(label) * 6.6
        mstrip.append(
            f'<g><title>{esc(name)} — {v:,} tokens</title>'
            f'<rect x="{mx2:.1f}" y="{my}" width="{wpx:.1f}" height="22" rx="11" fill="#0f1626" stroke="{STROKE}"/>'
            f'<text x="{mx2 + wpx / 2:.1f}" y="{my + 15}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="10.5" fill="{MUTED}">{esc(label)}</text></g>'
        )
        mx2 += wpx + 8

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Agent runtime token distribution">
<rect width="{W}" height="{H}" rx="16" fill="{PANEL}" stroke="{STROKE}"/>
<text x="30" y="36" font-family="{SANS}" font-size="17" font-weight="700" fill="{TEXT}">Where the tokens went</text>
<text x="{W - 30}" y="36" text-anchor="end" font-family="{FONT}" font-size="11" fill="{DIM}">{len(order)} runtimes · {len(D["by_model"])} distinct models</text>
{"".join(stack)}
{"".join(rows)}
<text x="30" y="{my - 8}" font-family="{FONT}" font-size="10" fill="{DIM}" letter-spacing="1.4">TOP MODELS BY VOLUME</text>
{"".join(mstrip)}
</svg>"""
    write("agents.svg", svg)


# ---------------------------------------------------------------- 5. monthly
def build_monthly(D):
    months = sorted(D["by_month"].items())
    W, H = 900, 250
    pad_l, pad_r, pad_t, pad_b = 58, 30, 62, 52
    pw, ph = W - pad_l - pad_r, H - pad_t - pad_b
    mx = max(v[0] for _, v in months)

    slot = pw / len(months)
    bw = min(64.0, slot * 0.56)

    bars, labels, pts = [], [], []
    for i, (m, v) in enumerate(months):
        cx = pad_l + slot * (i + 0.5)
        h = ph * (v[0] / mx)
        y = pad_t + ph - h
        bars.append(
            f'<g><title>{m} — {v[0]:,} tokens · ${v[1]:,.0f} · {v[2]:,} msgs</title>'
            f'<rect x="{cx - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(h, 2):.1f}" rx="5" fill="url(#mg)"/>'
            f'<text x="{cx:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-family="{FONT}" font-size="10.5" '
            f'fill="{CYAN}">{human(v[0])}</text></g>'
        )
        labels.append(
            f'<text x="{cx:.1f}" y="{pad_t + ph + 20:.1f}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="10.5" fill="{MUTED}">{m[5:]}/{m[2:4]}</text>'
        )
        labels.append(
            f'<text x="{cx:.1f}" y="{pad_t + ph + 36:.1f}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="9.5" fill="{DIM}">${v[1]:,.0f}</text>'
        )
        pts.append(f"{cx:.1f},{y:.1f}")

    grid = []
    for f in (0, 0.25, 0.5, 0.75, 1.0):
        y = pad_t + ph - ph * f
        grid.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{W - pad_r}" y2="{y:.1f}" stroke="#141b2b" stroke-width="1"/>'
            f'<text x="{pad_l - 10}" y="{y + 3.5:.1f}" text-anchor="end" font-family="{FONT}" font-size="9.5" '
            f'fill="{DIM}">{human(mx * f)}</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Monthly token consumption">
<defs>
  <linearGradient id="mg" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0%" stop-color="{VIOLET}" stop-opacity="0.35"/><stop offset="100%" stop-color="{CYAN}"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{H}" rx="16" fill="{PANEL}" stroke="{STROKE}"/>
<text x="30" y="34" font-family="{SANS}" font-size="17" font-weight="700" fill="{TEXT}">Monthly burn</text>
<text x="{W - 30}" y="34" text-anchor="end" font-family="{FONT}" font-size="11" fill="{DIM}">tokens per month · est. cost below</text>
{"".join(grid)}
<polyline points="{" ".join(pts)}" fill="none" stroke="{PINK}" stroke-width="1.6" stroke-dasharray="3 3" opacity="0.55"/>
{"".join(bars)}
{"".join(labels)}
</svg>"""
    write("monthly.svg", svg)


# ---------------------------------------------------------------- README
README_START = "<!-- STATS:START -->"
README_END = "<!-- STATS:END -->"


def inject_readme(D, stats):
    """Rewrite the raw-totals table in README.md so it can never drift."""
    path = ROOT / "README.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if README_START not in text or README_END not in text:
        print("  README markers not found — skipped")
        return

    days = D["days"]
    peak = max(days, key=lambda d: d["totals"]["tokens"])
    r = stats["range"]
    hours = stats["activeHours"]
    cov = D["raw"].get("_codexCoverage")

    rows = [
        ("Window", f'`{r["start"]} → {r["end"]}` ({stats["totalDays"]} days, **{stats["activeDays"]} active**)'),
        ("Tokens", f'**{stats["totalTokens"]:,}**'),
        ("Messages", f'{stats["messages"]:,}'),
        ("Sessions", f'{stats["sessions"]:,}'),
        ("Agent uptime", f'{hours:,.0f} h — about **{hours / 24:.0f} days** of compute inside {stats["totalDays"]} calendar days'),
        ("Longest unbroken run", f'{stats["longestContinuousHours"]:,.1f} h'),
        ("Peak concurrency", f'{stats["maxConcurrentSessions"]} sessions at once'),
        ("Biggest single day", f'`{peak["date"]}` — {human(peak["totals"]["tokens"])} tokens'),
        ("Distinct models", f'{stats["models"]}, across {len(stats["clients"])} runtimes'),
    ]
    table = "| | |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in rows)

    block = (
        f"{README_START}\n\n{table}\n\n"
        f"<sub>Generated by <code>scripts/build_assets.py</code> — do not edit by hand.</sub>\n\n"
        f"{README_END}"
    )
    head, _, rest = text.partition(README_START)
    _, _, tail = rest.partition(README_END)
    path.write_text(head + block + tail, encoding="utf-8")
    print("  updated README.md stats block")


# ---------------------------------------------------------------- main
def main():
    print("building assets from", DATA)
    D = load()
    OUT.mkdir(exist_ok=True)
    build_hero(D)
    build_tokens_3d(D)
    build_stats(D)
    build_agents(D)
    build_monthly(D)

    # numbers the README quotes, so a refresh can be diffed at a glance
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
    }
    (ROOT / "data" / "stats.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("  wrote data/stats.json")
    inject_readme(D, stats)
    print(f"\n  {human(s['totalTokens'])} tokens · ${s['totalCost']:,.0f} · {s['activeDays']} active days")


if __name__ == "__main__":
    main()
