<!-- IMAGES:START -->

<img src="./assets/hero.svg?v=48ba0e1bf3" alt="총 소비한 AI 토큰, 추정치가 아니라 직접 센 값" width="100%">

<img src="./assets/skyline.svg?v=50cbad3f88" alt="토큰 스카이라인, 탑 하나가 하루" width="100%">

<img src="./assets/hud.svg?v=1f453d111f" alt="런타임별 분포와 월별 소비량" width="100%">

<!-- IMAGES:END -->

<!-- STATS:START -->

| | |
|---|---|
| 기간 | `2026-01-07 → 2026-08-05` · 138일 중 **138일 활동** |
| 총 토큰 | **34,004,134,923** (340억) |
| 메시지 | 246,787 |
| 세션 | 10,511 |
| 에이전트 가동시간 | 2,134시간 · 달력으로는 138일인데 실제 연산은 **약 89일치** |
| 최장 연속 가동 | 146.7시간 |
| 최대 동시 세션 | 22개 |
| 가장 많이 쓴 날 | `2026-05-25` · 24억 |
| 모델 / 런타임 | 45종 / 7개 |
| Codex 실측 커버리지 | **96.53%** · 공식 집계 29,070,000,000 중 28,062,310,711을 로컬 로그에서 날짜별로 복원했다 |

<sub>이 표는 <code>scripts/build_assets.py</code>가 만든다. 직접 고쳐도 다음 빌드에 덮어쓴다.</sub>

<!-- STATS:END -->

<br>

> **뱃지야 누구나 붙인다. 이건 직접 돌려서 확인할 수 있다.**
> 이 저장소를 받아서 `bash scripts/refresh.sh` 한 줄만 실행하면 위 그림이 전부
> 내 컴퓨터의 세션 로그에서 새로 그려진다. 생성기는 외부 라이브러리 하나 안 쓰는 파이썬 스크립트다.

<details>
<summary><b>이 숫자는 어떻게 나왔나, 그리고 어디부터 정확하지 않나</b></summary>

<br>

```bash
bash scripts/refresh.sh    # 에이전트 기록 전부 스캔 → 병합 → 이미지 재생성
```

**직접 센 부분.** 세션 로그에 남은 메시지별 토큰 수를 그대로 읽었다. 입력, 출력, 캐시 읽기,
캐시 쓰기를 따로 세서 합쳤다. 두 디렉터리에 흩어진 Codex 롤아웃 파일 6,872개, Claude Code
대화 기록 496개, 여기에 OpenCode와 Hermes, Kilo, Gajae-Code, Antigravity 기록까지 훑었다.
디렉터리끼리 세션 ID가 겹치지 않아서 같은 세션을 두 번 세는 일은 없다.

**보정한 부분.** OpenAI가 집계한 두 계정 누적치는 290.7억이다. 로컬 로그만으로 그중
**96.53%** 를 날짜별로 되살렸다. 나머지 3.47% 는 원본이 남아 있지 않다. 스캔하기 전에 정리된
세션이라 어디서도 날짜별로 복구할 방법이 없어서, 그 몫만 실제로 센 활동량에 비례해 나눠 넣었다.
수치와 근거는 [`data/overrides.json`](./data/overrides.json) 에 적어뒀다.

**추정인 부분.** 비용은 공개된 모델별 단가로 계산한 값이지 청구서가 아니다. 자릿수만 참고하면
된다. 그래서 첫 화면에는 금액을 넣지 않았다.

**자동으로 만들어지는 부분.** 위 그림과 표는 [`scripts/build_assets.py`](./scripts/build_assets.py) 가
[`data/graph.json`](./data/graph.json) 을 읽어서 쓴다. 이 문서에 손으로 친 숫자는 하나도 없다.
데이터가 바뀌면 그림도 따라 바뀐다.

원본 데이터: [`data/stats.json`](./data/stats.json) · [`data/graph.json`](./data/graph.json)

</details>

---

### 만들고 있는 것

| | |
|---|---|
| [**olli-interest-map**](https://github.com/inhodev/olli-interest-map) | 매주 꽂히는 게 바뀌어서 아예 지도로 만든 관심맵 |
| [**safe_map**](https://github.com/inhodev/safe_map) | 인하대 안전지도 · D-UP contest |
| [**Library-of-Things**](https://github.com/inhodev/Library-of-Things) | 물건을 빌려 쓰는 도서관 · GDGoC × AZIT 해커톤 |
| [**copyvara-ai**](https://github.com/inhodev/copyvara-ai) · [**copyvara-fast**](https://github.com/inhodev/copyvara-fast) | Python 코어 + TypeScript 런타임 |
| [**insta-ripper**](https://github.com/inhodev/insta-ripper) | 로그인 없이 쓰는 인스타 다운로더 |
| [**myBIBLE**](https://github.com/inhodev/myBIBLE) | 나만의 성경앱 |

<sub>Dart · TypeScript · Python · JavaScript — 그때그때 제일 빨리 내놓을 수 있는 걸로 쓴다.</sub>

<br>

<sub><b>kiminho</b> · 인하대학교 · 인천<br>
위 그래프는 돈을 얼마나 썼는지 자랑하려고 올린 게 아니다. 직접 타이핑하는 대신 에이전트를 굴려서
만든 분량이 얼마나 되는지 남겨둔 기록이다.</sub>
