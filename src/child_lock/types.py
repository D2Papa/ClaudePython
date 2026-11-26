"""!
@brief 공용 타입·상수 (ASIL B, SWD-001 2장).
@details 우선순위는 Rule 열거형 하나에만 정의한다 (SWA P-04).
         모든 데이터 구조는 불변이다 (SWA P-01).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from types import MappingProxyType


class Lock(StrEnum):
    """! @brief 도어 논리 차일드락 출력 (OEM-IF-005)."""

    LOCK = "LOCK"
    RELEASE = "RELEASE"


class Door(StrEnum):
    """! @brief 후석 도어. 선언 순서(LEFT → RIGHT)가 동률 시 우선순위다."""

    LEFT = "left"
    RIGHT = "right"


class State(StrEnum):
    """! @brief SW 상태. 선언 순서가 표시 우선순위다 (앞이 높음, SWRS 2.2)."""

    OFF = "OFF"
    DEGRADED = "DEGRADED"
    FAULT = "FAULT"
    OVERRIDE = "OVERRIDE"
    NORMAL = "NORMAL"


class Validity(StrEnum):
    """! @brief 입력 유효성 표시 (SWRS 2.2)."""

    VALID = "VALID"
    INVALID = "INVALID"
    STALE = "STALE"


class Group(StrEnum):
    """! @brief 검증·신선도 판정 단위 입력 그룹 (SWRS 2.1)."""

    G1 = "G1"  # OEM-IF-001 차속·기어
    G2 = "G2"  # OEM-IF-002 충돌
    G3 = "G3"  # OEM-IF-003 접근위험
    G7 = "G7"  # OEM-IF-007 화재·과온·성인
    G8 = "G8"  # OEM-IF-008 ISOFIX
    G9 = "G9"  # OEM-IF-009 시동·센서 고장


class Reason(StrEnum):
    """! @brief 이유 코드 (SWRS 2.3)."""

    IGNITION_OFF = "IGNITION_OFF"
    CRASH_RELEASE = "CRASH_RELEASE"
    CRASH_PENDING = "CRASH_PENDING"
    FIRE_RELEASE = "FIRE_RELEASE"
    OVERTEMP_RELEASE = "OVERTEMP_RELEASE"
    INPUT_STALE = "INPUT_STALE"
    SENSOR_FAULT = "SENSOR_FAULT"
    ISOFIX_LOCK = "ISOFIX_LOCK"
    APPROACH_RISK_LOCK = "APPROACH_RISK_LOCK"
    APPROACH_RISK_SUPPRESSED = "APPROACH_RISK_SUPPRESSED"
    DRIVER_OVERRIDE = "DRIVER_OVERRIDE"
    ADULT_RELEASE = "ADULT_RELEASE"
    AUTO_LOCK_SPEED = "AUTO_LOCK_SPEED"
    DRIVER_COMMAND = "DRIVER_COMMAND"
    INPUT_INVALID = "INPUT_INVALID"
    COMMAND_REJECTED = "COMMAND_REJECTED"
    NO_CHANGE = "NO_CHANGE"


class Rule(IntEnum):
    """! @brief 판정 규칙. 값이 작을수록 우선 (SWRS 3.1, 7a를 7 앞에 재번호)."""

    IGNITION_OFF = 1
    CRASH = 2
    EMERGENCY_RELEASE = 3
    INPUT_STALE = 4
    SENSOR_FAULT = 5
    ISOFIX = 6
    DRIVER_OVERRIDE = 7
    APPROACH_RISK = 8
    ADULT_RELEASE = 9
    AUTO_LOCK = 10
    DRIVER_COMMAND = 11
    NO_CHANGE = 12


## QM 요구에서 온 규칙 (중재기의 QM 후보 검사 대상, SWA 5장)
QM_RULES = frozenset(
    {
        Rule.IGNITION_OFF,
        Rule.EMERGENCY_RELEASE,
        Rule.ISOFIX,
        Rule.ADULT_RELEASE,
        Rule.AUTO_LOCK,
        Rule.DRIVER_COMMAND,
    }
)

## 규칙별 고정 출력 (None = 직전 유지). DRIVER_COMMAND는 명령에 따라 달라 제외
RULE_OUTPUT: Mapping[Rule, Lock | None] = MappingProxyType(
    {
        Rule.IGNITION_OFF: Lock.RELEASE,
        Rule.CRASH: Lock.RELEASE,
        Rule.EMERGENCY_RELEASE: Lock.RELEASE,
        Rule.INPUT_STALE: None,
        Rule.SENSOR_FAULT: None,
        Rule.ISOFIX: Lock.LOCK,
        Rule.DRIVER_OVERRIDE: Lock.RELEASE,
        Rule.APPROACH_RISK: Lock.LOCK,
        Rule.ADULT_RELEASE: Lock.RELEASE,
        Rule.AUTO_LOCK: Lock.LOCK,
        Rule.NO_CHANGE: None,
    }
)

## 갱신 지연 판정 한계 (초과 시 지연, SWR-013)
STALE_AFTER_S = 0.200
## 자동 잠금 차속 (이상, SWR-003)
AUTO_LOCK_KPH = 3.0
## override 허용 시간 (이하, SWR-006)
OVERRIDE_WINDOW_S = 10.0
## 차속 유효 범위 (OEM-IF-001)
SPEED_MIN_KPH = 0.0
SPEED_MAX_KPH = 300.0
## 평가 주기 참고값 (가정 A-05)
ENGINE_PERIOD_S = 0.050
## 이벤트 보존 건수 (SWR-010)
EVENT_CAPACITY = 100
## 부동소수 경계 비교 자리수 (SAP 2장)
TIME_DIGITS = 9


def frozen(mapping: Mapping) -> Mapping:
    """!
    @brief 읽기 전용 매핑을 만든다.
    @param mapping 원본 매핑
    @return 원본 복사본의 읽기 전용 뷰
    """
    return MappingProxyType(dict(mapping))


@dataclass(frozen=True)
class Command:
    """!
    @brief 검증된 운전자 명령 (OEM-IF-004).
    @param doors 적용 도어 집합 (all → 양쪽)
    @param action LOCK 또는 RELEASE(unlock)
    @param source 입력 경로
    """

    doors: frozenset[Door]
    action: Lock
    source: str


@dataclass(frozen=True)
class Values:
    """!
    @brief 그룹별 마지막 수락 값. 미수신 필드는 None.
    """

    speed_kph: float | None = None
    gear: str | None = None
    crash_status: str | None = None
    risk: Mapping[Door, bool] | None = None
    fire: bool | None = None
    overtemp: bool | None = None
    adult: bool | None = None
    isofix: Mapping[Door, bool] | None = None
    ignition_on: bool | None = None
    sensor_fault: bool | None = None


@dataclass(frozen=True)
class DoorApproach:
    """!
    @brief 도어별 접근위험 판정 상태 (SWR-006).
    @param t0 첫 억제 시각 (없으면 None)
    @param override override 성립 여부
    """

    t0: float | None = None
    override: bool = False


## 접근위험 판정 초기 상태 (양쪽 도어)
INITIAL_DOORS: Mapping[Door, DoorApproach] = frozen({d: DoorApproach() for d in Door})


@dataclass(frozen=True)
class ControllerState:
    """! @brief 판정 코어의 주기 간 상태 (SWA 4.3)."""

    values: Values = field(default_factory=Values)
    group_ts: Mapping[Group, float] = field(default_factory=lambda: frozen({}))
    last_ts: float | None = None
    crash_latched: bool = False
    doors: Mapping[Door, DoorApproach] = INITIAL_DOORS
    outputs: Mapping[Door, Lock] = field(
        default_factory=lambda: frozen(dict.fromkeys(Door, Lock.RELEASE))
    )


@dataclass(frozen=True)
class Intake:
    """! @brief 입력 검증 결과 (SWD 3.1)."""

    values: Values
    group_ts: Mapping[Group, float]
    last_ts: float | None
    command: Command | None = None
    command_ts: float | None = None
    command_rejected: bool = False
    input_rejected: bool = False


@dataclass(frozen=True)
class Context:
    """! @brief 한 평가 주기의 불변 판정 문맥 (SWD 2.3)."""

    now_s: float
    values: Values
    stale: frozenset[Group]
    command: Command | None
    command_rejected: bool
    input_rejected: bool
    crash_latched: bool
    doors: Mapping[Door, DoorApproach]
    suppressed: frozenset[Door]


@dataclass(frozen=True)
class Candidate:
    """!
    @brief 도어 하나에 대한 규칙 후보.
    @param rule 규칙 (우선순위)
    @param lock 출력 (None = 직전 유지)
    @param reason 이유 코드
    """

    rule: Rule
    lock: Lock | None
    reason: Reason


@dataclass(frozen=True)
class Decision:
    """! @brief 한 주기의 결정 (SWRS 2.2, OEM-IF-005·006)."""

    lock_left: Lock
    lock_right: Lock
    state: State
    priority_reason: str
    reason_code: Reason
    reason_left: Reason
    reason_right: Reason
    input_validity: Validity
    warning_code: str | None


@dataclass(frozen=True)
class StepResult:
    """! @brief evaluate 결과: 다음 상태와 결정."""

    state: ControllerState
    decision: Decision


## 첫 평가 전 결정 값 (SWRS 2.2, CR-001)
INITIAL_DECISION = Decision(
    lock_left=Lock.RELEASE,
    lock_right=Lock.RELEASE,
    state=State.OFF,
    priority_reason=Rule.NO_CHANGE.name,
    reason_code=Reason.NO_CHANGE,
    reason_left=Reason.NO_CHANGE,
    reason_right=Reason.NO_CHANGE,
    input_validity=Validity.STALE,
    warning_code=None,
)
