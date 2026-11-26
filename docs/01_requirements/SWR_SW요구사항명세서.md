# 전자식 차일드락 제어 SW 요구사항 명세서

| 항목 | 내용 |
|---|---|
| 문서 ID | SWRS-001 |
| 상위 입력 | OEM-SWR-001 OEM SW 요구사항 사양서 Rev 1.0 (BL-OEM-1.0) |
| 기준선 | BL-SWR-1.0 |
| A-SPICE | SWE.1 SW 요구사항 분석 |
| 상태 | 검토 반영본 (REV-G1-001 지적 10건 반영) |

## 1. 목적과 범위

OEM-A 요구사항(OEM-SR/FR/NFR)과 외부 인터페이스 계약(OEM-IF)으로부터 검증 가능한 SW 요구사항(SWR)을 도출한다. 범위는 PC/SIL 참조 구현과 Web 시뮬레이터이며, HW·HIL·실차·인증은 제외한다 (개발계획서 1장).

## 2. 공통 정의

### 2.1 시간 모델

| 용어 | 정의 |
|---|---|
| 평가 주기 | SW가 판정을 수행하는 주기. 50 ms, 설정으로 변경 가능 **[가정 A-05]** |
| 평가 시각 `now_s` | 평가 시점의 시계 값. 시계는 외부에서 주입한다 (SWR-016) |
| 입력 스냅샷 | 한 시점의 차량 입력과 선택적 운전자 명령의 묶음. `source_timestamp_s`(OEM-IF-001)를 가진다 |
| 입력 그룹 | 검증·신선도 판정 단위. G1=OEM-IF-001(차속·기어), G2=IF-002(충돌), G3=IF-003(접근위험), G7=IF-007(화재·과온·성인), G8=IF-008(ISOFIX), G9=IF-009(시동·센서 고장). 운전자 명령(IF-004)은 그룹이 아니라 이벤트다 |
| 그룹 갱신 시각 | 그룹 값이 마지막으로 수락된 스냅샷의 `source_timestamp_s` |
| 신선한 그룹 | `now_s − 그룹 갱신 시각 ≤ 0.200 s`인 그룹 |
| 반영 주기 | 어떤 입력 변화를 처음 포함한 스냅샷을 평가한 주기. OEM 수용기준의 "다음 평가주기", "첫 평가주기"는 반영 주기를 뜻한다 |

새 스냅샷이 없는 주기에도 평가를 수행한다. 각 규칙은 **마지막으로 수락된 그룹 값**으로 판정한다.

### 2.2 출력 모델

| 출력 | 값 | 설명 |
|---|---|---|
| `lock_left`, `lock_right` | `LOCK` / `RELEASE` | 도어별 논리 차일드락 명령 (OEM-IF-005) |
| `state` | `OFF` / `NORMAL` / `OVERRIDE` / `DEGRADED` / `FAULT` | SW 상태 (OEM-IF-006). 두 도어의 결정 규칙이 서로 다른 state를 내면 `OFF > DEGRADED > FAULT > OVERRIDE > NORMAL` 순으로 높은 것을 쓴다 |
| `reason_left`, `reason_right` | 2.3 이유 코드 | 도어별 출력을 결정한 이유 **[가정 A-20]** |
| `priority_reason` | 3장 규칙명 | 두 도어의 결정 규칙 중 우선순위가 더 높은 규칙 (같으면 좌 도어) (OEM-IF-006) |
| `reason_code` | 2.3 이유 코드 | `priority_reason`을 낸 도어의 이유 코드 (3.2 매핑) (OEM-IF-006) |
| `input_validity` | `VALID` / `INVALID` / `STALE` | 신선하지 않은 그룹이 있으면 `STALE`, 아니면 이번 주기에 거절된 그룹·스냅샷이 있으면 `INVALID`, 아니면 `VALID` |
| `warning_code` | `W_SENSOR_FAULT` / 없음 | 센서 고장 경고 (SWR-021) |

도어별 출력은 매 주기 **활성 규칙 중 우선순위가 가장 높은 규칙**이 정한다. 활성 규칙이 없으면 직전 출력을 유지한다. 운전자 명령은 해당 스냅샷의 주기에만 활성인 이벤트이고, 나머지 규칙은 조건이 참인 동안 활성이다.

**초기 상태**: 시작 시 두 출력은 `RELEASE`, `state`는 `OFF`, 모든 그룹은 미수신(신선하지 않음)이다.

### 2.3 이유 코드

| 코드 | 의미 | 정의 SWR |
|---|---|---|
| `IGNITION_OFF` | 시동 꺼짐 | SWR-020 |
| `CRASH_RELEASE` | 충돌 확정 긴급 해제 | SWR-007 |
| `CRASH_PENDING` | 충돌 판정 대기 (출력 변경 없음) | SWR-008 |
| `FIRE_RELEASE` | 화재 강제 해제 | SWR-017 |
| `OVERTEMP_RELEASE` | 과온 강제 해제 | SWR-017 |
| `INPUT_STALE` | 필수 입력 갱신 지연 (DEGRADED) | SWR-013 |
| `SENSOR_FAULT` | 센서 고장으로 출력 유지 | SWR-021 |
| `ISOFIX_LOCK` | ISOFIX 강제 잠금 | SWR-018 |
| `APPROACH_RISK_LOCK` | 접근위험 잠금 | SWR-005 |
| `APPROACH_RISK_SUPPRESSED` | 접근위험으로 해제 요청 억제 | SWR-005 |
| `DRIVER_OVERRIDE` | 접근위험 경고 후 운전자 재입력으로 해제 | SWR-006 |
| `ADULT_RELEASE` | 성인 탑승 강제 해제 | SWR-017 |
| `AUTO_LOCK_SPEED` | 주행 자동 잠금 (주행 중 해제 거절 포함) | SWR-003, SWR-004 |
| `DRIVER_COMMAND` | 운전자 명령 적용 | SWR-001, SWR-002 |
| `INPUT_INVALID` | 입력 그룹·스냅샷 형식·범위 오류로 거절 | SWR-013 |
| `COMMAND_REJECTED` | 운전자 명령 형식 오류로 거절 | SWR-013 |
| `NO_CHANGE` | 활성 규칙 없음, 직전 출력 유지 | SWR-022 |

## 3. 우선순위 중재 (SWR-022의 상세)

### 3.1 우선순위 표

**위에 있을수록 우선**이며 도어별로 적용한다. "신선"은 2.1의 신선한 그룹을 뜻한다.

| 순위 | 규칙명 (`priority_reason`) | 조건 | 도어 출력 | state | 근거 |
|---|---|---|---|---|---|
| 1 | `IGNITION_OFF` | G9 신선, `ignition_on = FALSE` | 양쪽 RELEASE | OFF | FR-007, A-14 |
| 2 | `CRASH` | G2 신선하고 `CONFIRMED`, 또는 충돌 래치 | 양쪽 RELEASE | 표시 규칙¹ | SR-001, A-03, A-04, A-15 |
| 3 | `EMERGENCY_RELEASE` | G7 신선, 화재 또는 과온 TRUE | 양쪽 RELEASE | 표시 규칙¹ | FR-005, A-01, A-08 |
| 4 | `INPUT_STALE` | 신선하지 않은 그룹이 하나라도 있음 | 직전 유지 | DEGRADED | SR-003, A-12 |
| 5 | `SENSOR_FAULT` | `sensor_fault = TRUE` | 직전 유지 | FAULT | SR-004, A-18 |
| 6 | `ISOFIX` | 해당 도어 ISOFIX TRUE | 해당 도어 LOCK | NORMAL | FR-006, A-01 |
| 7 | `APPROACH_RISK` | 해당 도어 접근위험 TRUE, override 미성립 | 해당 도어 LOCK | NORMAL | SR-002 |
| 7a | `DRIVER_OVERRIDE` | 해당 도어 접근위험 TRUE, override 유지 중, 차속 < 3.0 km/h (SWR-006) | 해당 도어 RELEASE | OVERRIDE | FR-003, A-02, A-11, A-13 |
| 8 | `ADULT_RELEASE` | 성인 탑승 TRUE | 양쪽 RELEASE | NORMAL | FR-005, A-01 |
| 9 | `AUTO_LOCK` | 차속 ≥ 3.0 km/h | 양쪽 LOCK | NORMAL | FR-002, A-13 |
| 10 | `DRIVER_COMMAND` | 유효한 운전자 명령 | 선택 도어에 명령 적용 | NORMAL | FR-001 |
| 11 | `NO_CHANGE` | 해당 없음 | 직전 유지 | NORMAL | — |

¹ 표시 규칙: 순위 2·3이 출력을 정해도 `state`는 고장·지연을 숨기지 않는다. 신선하지 않은 그룹이 있으면 DEGRADED, 아니면 `sensor_fault = TRUE`이면 FAULT, 아니면 NORMAL. 순위 1(시동 OFF)이 활성이면 다른 그룹이 지연되어도 `state = OFF`이다 — 시동 OFF 중에는 차량 신호가 끊기는 것이 정상이기 때문이다 **[가정 A-14]**.

순위 비교에서 7a는 7보다 높다 (7a는 7의 예외이다).

순위 1~3은 자기 입력 그룹이 신선할 때만 활성이다. 순위 4가 활성이면 순위 5~10은 평가하지 않는다. 즉 지연된(stale) 값으로 고장·잠금·해제를 판정하지 않는다.

### 3.2 `priority_reason` → `reason_code` 매핑

| `priority_reason` | `reason_code` |
|---|---|
| `IGNITION_OFF` | `IGNITION_OFF` |
| `CRASH` | `CRASH_RELEASE` |
| `EMERGENCY_RELEASE` | 화재 TRUE이면 `FIRE_RELEASE`, 아니면 `OVERTEMP_RELEASE` |
| `INPUT_STALE` | `INPUT_STALE` |
| `SENSOR_FAULT` | `SENSOR_FAULT` |
| `ISOFIX` | `ISOFIX_LOCK` |
| `APPROACH_RISK` | 이번 주기에 해당 도어 해제 요청이 억제되었으면 `APPROACH_RISK_SUPPRESSED`, 아니면 `APPROACH_RISK_LOCK` |
| `DRIVER_OVERRIDE` | `DRIVER_OVERRIDE` |
| `ADULT_RELEASE` | `ADULT_RELEASE` |
| `AUTO_LOCK` | `AUTO_LOCK_SPEED` |
| `DRIVER_COMMAND` | `DRIVER_COMMAND` |
| `NO_CHANGE` | 아래 중 처음 해당하는 것: `INPUT_INVALID`(이번 주기 거절 있음) → `COMMAND_REJECTED`(명령 거절) → `CRASH_PENDING`(G2 신선, PENDING) → `NO_CHANGE` |

## 4. SW 요구사항

표기: **[가정 A-xx]**는 OEM 확인 전 작업 가정에 의존한다 (개발계획서 5장). 검증 수준: U=단위, I=통합, S=SW 검증(PC/SIL), W=Web.

### 4.1 입력 검증 (ASIL B)

#### SWR-013 입력 유효성·신선도 확인
- **분류**: ASIL B · **출처**: OEM-SR-003, OEM-IF-001~004, 007~009 · **검증**: U, S
- **요구사항**:
  1. `source_timestamp_s`가 누락·형식 오류(실수 아님, 불리언), 음수, 또는 직전에 수락된 스냅샷보다 이르면 스냅샷 전체를 평가 전에 거절한다 **[가정 A-16]**.
  2. 그렇지 않으면 입력 그룹별로 아래 계약을 검사한다. 위반한 그룹은 **그 그룹만** 거절하고(값과 그룹 갱신 시각 불변), 나머지 그룹은 수락한다 **[가정 A-19]**. 필드 누락도 위반이다.

     | 그룹 | 필드 | 형식 | 유효 범위 |
     |---|---|---|---|
     | G1 | `vehicle_speed_kph` | 실수 (불리언 불가) | 0.0 ~ 300.0 (양 끝 포함) |
     | G1 | `gear` | 문자열 | `P`, `N`, `D`, `R` (판정에 쓰지 않음, A-09) |
     | G2 | `crash_status` | 문자열 | `NONE`, `PENDING`, `CONFIRMED` |
     | G3 | `rear_left_approach_risk`, `rear_right_approach_risk` | 불리언 | TRUE/FALSE |
     | G7 | `fire_detected`, `overtemperature_detected`, `adult_present` | 불리언 | TRUE/FALSE |
     | G8 | `isofix_left`, `isofix_right` | 불리언 | TRUE/FALSE |
     | G9 | `ignition_on`, `sensor_fault` | 불리언 | TRUE/FALSE |

  3. 운전자 명령(OEM-IF-004)이 형식 위반(필드 누락, 미등록 enum)이면 **명령만 거절**하고 차량 입력은 평가한다 (이유 코드는 3.2 매핑) **[가정 A-16]**.
  4. 매 평가 주기에, 새 스냅샷의 수락·거절과 무관하게 신선도를 판정한다. 신선하지 않은 그룹이 하나라도 있으면 그 주기에 `state = DEGRADED`, `input_validity = STALE`이고 출력은 직전 값을 유지한다 (3.1 순위 1~3 예외) **[가정 A-12]**.
  5. 모든 그룹이 다시 신선해지는 주기에 DEGRADED를 벗어난다. 갱신 시각이 그대로인 재전송은 신선도를 회복하지 않는다.
- **수용기준** (평가 주기 50 ms 기준 **[가정 A-05]**):
  - 그룹 갱신 지연 0.200 s인 주기는 DEGRADED가 아니고, 0.250 s 주기는 DEGRADED다. 200 ms 초과 후 100 ms 이내 전환을 충족한다.
  - 형식 오류 스냅샷이 매 주기 연속으로 와도 마지막 수락 후 0.250 s 주기에 DEGRADED가 된다.
  - G1 범위 오류(차속 300.1)와 G2 `CONFIRMED`가 함께 오면 G1만 거절되고 충돌 해제는 적용된다.

### 4.2 충돌 (ASIL B)

#### SWR-007 충돌 확정 시 긴급 해제
- **분류**: ASIL B · **출처**: OEM-SR-001, OEM-IF-002 · **검증**: U, S
- **요구사항**: G2가 수락되고 `crash_status = CONFIRMED`인 반영 주기에 SW는 두 출력을 `RELEASE`, 이유 코드를 `CRASH_RELEASE`로 해야 한다. 이 규칙은 3.1 순위 2로서 순위 3~11의 모든 규칙보다 우선한다 **[가정 A-03, A-04]**. 충돌이 한 번 확정되면 이후 `crash_status`가 바뀌거나 G2가 신선하지 않아도 시동 OFF(SWR-020)까지 해제를 유지한다(충돌 래치) **[가정 A-15]**.
- **수용기준**: CONFIRMED 반영 주기에 양쪽 RELEASE (평가 주기 50 ms이므로 300 ms 이내 **[가정 A-05]**). 이후 `NONE`, 접근위험 TRUE, ISOFIX TRUE, 운전자 LOCK, sensor_fault TRUE, 입력 지연이 와도 RELEASE 유지. `ignition_on = FALSE` 반영 주기에 래치 해제.

#### SWR-008 충돌 판정 대기 처리
- **분류**: ASIL B · **출처**: OEM-SR-001, OEM-IF-002 · **검증**: U, S
- **요구사항**: `crash_status = PENDING`은 출력을 바꾸지 않는다. 도어 결정 규칙이 `NO_CHANGE`인 주기에는 3.2 매핑에 따라 `CRASH_PENDING`을 제공한다 **[가정 A-06]**.
- **수용기준**: 양쪽 LOCK, 다른 규칙 비활성에서 PENDING 입력 → 양쪽 LOCK 유지, `CRASH_PENDING`.

### 4.3 센서 고장 (ASIL B)

#### SWR-021 센서 고장 시 출력 유지
- **분류**: ASIL B · **출처**: OEM-SR-004, OEM-IF-009 · **검증**: U, S
- **요구사항**: `sensor_fault = TRUE`인 반영 주기부터 SW는 3.1 순위 6~11 규칙(운전자 명령 포함)을 적용하지 않고 직전 확정 출력을 유지하며, `state = FAULT`, 이유 코드 `SENSOR_FAULT`, `warning_code = W_SENSOR_FAULT`를 제공해야 한다. 순위 1~3(시동 OFF, 충돌, 화재·과온)은 예외로 적용한다 **[가정 A-03, A-18]**. `sensor_fault = FALSE`가 수락되면 FAULT를 벗어난다.
- **수용기준**: 좌 LOCK/우 RELEASE에서 sensor_fault TRUE + 운전자 ALL LOCK → 좌 LOCK/우 RELEASE 유지, FAULT, W_SENSOR_FAULT. sensor_fault TRUE + 화재 TRUE → 양쪽 RELEASE, state FAULT.

### 4.4 접근위험 (ASIL B)

#### SWR-005 접근위험 도어 잠금과 해제 억제
- **분류**: ASIL B · **출처**: OEM-SR-002, OEM-IF-003 · **검증**: U, S
- **요구사항**: 도어별 접근위험이 TRUE인 동안 해당 도어 출력은 `LOCK`이어야 한다. 해당 도어에 대한 해제 요청은 억제하고, 그 도어의 이유 코드(`reason_left`/`reason_right`)를 `APPROACH_RISK_SUPPRESSED`로 기록한다 (그 외 주기는 `APPROACH_RISK_LOCK`) **[가정 A-20]**. 억제 시각은 override 판정(SWR-006)의 기산점이 된다.
- **수용기준**: 좌 접근위험 TRUE → 좌 LOCK, `reason_left = APPROACH_RISK_LOCK`. 좌 unlock 명령 → 좌 LOCK 유지, 그 주기 이벤트의 `reason_left = APPROACH_RISK_SUPPRESSED`.

#### SWR-006 접근위험 경고 후 운전자 override
- **분류**: ASIL B (A-02에 따라 QM 요구 OEM-FR-003을 ASIL B 모듈에서 구현) · **출처**: OEM-SR-002, OEM-FR-003 · **검증**: U, S, W
- **요구사항**:
  1. 시각은 명령을 담은 스냅샷의 `source_timestamp_s`를 쓴다 (OEM-IF-004).
  2. SWR-005에 의해 도어 d의 해제가 처음 억제된 시각을 `t0`로 기록한다.
  3. 이후 도어 d를 포함하는 unlock 명령(`side`가 d 또는 `all`, `source` 무관)이 아래 조건을 모두 만족하면 override로 처리한다: 도어 d 출력 `RELEASE`, `state = OVERRIDE`, 이유 코드 `DRIVER_OVERRIDE` **[가정 A-07, A-11]**.
     - `t − t0 ≤ 10.0 s`
     - 차속 < 3.0 km/h (주행 중에는 override 불가) **[가정 A-13]**
  4. `t − t0 > 10.0 s`인 재입력은 새 첫 억제로 처리하고 `t0`를 갱신한다.
  5. 도어 d의 접근위험이 FALSE로 바뀌는 주기, 또는 차속이 3.0 km/h 이상이 되는 주기에 도어 d의 override 상태와 `t0`를 모두 초기화한다 **[가정 A-13]**. 이후 위험이 TRUE이면 새 억제부터 시작한다.
  6. override는 3.1 순위 1~6 규칙(ISOFIX 포함)을 넘지 못한다.
- **수용기준**: 첫 억제 후 10.0 s 재입력 → override, 10.1 s → 억제(새 t0). 차속 3.0 km/h에서 10 s 내 재입력 → 억제, 2.9 km/h → override. 2.9 km/h에서 override 성립 후 접근위험 TRUE 유지한 채 3.0 km/h → 그 주기에 해당 도어 LOCK(`AUTO_LOCK_SPEED`), override 종료. 좌 override가 우 도어를 바꾸지 않는다. 위험 FALSE→TRUE 후 첫 unlock은 억제된다.

#### SWR-009 좌·우 독립 처리
- **분류**: ASIL B · **출처**: OEM-SR-002 · **검증**: U, S
- **요구사항**: 접근위험, 억제, override 판정은 좌·우 도어별로 독립적으로 수행해야 한다. 한쪽 도어의 접근위험·override가 반대쪽 출력, 이유 코드, `t0`를 바꾸지 않아야 한다.
- **수용기준**: 좌 접근위험 TRUE, 우 FALSE에서 ALL unlock → 좌 LOCK(`APPROACH_RISK_SUPPRESSED`), 우 RELEASE(`DRIVER_COMMAND`).

### 4.5 강제 해제·강제 잠금 (QM)

#### SWR-017 화재·과온·성인 탑승 강제 해제
- **분류**: QM · **출처**: OEM-FR-005, OEM-IF-007 · **검증**: U, S, W
- **요구사항**: `fire_detected`, `overtemperature_detected`, `adult_present` 중 하나가 TRUE인 반영 주기에 두 출력을 `RELEASE`로 하고 입력별 이유 코드를 기록해야 한다. 화재·과온은 3.1 순위 3, 성인 탑승은 순위 8을 따른다 **[가정 A-01, A-08]**. 동시에 참이면 화재 > 과온 > 성인 순으로 이유 코드를 정한다.
- **수용기준**: 각 입력 단독 주입 시 반영 주기에 양쪽 RELEASE와 해당 이유 코드. 차속 50 km/h에서 화재 TRUE → 양쪽 RELEASE. 우 ISOFIX TRUE + 성인 TRUE → 우 LOCK 유지, 좌 RELEASE.

#### SWR-018 ISOFIX 강제 잠금
- **분류**: QM · **출처**: OEM-FR-006, OEM-IF-008 · **검증**: U, S, W
- **요구사항**: `isofix_left`/`isofix_right`가 TRUE인 동안 해당 도어 출력을 `LOCK`(`ISOFIX_LOCK`)으로 하고, 반대쪽 출력은 다른 규칙이 없으면 유지해야 한다 (3.1 순위 6, 화재·과온보다 낮고 성인 탑승보다 높음) **[가정 A-01]**.
- **수용기준**: 좌·우 RELEASE에서 좌 ISOFIX만 TRUE → 반영 주기에 좌 LOCK, 우 RELEASE.

### 4.6 운전자 명령·자동 잠금·시동 (QM)

#### SWR-001 운전자 잠금·해제 명령 처리
- **분류**: QM · **출처**: OEM-FR-001, OEM-IF-004 · **검증**: U, S, W
- **요구사항**: SW는 `source`가 `physical_button`, `avn`, `voice`, `mobile_app` 중 하나인 유효한 운전자 명령을 동일하게 처리해야 한다. `action = lock`은 선택 도어를 `LOCK`으로, `unlock`은 SWR-004 조건에서 `RELEASE`로 하고, 이유 코드는 `DRIVER_COMMAND`이다.
- **수용기준**: 정지·정상 입력에서 4 source × 2 action × 3 side 조합이 선택 도어에만 적용된다.

#### SWR-002 도어 선택
- **분류**: QM · **출처**: OEM-FR-001 · **검증**: U, S
- **요구사항**: `side = left`는 좌 도어만, `right`는 우 도어만, `all`은 양쪽 도어에 명령을 적용해야 한다. 선택하지 않은 도어 출력은 바꾸지 않는다.
- **수용기준**: 좌 LOCK/우 RELEASE에서 `right lock` → 좌 LOCK/우 LOCK, 이어서 `left unlock` → 좌 RELEASE/우 LOCK.

#### SWR-004 일반 해제 허용 조건
- **분류**: QM · **출처**: OEM-FR-001 · **검증**: U, S
- **요구사항**: 운전자 unlock 명령은 해당 도어에 3.1 순위 1~9의 활성 규칙이 없을 때만 적용된다. 접근위험(순위 7)에 막히면 SWR-005·006으로, 자동 잠금(순위 9)에 막히면 이유 코드 `AUTO_LOCK_SPEED`로 처리한다 **[가정 A-13]**.
- **수용기준**: 차속 3.0 km/h에서 `all unlock` → 양쪽 LOCK 유지, `AUTO_LOCK_SPEED`. 차속 2.9 km/h, 양쪽 LOCK에서 → 양쪽 RELEASE.

#### SWR-003 주행 자동 잠금
- **분류**: QM · **출처**: OEM-FR-002, OEM-IF-001 · **검증**: U, S
- **요구사항**: 차속이 3.0 km/h 이상인 동안 두 출력을 `LOCK`(`AUTO_LOCK_SPEED`)으로 해야 한다 (3.1 순위 9). 차속이 3.0 km/h 미만이 되어도 자동으로 해제하지 않는다.
- **수용기준**: 차속 2.9 → 3.0 km/h의 반영 주기에 양쪽 LOCK. 2.9 km/h에서는 바뀌지 않는다. 이후 0.0 km/h가 되어도 LOCK 유지.

#### SWR-020 시동 꺼짐 시 해제
- **분류**: QM · **출처**: OEM-FR-007, OEM-IF-009 · **검증**: U, S, W
- **요구사항**: G9가 신선하고 `ignition_on = FALSE`인 주기에 두 출력을 `RELEASE`, `state = OFF`, 이유 코드 `IGNITION_OFF`로 해야 한다. 이 규칙은 3.1 순위 1로 최우선이다 **[가정 A-14]**. 이 주기에 충돌 래치, override 상태, `t0`를 초기화한다.
- **수용기준**: 양쪽 LOCK, 접근위험 TRUE에서 ignition_on FALSE → 반영 주기에 양쪽 RELEASE, OFF, IGNITION_OFF.

### 4.7 우선순위 중재 (ASIL B)

#### SWR-022 우선순위 중재
- **분류**: ASIL B (ASIL B 규칙을 포함하므로) · **출처**: OEM-SR-001, SR-002, SR-003, SR-004, FR-002, FR-005, FR-006, FR-007 · **검증**: U, S
- **요구사항**: 여러 규칙이 동시에 활성이면 SW는 3.1 표에 따라 도어별로 최상위 규칙 하나로 출력을 정하고, 2.2와 3.2에 따라 `reason_left`, `reason_right`, `priority_reason`, `reason_code`, `state`를 제공해야 한다 **[가정 A-01, A-03, A-04, A-08, A-12, A-13, A-14, A-15, A-18, A-20]**.
- **수용기준**: 동시에 활성화될 수 있는 **모든 규칙 쌍**(순위 1~10 중 두 개, 7과 7a는 같은 도어에서 배타)에서 상위 규칙의 출력·이유 코드·state가 나온다. 세 개 이상의 조합은 G4 시스템 테스트에서 PICT 페어와이즈로 검증한다.
- **비고**: OEM 추적표(9장)에 없는 SWR이다. 여러 OEM 요구 사이의 충돌을 한 곳에서 정하려고 추가했다.

### 4.8 상태 제공·표시 (QM)

#### SWR-014 상태 조회 인터페이스
- **분류**: QM · **출처**: OEM-FR-004, OEM-IF-006 · **검증**: U, I
- **요구사항**: SW는 상태 조회 요청에 `lock_left`, `lock_right`, `state`, `input_validity`, `priority_reason`, `reason_code`, `reason_left`, `reason_right` **[가정 A-20]**, `warning_code`를 담은 응답을 제공해야 한다. 응답 직렬화에 실패하면 HTTP 500을 반환한다.
- **수용기준**: 응답에 위 9개 필드가 모두 존재. 직렬화 실패 주입 시 HTTP 500.

#### SWR-015 Web 시뮬레이터 표시와 시험 입력
- **분류**: QM · **출처**: OEM-FR-004 · **검증**: I, W
- **요구사항**: Web 시뮬레이터는 SWR-014의 필드(도어별 이유 포함, **[가정 A-20]**)를 화면에 표시하고, OEM-IF-001~004, 007~009의 시험 입력을 주입할 수 있어야 한다. 주입한 입력은 SWR-013 검증을 그대로 거친다.
- **수용기준**: Web에서 좌 접근위험 TRUE를 주입하면 화면에 좌 LOCK, 좌 이유 `APPROACH_RISK_LOCK`이 표시된다.

### 4.9 이벤트 기록 (QM)

#### SWR-010 최근 결정 100건 보존
- **분류**: QM · **출처**: OEM-NFR-002 · **검증**: U, I
- **요구사항**: SW는 평가 주기마다 결정 하나를 이벤트로 기록하고 **[가정 A-17]**, 1부터 1씩 증가하는 `event_id`를 부여하며, 최신 100건만 시간순으로 보존해야 한다.
- **수용기준**: 101건 기록 후 조회 결과가 `event_id` 2~101의 100건, 오름차순.

#### SWR-011 이벤트 스키마와 금지 정보
- **분류**: QM · **출처**: OEM-NFR-002 · **검증**: U
- **요구사항**: 이벤트는 `event_id`, `now_s`, `lock_left`, `lock_right`, `state`, `priority_reason`, `reason_code`, `reason_left`, `reason_right` **[가정 A-20]**, `input_validity`, `warning_code` 필드만 가져야 한다. 영상, 음성, 개인 식별자는 저장하지 않는다. 입력 스냅샷에 허용 외 필드가 있어도 이벤트에 복사하지 않는다.
- **수용기준**: 허용 외 필드(예: `driver_name`)가 포함된 입력 후에도 이벤트 필드 집합이 정확히 위 11개.

#### SWR-012 휘발성 저장
- **분류**: QM · **출처**: OEM-NFR-002 · **검증**: I
- **요구사항**: 이벤트 저장소는 프로세스 메모리에만 존재해야 하며 파일·DB 등 영속 저장소에 쓰지 않는다. 프로세스를 재기동하면 이벤트는 0건이다.
- **수용기준**: 이벤트 기록 후 재기동 → 조회 결과 0건. 실행 중 파일 쓰기 없음.

### 4.10 결정론 (QM)

#### SWR-016 결정론적 재생
- **분류**: QM · **출처**: OEM-NFR-001 · **검증**: S
- **요구사항**: 같은 초기 상태, 같은 입력 스냅샷 순서, 같은 주입 시계에는 같은 출력 순서를 생성해야 한다. 판정은 실제 시간, 난수, 전역 가변 상태에 의존하지 않는다.
- **수용기준**: 고정 시계로 같은 입력 벡터를 1,000회 재생했을 때 출력 순서의 SHA-256 해시가 모두 같다.

### 4.11 결번

- **SWR-019**: OEM 추적표에 없는 번호. 결번으로 두고 OEM에 누락 여부를 질의한다 **[가정 A-10]**.

## 5. 요구사항 요약

| 구분 | SWR | 수 |
|---|---|---|
| ASIL B | 005, 006, 007, 008, 009, 013, 021, 022 | 8 |
| QM | 001, 002, 003, 004, 010, 011, 012, 014, 015, 016, 017, 018, 020 | 13 |
| 결번 | 019 | 1 |
| 합계 (결번 제외) | | 21 |

가정 의존 요구사항 (OEM 답변 시 재검토): SWR-004, 005, 006, 007, 008, 010, 011, 013, 014, 015, 017, 018, 020, 021, 022.
