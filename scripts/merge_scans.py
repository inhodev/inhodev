#!/usr/bin/env python3
"""
Merge several tokscale `graph` exports into one, day by day.

tokscale scans a single sessions directory per run. Codex sessions live in two
places on this machine (~/.codex/sessions and ~/.codex/archived_sessions, both
symlinked out to an external volume), so each is scanned separately and merged
here. Session IDs across the two directories are disjoint, so nothing is
double-counted.

usage: merge_scans.py OUT.json IN1.json IN2.json [...]
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def merge(paths):
    days = {}
    meta_versions = set()
    time_totals = defaultdict(int)
    mcp = set()

    for p in paths:
        g = json.loads(Path(p).read_text(encoding="utf-8"))
        meta_versions.add(g["meta"].get("version", "?"))
        mcp.update(g.get("mcpServers") or [])

        tm = g.get("timeMetrics") or {}
        time_totals["totalActiveTimeMs"] += tm.get("totalActiveTimeMs", 0)
        time_totals["sessionCount"] += tm.get("sessionCount", 0)
        time_totals["longestContinuousMs"] = max(
            time_totals["longestContinuousMs"], tm.get("longestContinuousMs", 0)
        )
        time_totals["maxConcurrentSessions"] = max(
            time_totals["maxConcurrentSessions"], tm.get("maxConcurrentSessions", 0)
        )

        for d in g["contributions"]:
            cur = days.get(d["date"])
            if cur is None:
                days[d["date"]] = json.loads(json.dumps(d))
                continue
            for key in ("tokens", "cost", "messages"):
                cur["totals"][key] += d["totals"][key]
            for key in cur.get("tokenBreakdown", {}):
                cur["tokenBreakdown"][key] += d.get("tokenBreakdown", {}).get(key, 0)
            cur["activeTimeMs"] = cur.get("activeTimeMs", 0) + d.get("activeTimeMs", 0)

            # fold client rows together on (client, modelId, providerId)
            index = {
                (e["client"], e["modelId"], e["providerId"]): e for e in cur["clients"]
            }
            for e in d["clients"]:
                k = (e["client"], e["modelId"], e["providerId"])
                if k in index:
                    tgt = index[k]
                    for tk in e["tokens"]:
                        tgt["tokens"][tk] = tgt["tokens"].get(tk, 0) + e["tokens"][tk]
                    tgt["cost"] += e["cost"]
                    tgt["messages"] += e["messages"]
                else:
                    cur["clients"].append(json.loads(json.dumps(e)))
                    index[k] = cur["clients"][-1]

    contributions = [days[k] for k in sorted(days)]
    total_tokens = sum(d["totals"]["tokens"] for d in contributions)
    total_cost = sum(d["totals"]["cost"] for d in contributions)

    models, clients = set(), set()
    for d in contributions:
        for e in d["clients"]:
            models.add(e["modelId"])
            clients.add(e["client"])

    return {
        "meta": {
            "generatedBy": "merge_scans.py",
            "tokscaleVersions": sorted(meta_versions),
            "sources": [str(p) for p in paths],
            "dateRange": {
                "start": contributions[0]["date"],
                "end": contributions[-1]["date"],
            },
        },
        "summary": {
            "totalTokens": total_tokens,
            "totalCost": total_cost,
            "totalDays": len(contributions),
            "activeDays": sum(
                1 for d in contributions if d["totals"]["tokens"] > 0
            ),
            "clients": sorted(clients),
            "models": sorted(models),
        },
        "contributions": contributions,
        "timeMetrics": dict(time_totals),
        "mcpServers": sorted(mcp),
    }


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out, ins = sys.argv[1], sys.argv[2:]
    g = merge(ins)
    Path(out).write_text(json.dumps(g), encoding="utf-8")
    s = g["summary"]
    print(
        f"merged {len(ins)} scans -> {out}\n"
        f"  {s['totalTokens']:,} tokens · {s['activeDays']}/{s['totalDays']} active days · "
        f"{len(s['models'])} models"
    )


if __name__ == "__main__":
    main()
