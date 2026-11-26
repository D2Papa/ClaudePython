# 전자식 차일드락 제어 SW 상세 설계서

| 항목 | 내용 |
|---|---|
| 문서 ID | SWD-001 |
| 상위 입력 | SWA-001 (BL-SWA-1.0), SWRS-001 (BL-SWR-1.0) |
| 기준선 | BL-SWD-1.0 |
| A-SPICE | SWE.3 SW 상세 설계 및 유닛 구성 |
| 상태 | 검토 반영본 (REV-G2-001 지적 반영) |

## 1. 소스 구조

```
src/child_lock/
├── __init__.py
├── types.py            # 공용 타입 (ASIL B)
├── engine.py           # 판정 코어 (ASIL B)
├── event_log.py        # 이벤트 기록 (QM)
├── replay.py           # 결정론 재생 (QM)
├── safety/             # ASIL B
│   ├── __init__.py
│   ├── validation.py
│   ├── freshness.py
│   ├── crash.py
│   ├── approach.py
│   └── arbiter.py
├── qm/                 # QM
│   ├── __init__.py
│   └── rules.py
└── web/                # QM
    ├── __init__.py
    ├── app.py
    └── static/index.html
```

## 2. 공용 타입 (`types.py`)

### 2.1 열거형

| 타입 | 값 | 비고 |
|---|---|---|
| `Lock(StrEnum)` | `LOCK`, `RELEASE` | |
| `Door(StrEnum)` | `LEFT="left"`, `RIGHT="right"` | 반복 순서 LEFT → RIGHT (동률 시 좌 우선) |
| `State(StrEnum)` | `OFF`, `DEGRADED`, `FAULT`, `OVERRIDE`, `NORMAL` | 선언 순서 = 표시 우선순위 (앞이 높음) |
| `Validity(StrEnum)` | `VALID`, `INVALID`, `STALE` | |
| `Group(StrEnum)` | `G1`, `G2`, `G3`, `G7`, `G8`, `G9` | SWRS 2.1 |
| `Reason(StrEnum)` | SWRS 2.3의 17개 코드 | |
| `Rule(IntEnum)` | 아래 표 | 값이 작을수록 우선 |

`Rule` 값과 SWRS 3.1 순위의 대응 (7a를 7보다 앞에 두려고 번호를 다시 매김):

| `Rule` | 값 | SWRS 순위 | 분류 |
|---|---|---|---|
| `IGNITION_OFF` | 1 | 1 | QM |
| `CRASH` | 2 | 2 | ASIL B |
| `EMERGENCY_RELEASE` | 3 | 3 | QM |
| `INPUT_STALE` | 4 | 4 | ASIL B |
| `SENSOR_FAULT` | 5 | 5 | ASIL B |
| `ISOFIX` | 6 | 6 | QM |
| `DRIVER_OVERRIDE` | 7 | 7a | ASIL B |
| `APPROACH_RISK` | 8 | 7 | ASIL B |
| `ADULT_RELEASE` | 9 | 8 | QM |
| `AUTO_LOCK` | 10 | 9 | QM |
| `DRIVER_COMMAND` | 11 | 10 | QM |
| `NO_CHANGE` | 12 | 11 | ASIL B |

`QM_RULES: frozenset[Rule]` = {IGNITION_OFF, EMERGENCY_RELEASE, ISOFIX, ADULT_RELEASE, AUTO_LOCK, DRIVER_COMMAND}.

`RULE_OUTPUT: Mapping[Rule, Lock | None]` — 규칙별 고정 출력 (`None` = 직전 유지). 중재기가 QM 후보의 출력이 이 표와 맞는지 검사한다 (SWA 5장). `DRIVER_COMMAND`는 명령에 따라 출력이 달라지므로 **표에 넣지 않고** `accept_qm`에서 예외로 처리한다.

| 규칙 | 출력 |
|---|---|
| `IGNITION_OFF`, `CRASH`, `EMERGENCY_RELEASE`, `DRIVER_OVERRIDE`, `ADULT_RELEASE` | `RELEASE` |
| `ISOFIX`, `APPROACH_RISK`, `AUTO_LOCK` | `LOCK` |
| `INPUT_STALE`, `SENSOR_FAULT`, `NO_CHANGE` | `None` (직전 유지) |

### 2.2 상수

| 이름 | 값 | 근거 |
|---|---|---|
| `STALE_AFTER_S` | 0.200 | SWR-013 (초과 시 지연) |
| `AUTO_LOCK_KPH` | 3.0 | SWR-003 (이상) |
| `OVERRIDE_WINDOW_S` | 10.0 | SWR-006 (이하) |
| `SPEED_MIN_KPH`, `SPEED_MAX_KPH` | 0.0, 300.0 | OEM-IF-001 |
| `ENGINE_PERIOD_S` | 0.050 | A-05 (호출자 참고값) |
| `EVENT_CAPACITY` | 100 | SWR-010 |
| `INITIAL_DECISION` | 양쪽 RELEASE, `OFF`, `NO_CHANGE`(규칙·이유 4개), `STALE`, 경고 None | SWRS 2.2 (CR-001) |

### 2.3 불변 데이터 구조 (`@dataclass(frozen=True)`)

| 타입 | 필드 |
|---|---|
| `Command` | `doors: frozenset[Door]`, `action: Lock` (`unlock`→RELEASE), `source: str` |
| `Values` | `speed_kph`, `gear`, `crash_status`, `risk: Mapping[Door,bool]`, `fire`, `overtemp`, `adult`, `isofix: Mapping[Door,bool]`, `ignition_on`, `sensor_fault` — 미수신은 `None` |
| `DoorApproach` | `t0: float \| None`, `override: bool` |
| `ControllerState` | `values: Values`, `group_ts: Mapping[Group,float]`, `last_ts: float \| None`, `crash_latched: bool`, `doors: Mapping[Door,DoorApproach]`, `outputs: Mapping[Door,Lock]` |
| `Intake` | `values`, `group_ts`, `last_ts`, `command: Command \| None`, `command_ts: float \| None`, `command_rejected: bool`, `input_rejected: bool` |
| `Context` | `now_s`, `values`, `stale: frozenset[Group]`, `command`, `command_rejected`, `input_rejected`, `crash_latched`, `doors`, `suppressed: frozenset[Door]` |
| `Candidate` | `rule: Rule`, `lock: Lock \| None` (None=직전 유지), `reason: Reason` |
| `Decision` | `lock_left`, `lock_right`, `state`, `priority_reason: str`, `reason_code`, `reason_left`, `reason_right`, `input_validity`, `warning_code: str \| None` |
| `StepResult` | `state: ControllerState`, `decision: Decision` |

## 3. 유닛 설계

각 함수는 순환 복잡도 10 이하, 순수 코드 50줄 이하로 설계한다. 표의 "복잡도"는 설계 시 추정치이며 Ruff `C901`로 확인한다.

### 3.1 `safety/validation.py` — SWR-013-1~3

| 함수 | 동작 | 복잡도 |
|---|---|---|
| `is_number(x) -> bool` | `int`/`float`이고 `bool`이 아니며 `math.isfinite(x)` (NaN·±inf 배제) | 3 |
| `check_timestamp(raw, last_ts) -> float \| None` | `source_timestamp_s` 누락·`is_number` 위반·음수·`last_ts` 미만이면 None, 아니면 값 | 4 |
| `parse_group(group, raw) -> dict \| None` | 그룹 필드 계약(SWRS 4.1 표) 검사. 위반·누락이면 None. 필드 계약은 모듈 상수 `GROUP_FIELDS: Mapping[Group, Mapping[str, Callable]]`로 표 형태 정의 | 3 |
| `parse_command(raw) -> tuple[Command \| None, bool]` | `command` 키 없음 → (None, False). 필드 누락·미등록 enum → (None, True). 정상 → (Command, False). `side=all` → 양쪽 도어 | 5 |
| `intake(state, raw) -> Intake` | raw가 None이면 상태 그대로, 명령 없음. 타임스탬프 불량이면 전체 거절(`input_rejected=True`) — **명령도 버린다** (`command=None`, `command_rejected=False`). 아니면 그룹별 `parse_group`, 수락 그룹만 값·`group_ts` 갱신, 하나라도 거절이면 `input_rejected=True`. 명령 파싱, `command_ts` = 스냅샷 타임스탬프 | 6 |

판정표 — 숫자 필드:

| 입력 | 결과 |
|---|---|
| `True`/`False` | 위반 (bool은 int 하위 형이므로 별도 배제) |
| `"3.0"` (문자열) | 위반 |
| `-0.1`, `300.1` | 위반 |
| `0`, `0.0`, `300`, `300.0` | 수락 |
| `float("nan")`, `float("inf")`, `float("-inf")` | 위반 (타임스탬프·차속·Web `now_s` 공통) |

### 3.2 `safety/freshness.py` — SWR-013-4·5

| 함수 | 동작 | 복잡도 |
|---|---|---|
| `stale_groups(group_ts, now_s) -> frozenset[Group]` | 모든 `Group`에 대해 `group_ts`에 없거나 `now_s - ts > STALE_AFTER_S`이면 포함 | 3 |

경계: `now_s - ts == 0.200` → 신선. 부동소수 오차를 피하기 위해 비교 전 `round(now_s - ts, 9)`를 쓴다.

### 3.3 `safety/crash.py` — SWR-007, 008

| 함수 | 동작 | 복잡도 |
|---|---|---|
| `ignition_off(values, stale) -> bool` | G9 신선이고 `ignition_on is False` | 2 |
| `update_latch(latched, values, stale) -> bool` | 시동 OFF → False. G2 신선이고 `CONFIRMED` → True. 그 외 `latched` | 3 |
| `crash_candidate(latched) -> Candidate \| None` | 래치면 `(CRASH, RELEASE, CRASH_RELEASE)` | 1 |
| `crash_pending(values, stale) -> bool` | G2 신선이고 `PENDING` (3.2 매핑용) | 2 |

### 3.4 `safety/approach.py` — SWR-005, 006, 009

도어마다 독립 계산 (SWR-009).

| 함수 | 동작 | 복잡도 |
|---|---|---|
| `unlock_requested(command, door) -> bool` | 명령이 있고 `action=RELEASE`이고 `door in command.doors` | 3 |
| `update_door(prev, risk, speed, unlock, t) -> tuple[DoorApproach, bool]` | 아래 판정표. 반환 (새 상태, 억제 여부) | 6 |
| `update_doors(prev_doors, intake, stale, ignition_off) -> tuple[Mapping[Door, DoorApproach], frozenset[Door]]` | 시동 OFF, 지연 그룹 있음, 또는 `sensor_fault is True` → 모든 도어 초기화(`t0=None`, `override=False`), 억제 없음 (SWR-006-5, A-21: 지연·고장 값으로 새 판정을 하지 않고 기존 override도 보수적으로 끝냄). 아니면 도어별 `update_door` | 4 |
| `approach_candidate(ctx, door) -> Candidate \| None` | 접근위험 FALSE·미수신이면 None. override면 `(DRIVER_OVERRIDE, RELEASE, DRIVER_OVERRIDE)`, 아니면 `(APPROACH_RISK, LOCK, SUPPRESSED 또는 LOCK)` | 3 |

`update_door` 판정표 (`t` = 명령 스냅샷 시각, `moving` = speed ≥ 3.0):

| risk | moving | prev.override | unlock | t0 조건 | 새 t0 | 새 override | 억제 |
|---|---|---|---|---|---|---|---|
| FALSE/None | — | — | — | — | None | False | 아니오 |
| TRUE | 예 | — | 아니오 | — | None | False | 아니오 |
| TRUE | 예 | — | 예 | — | None | False | 예 |
| TRUE | 아니오 | True | — | — | 유지 | True | 아니오 |
| TRUE | 아니오 | False | 아니오 | — | 유지 | False | 아니오 |
| TRUE | 아니오 | False | 예 | t0 None 또는 `t − t0 > 10.0` | t | False | 예 |
| TRUE | 아니오 | False | 예 | `t − t0 ≤ 10.0` | 유지 | True | 아니오 |

주행 중 억제는 t0를 기록하지 않는다 (주행 중 override 불가, SWR-006-5). `t − t0` 비교도 `round(…, 9)`를 쓴다.

### 3.5 `qm/rules.py` — SWR-001~004, 017, 018, 020

| 함수 | 후보 | 복잡도 |
|---|---|---|
| `ignition_candidate(ctx)` | G9 신선, `ignition_on is False` → `(IGNITION_OFF, RELEASE, IGNITION_OFF)` | 2 |
| `emergency_candidate(ctx)` | G7 신선, `fire is True` → `FIRE_RELEASE`, `overtemp is True` → `OVERTEMP_RELEASE` (RELEASE) | 3 |
| `isofix_candidate(ctx, door)` | `isofix`가 None이 아니고 `isofix[door] is True` → `(ISOFIX, LOCK, ISOFIX_LOCK)` | 2 |
| `adult_candidate(ctx)` | `adult is True` → `(ADULT_RELEASE, RELEASE, ADULT_RELEASE)` | 1 |
| `auto_lock_candidate(ctx)` | `speed_kph`가 None이 아니고 `≥ 3.0` → `(AUTO_LOCK, LOCK, AUTO_LOCK_SPEED)` | 2 |
| `driver_candidate(ctx, door)` | `command`가 None이 아니고 `door in command.doors` → `(DRIVER_COMMAND, command.action, DRIVER_COMMAND)` | 2 |
| `qm_candidates(ctx, door) -> list[Candidate]` | 위 결과 중 None이 아닌 것 | 2 |

**미수신 값 처리**: `Values`의 미수신 필드는 `None`이다. 모든 후보 함수는 값이 `None`이면 후보를 만들지 않는다 (`is True` 비교, `None` 검사). 초기 상태에서 스냅샷 없이 평가해도 예외 없이 DEGRADED/`INPUT_STALE` 결정이 나와야 한다 — 단위 시험으로 확인한다.

QM 규칙은 지연·고장 여부를 보지 않는다. 지연·고장 시의 차단은 ASIL B 중재기가 우선순위로 보장한다 (QM 규칙의 판단에 의존하지 않음).

### 3.6 `safety/arbiter.py` — SWR-013-4, 021, 022

| 함수 | 동작 | 복잡도 |
|---|---|---|
| `safety_candidates(ctx, door) -> list[Candidate]` | 충돌(래치), 지연(`stale` 비어있지 않음 → `(INPUT_STALE, None, INPUT_STALE)`), 고장(G9 `sensor_fault is True` → `(SENSOR_FAULT, None, SENSOR_FAULT)`), 접근위험 후보 | 4 |
| `accept_qm(candidate, ctx, door) -> bool` | 1) `rule in QM_RULES` 2) 출력 검사: `DRIVER_COMMAND`는 `lock`이 `Lock`이면 허용, 그 외는 `lock == RULE_OUTPUT[rule]` 3) `qm_plausible` 호출. 하나라도 어긋나면 False (SWA 5장) | 4 |
| `qm_plausible(candidate, ctx, door) -> bool` | ASIL B 규칙보다 우선하는 QM 규칙의 조건을 `ctx`로 직접 재확인: `IGNITION_OFF` → `crash.ignition_off(values, stale)`, `EMERGENCY_RELEASE` → G7 신선·(`fire is True` 또는 `overtemp is True`), `ISOFIX` → `isofix is not None`·`isofix[door] is True`. 그 밖의 규칙은 True. 미수신 값에서도 예외를 던지지 않는다 | 5 |

**한계**: 중재기는 QM 후보의 출력은 검증하지만 이유 코드(예: `EMERGENCY_RELEASE`의 `FIRE_RELEASE`/`OVERTEMP_RELEASE` 구분)는 검증하지 않는다. 이유 코드 오류는 출력 안전에 영향이 없으므로 수용한다.
| `no_change_reason(ctx) -> Reason` | SWRS 3.2: `INPUT_INVALID` → `COMMAND_REJECTED` → `CRASH_PENDING` → `NO_CHANGE` | 4 |
| `pick(candidates) -> Candidate` | `rule` 값이 가장 작은 후보. 후보가 없으면 `(NO_CHANGE, None, no_change_reason)` | 2 |
| `door_state(rule, ctx) -> State` | IGNITION_OFF→OFF, INPUT_STALE→DEGRADED, SENSOR_FAULT→FAULT, DRIVER_OVERRIDE→OVERRIDE, CRASH·EMERGENCY_RELEASE→표시 규칙(지연→DEGRADED, 고장→FAULT, 아니면 NORMAL), 그 외 NORMAL | 6 |
| `validity(ctx) -> Validity` | 지연 → STALE, `input_rejected` → INVALID, 아니면 VALID | 2 |
| `decide(ctx, qm_by_door, previous) -> Decision` | 도어별 `pick(safety + accepted qm)`, 출력 = `lock` 또는 `previous[door]`. state = 두 도어 state 중 `State` 선언 순서상 앞선 것. priority_reason = `rule` 값이 작은 도어(동률 LEFT)의 규칙명, reason_code = 그 도어 reason. warning = G9 신선하고 `sensor_fault is True`이면 `W_SENSOR_FAULT` | 5 |

### 3.7 `engine.py` — SWR-016, 022

| 함수 | 동작 | 복잡도 |
|---|---|---|
| `initial_state() -> ControllerState` | 값 전부 None, `group_ts` 빈 매핑, `last_ts=None`, 래치 False, 도어 초기, 출력 양쪽 RELEASE | 1 |
| `evaluate(state, now_s, raw) -> StepResult` | 1) `intake` 2) `stale_groups` 3) `ignition_off` 4) `update_latch` 5) `update_doors` 6) `Context` 생성 (래치·도어 갱신 **후**) 7) 도어별 `qm_candidates` 8) `decide` 9) 새 `ControllerState` 조립 | 1 |

`evaluate`는 전역 상태·실제 시계·난수를 쓰지 않는다 (SWR-016).

### 3.8 `event_log.py` — SWR-010, 011, 012

| 요소 | 동작 | 복잡도 |
|---|---|---|
| `Event` (frozen dataclass) | SWR-011의 11개 필드만 | — |
| `EventLog.__init__(capacity=100)` | `deque(maxlen=capacity)`, `next_id = 1` | 1 |
| `EventLog.append(decision, now_s) -> Event` | `Decision`의 필드를 명시적으로 복사해 `Event` 생성 (입력 스냅샷은 받지 않으므로 허용 외 필드가 섞일 수 없음), `next_id` 증가 | 1 |
| `EventLog.events() -> list[Event]` | 오래된 것부터 | 1 |

파일·DB 접근 코드는 없다. 재기동 시 새 `EventLog`가 만들어진다 (SWR-012).

### 3.9 `replay.py` — SWR-016

| 함수 | 동작 | 복잡도 |
|---|---|---|
| `replay(vector) -> list[Decision]` | `vector`는 `[{"now_s":…, "snapshot":…}]`. `initial_state()`부터 차례로 `evaluate` | 2 |
| `digest(decisions) -> str` | `asdict` → `json.dumps(sort_keys=True, ensure_ascii=False)` → SHA-256 hex | 1 |

### 3.10 `web/app.py` — SWR-014, 015

| 요소 | 동작 | 복잡도 |
|---|---|---|
| `create_app(serialize=decision_json) -> FastAPI` | 앱마다 `ControllerState`, `EventLog`, 마지막 `Decision`, `threading.Lock` 보유. `serialize`는 직렬화 실패 시험 주입용 | 2 |
| `decision_json(decision) -> dict` | SWR-014의 9개 필드 | 1 |
| `POST /api/step` | `now_s`가 유한한 숫자인지 검사(`validation.is_number`, 아니면 422), 잠금 안에서 `evaluate` → `append` → 응답 | 3 |
| `GET /api/status` | 마지막 결정 직렬화. 평가 전이면 `INITIAL_DECISION` (SWRS 2.2: 양쪽 RELEASE, OFF, 이유 전부 NO_CHANGE, STALE, 경고 없음) | 2 |
| `GET /api/events` | 이벤트 목록 | 1 |
| 직렬화 오류 처리 | `serialize` 호출을 `try`로 감싸 `TypeError`·`ValueError` → HTTP 500 `{"error": "serialization_failed"}` | — |
| `GET /` | `static/index.html` | 1 |

`static/index.html`: 입력 폼(SWRS 4.1 필드, 운전자 명령), `now_s` 입력과 "+50 ms" 버튼, 상태 표(9개 필드), 이벤트 표. 외부 스크립트 없이 `fetch`만 사용.

## 4. 오류 처리 원칙

| 상황 | 처리 |
|---|---|
| 입력 형식·범위 오류 | 예외를 던지지 않고 값으로 처리 (그룹 거절, `input_validity`) |
| 코어 내부의 예상 못한 예외 | 잡지 않는다 — 시험에서 드러나게 한다. Web 계층에서만 HTTP 500으로 변환 |
| Web 요청 본문 오류 | HTTP 422 |

## 5. 단위 시험 설계 방침

- 유닛별 시험 파일: `tests/unit/test_<모듈>.py`. 기대값은 SWRS 수용기준의 리터럴 값으로 직접 쓴다.
- 경계값: 0.200/0.250 s, 2.9/3.0 km/h, 10.0/10.1 s, 0.0/300.0/−0.1/300.1 km/h.
- 동치 클래스: 그룹별 유효/무효(형식·범위·누락), 명령 source 4종·side 3종·action 2종.
- 판정표(3.4 `update_door`, 3.6 `door_state`)는 행마다 시험 하나.
- 결함 주입: `accept_qm`에 규칙·출력이 맞지 않는 후보(예: `(ISOFIX, RELEASE)`), 조건이 거짓인 후보(예: G9 신선·`ignition_on=TRUE`에서 `IGNITION_OFF`), 값이 미수신인 후보(예: G8 미수신에서 `(ISOFIX, LOCK)`)를 넣어 예외 없이 버려지는지 확인한다.
- 초기 상태·미수신 값: `initial_state()`에서 스냅샷 없이 평가 → 예외 없이 DEGRADED.
- 비유한 값: NaN·inf 타임스탬프·차속 거절.
- 아키텍처 시험(`tests/unit/test_architecture.py`): SWA 2.2 의존 규칙을 import 분석으로 검사.
- 통합 시험(`tests/integration/`): `engine` + `event_log` + `web` (TestClient), SWRS 3.1 규칙 쌍 조합.

## 6. 추적성: 컴포넌트 → 유닛 → SWR

| 유닛 | SWR |
|---|---|
| `types` | 022 |
| `safety.validation` | 013 |
| `safety.freshness` | 013 |
| `safety.crash` | 007, 008, 020 (래치 초기화) |
| `safety.approach` | 005, 006, 009, 020 (override 초기화) |
| `safety.arbiter` | 004, 008, 013, 021, 022 |
| `qm.rules` | 001, 002, 003, 004, 017, 018, 020 |
| `engine` | 016, 022 |
| `event_log` | 010, 011, 012 |
| `replay` | 016 |
| `web.app`, `web.static` | 014, 015 |

SWR 21건 모두 하나 이상의 유닛에 할당되었다.
