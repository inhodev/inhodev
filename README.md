<!-- IMAGES:START -->

<img src="./assets/hero.svg?v=9884262548" alt="총 소비한 AI 토큰 — 추정이 아니라 실측" width="100%">

<img src="./assets/skyline.svg?v=f8afaba705" alt="토큰 스카이라인 — 탑 하나가 하루치 작업" width="100%">

<img src="./assets/hud.svg?v=1d641a9a6e" alt="런타임별 분포와 월별 소비량" width="100%">

<!-- IMAGES:END -->

<!-- STATS:START -->

| | |
|---|---|
| 기간 | `2026-01-07 → 2026-08-05` — 138일 중 **138일 활동** |
| 총 토큰 | **34,004,134,923** (340억) |
| 메시지 | 246,787 |
| 세션 | 10,511 |
| 에이전트 가동시간 | 2,134시간 — 138일 안에 **약 89일치** 연산 |
| 최장 연속 가동 | 146.7시간 |
| 최대 동시 세션 | 22개 |
| 하루 최고 기록 | `2026-05-25` — 24억 |
| 모델 / 런타임 | 45종 / 7개 |
| Codex 실측 커버리지 | **96.53%** — 공식 29,070,000,000 중 28,062,310,711을 로컬 로그에서 일자별로 복원 |

<sub><code>scripts/build_assets.py</code>가 생성한 표입니다. 직접 고쳐도 다음 빌드에 덮어써집니다.</sub>

<!-- STATS:END -->

<br>

> **뱃지는 누구나 붙인다. 이건 재현이 된다.**
> 이 저장소를 클론하고 `bash scripts/refresh.sh` 한 줄만 돌리면, 위의 모든 픽셀이 당신 컴퓨터의
> 세션 로그에서 다시 만들어집니다. 생성기는 의존성 없는 순수 파이썬입니다.

<details>
<summary><b>이 숫자들은 어떻게 만들어졌나 — 그리고 어디부터 정확하지 않은가</b></summary>

<br>

```bash
bash scripts/refresh.sh    # 모든 에이전트 저장소 스캔 → 병합 → 전체 SVG 재생성
```

**실측한 부분.** 로컬 세션 로그의 메시지별 토큰 수를 그대로 읽습니다. 입력·출력·캐시 읽기·캐시 쓰기를
각각 따로 세고 합칩니다. 두 디렉터리에 걸친 Codex 롤아웃 파일 6,872개, Claude Code 트랜스크립트
496개, 그리고 OpenCode·Hermes·Kilo·Gajae-Code·Antigravity 저장소까지. 디렉터리 간 세션 ID가
겹치지 않아 중복 집계는 없습니다.

**보정한 부분.** OpenAI는 두 계정 합산 누적 290.7억 토큰을 보고합니다. 로컬 로그만으로 그중
**96.53%** 를 일자별로 독립 재구성했습니다. 나머지 3.47% 는 로컬에 원본이 남아 있지 않고 — 스캔되기
전에 정리된 세션이라 일자별 API로도 복구가 불가능합니다 — 그래서 그 잔여분만 실측된 활동량에
비례해 분배했습니다. 정확한 수치와 근거: [`data/overrides.json`](./data/overrides.json)

**추정인 부분.** 비용은 공개된 모델별 단가로 계산한 값이지 청구서가 아닙니다. 자릿수 감각으로만
보세요. 그래서 첫 화면에는 금액을 넣지 않았습니다.

**생성되는 부분.** 모든 SVG와 위 표는 [`scripts/build_assets.py`](./scripts/build_assets.py) 가
[`data/graph.json`](./data/graph.json) 을 읽어 씁니다. 이 README에 손으로 친 숫자는 없습니다.
데이터가 바뀌면 그림도 바뀝니다.

기계가 읽을 수 있는 형태: [`data/stats.json`](./data/stats.json) · [`data/graph.json`](./data/graph.json)

</details>

---

### 만들고 있는 것

| | |
|---|---|
| [**olli-interest-map**](https://github.com/inhodev/olli-interest-map) | 매주 꽂히는 게 바뀌어서, 아예 지도로 만든 관심맵 |
| [**safe_map**](https://github.com/inhodev/safe_map) | 인하대 안전지도 · D-UP contest |
| [**Library-of-Things**](https://github.com/inhodev/Library-of-Things) | 물건을 빌려 쓰는 도서관 · GDGoC × AZIT 해커톤 |
| [**copyvara-ai**](https://github.com/inhodev/copyvara-ai) · [**copyvara-fast**](https://github.com/inhodev/copyvara-fast) | Python 코어 + TypeScript 런타임 |
| [**insta-ripper**](https://github.com/inhodev/insta-ripper) | 로그인 없는 인스타 다운로더 |
| [**myBIBLE**](https://github.com/inhodev/myBIBLE) | 나만의 성경앱 |

<sub>Dart · TypeScript · Python · JavaScript — 그 주에 출시되는 걸로.</sub>

<br>

<sub><b>kiminho</b> · 인하대학교 · 인천<br>
위 그래프는 돈을 얼마나 썼는지 자랑하려는 게 아닙니다. 이 중 얼마나 많은 부분을 직접 타이핑하는 대신
에이전트를 몰아서 만들었는지에 대한 기록입니다.</sub>
