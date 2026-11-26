# Wiper Control ECU — Software Requirements Specification (발췌)

| ID | ASIL | 요구사항 |
|---|---|---|
| SWR-WIP-001 | B | 점화 상태(Ignition)가 ON일 때만 와이퍼 모터를 구동한다. Ignition 값: OFF, ACC, ON. |
| SWR-WIP-002 | B | WiperSwitch가 LOW이면 모터를 저속(45 rpm ±3)으로, HIGH이면 고속(65 rpm ±3)으로 구동한다. WiperSwitch 값: OFF, INT, LOW, HIGH. |
| SWR-WIP-003 | B | WiperSwitch가 INT일 때 간헐 주기는 IntDelay 신호(1~10, 정수, 분해능 1)에 따라 주기 = IntDelay × 1.0 s 로 한다. 범위 밖 값은 무효로 간주하고 주기 4 s를 사용한다. |
| SWR-WIP-004 | A | INT 모드에서 차속(VehicleSpeed, 0~250 km/h, 분해능 0.1)이 100 km/h 이상이면 간헐 주기를 50%로 단축한다. |
| SWR-WIP-005 | A | RainSensor가 HEAVY이고 WiperSwitch가 INT이면 자동으로 LOW 속도로 구동한다. RainSensor 값: NONE, LIGHT, HEAVY. |
| SWR-WIP-006 | B | WiperSwitch 신호가 200 ms 이상 수신되지 않으면 모터를 정지 위치(park)로 복귀시키고 DTC B1001을 저장한다. |
| SWR-WIP-007 | QM | 스위치 OFF 입력 후 모터는 1.5 s 이내에 park 위치에 정지해야 한다. |
