<!-- IMAGES:START -->

<img src="./assets/hero.svg?v=0c1df8527b" alt="Total AI tokens consumed — measured, not estimated" width="100%">

<img src="./assets/ticker.svg?v=43a67fc82b" alt="Models driven, ranked by volume" width="100%">

<img src="./assets/skyline.svg?v=a6710a0e9b" alt="Isometric skyline — one tower per day of agent work" width="100%">

<img src="./assets/hud.svg?v=4dea429660" alt="Runtime split and monthly token burn" width="100%">

<!-- IMAGES:END -->

<!-- STATS:START -->

| | |
|---|---|
| Window | `2026-01-07 → 2026-08-05` — 138 days, **138 of them active** |
| Tokens | **34,004,134,923** |
| Messages | 246,787 |
| Sessions | 10,511 |
| Agent uptime | 2,134 h — roughly **89 days** of compute inside 138 calendar days |
| Longest unbroken run | 146.7 h |
| Peak concurrency | 22 sessions at once |
| Biggest single day | `2026-05-25` — 2.4B tokens |
| Distinct models | 45, across 7 runtimes |
| Codex measured coverage | **96.53%** — 28,062,310,711 of 29,070,000,000 reconstructed from local logs day by day |

<sub>Written by <code>scripts/build_assets.py</code>. Do not edit by hand — it will be overwritten.</sub>

<!-- STATS:END -->

<br>

> **Anyone can put a badge on a profile. This one is reproducible.**
> Clone the repo, run `bash scripts/refresh.sh`, and every pixel above regenerates from your own
> machine's session logs. The generator is plain Python with no dependencies.

<details>
<summary><b>How these numbers are made — and where they stop being exact</b></summary>

<br>

```bash
bash scripts/refresh.sh    # scan every agent store → merge → rebuild every SVG
```

**Measured.** Per-message token counts are read straight out of local session logs — input,
output, cache-read and cache-write counted separately, then summed. 6,872 Codex rollout files
across two directories, 496 Claude Code transcripts, plus OpenCode, Hermes, Kilo, Gajae-Code and
Antigravity stores. Session IDs across directories are disjoint, so nothing is double-counted.

**Anchored.** OpenAI reports 29.07B lifetime tokens across two accounts. Local logs independently
account for **96.53%** of that, day by day. The remaining 3.47% has no local source left — those
sessions were pruned before they were ever scanned, and there is no per-day API to recover them —
so that residual is spread across days in proportion to measured activity. Exact figures and
reasoning: [`data/overrides.json`](./data/overrides.json).

**Estimated.** Cost comes from public per-model pricing, not from a bill. Order of magnitude, not
an invoice. That is why no dollar figure appears above the fold.

**Generated.** Every SVG and the table above are written by
[`scripts/build_assets.py`](./scripts/build_assets.py) from [`data/graph.json`](./data/graph.json).
Nothing in this README is typed by hand. Change the data, the picture changes.

Machine-readable: [`data/stats.json`](./data/stats.json) · [`data/graph.json`](./data/graph.json)

</details>

---

### Building

| | |
|---|---|
| [**olli-interest-map**](https://github.com/inhodev/olli-interest-map) | 매주 꽂히는 게 바뀌어서, 아예 지도로 만든 관심맵 |
| [**safe_map**](https://github.com/inhodev/safe_map) | 인하대 안전지도 · D-UP contest |
| [**Library-of-Things**](https://github.com/inhodev/Library-of-Things) | 물건을 빌려 쓰는 도서관 · GDGoC × AZIT hackathon |
| [**copyvara-ai**](https://github.com/inhodev/copyvara-ai) · [**copyvara-fast**](https://github.com/inhodev/copyvara-fast) | Python 코어 + TypeScript 런타임 |
| [**insta-ripper**](https://github.com/inhodev/insta-ripper) | 로그인 없는 인스타 다운로더 |
| [**myBIBLE**](https://github.com/inhodev/myBIBLE) | 나만의 성경앱 |

<sub>Dart · TypeScript · Python · JavaScript — whatever ships this week.</sub>

<br>

<sub><b>kiminho</b> · Inha University · Incheon, KR<br>
The graph is not a flex about spend. It is a log of how much of this was built by driving agents
instead of typing.</sub>
