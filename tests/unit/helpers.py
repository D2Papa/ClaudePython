"""!
@brief 단위 테스트 공용 보조 함수 (시험 전용 — 제품 코드에 두지 않음).
"""

from child_lock.types import Context, Door, DoorApproach, Values, frozen

## 정상 주행 전 상태의 값: 시동 ON, 정지, 위험·강제 조건 없음
NORMAL_VALUES = Values(
    speed_kph=0.0,
    gear="P",
    crash_status="NONE",
    risk=frozen({Door.LEFT: False, Door.RIGHT: False}),
    fire=False,
    overtemp=False,
    adult=False,
    isofix=frozen({Door.LEFT: False, Door.RIGHT: False}),
    ignition_on=True,
    sensor_fault=False,
)


def doors(left=None, right=None):
    """! 도어별 DoorApproach 매핑 (기본: 초기 상태)."""
    return frozen({Door.LEFT: left or DoorApproach(), Door.RIGHT: right or DoorApproach()})


def make_ctx(values=NORMAL_VALUES, **changes):
    """! 기본값이 정상 상태인 Context. changes로 필드를 바꾼다."""
    fields = {
        "now_s": 1.0,
        "values": values,
        "stale": frozenset(),
        "command": None,
        "command_rejected": False,
        "input_rejected": False,
        "crash_latched": False,
        "doors": doors(),
        "suppressed": frozenset(),
    }
    fields.update(changes)
    return Context(**fields)
