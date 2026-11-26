# 요구사항 양방향 추적성 매트릭스

| 항목 | 내용 |
|---|---|
| 문서 ID | TRACE-001 |
| 대상 | OEM-SWR-001 ↔ SWRS-001 ↔ UC-001 |
| 기준선 | BL-SWR-1.0 |

## 1. OEM 요구사항 → SW 요구사항 (하향)

| OEM ID | 분류 | SWR | OEM 추적표(9장) 대비 | 비고 |
|---|---|---|---|---|
| OEM-SR-001 | ASIL B | SWR-007, SWR-008, SWR-022 | 일치 + SWR-022 | 충돌 우선순위는 SWR-022 |
| OEM-SR-002 | ASIL B | SWR-005, SWR-006, SWR-009, SWR-022 | 일치 + SWR-022 | |
| OEM-SR-003 | ASIL B | SWR-013, SWR-022 | 일치 + SWR-022 | DEGRADED 우선순위는 SWR-022 |
| OEM-SR-004 | ASIL B | SWR-021, SWR-022 | 일치 + SWR-022 | |
| OEM-FR-001 | QM | SWR-001, SWR-002, SWR-004 | 일치 | |
| OEM-FR-002 | QM | SWR-003, SWR-022 | 일치 + SWR-022 | |
| OEM-FR-003 | QM | SWR-006 | 일치 | ASIL B 모듈에서 구현 (A-02) |
| OEM-FR-004 | QM | SWR-014, SWR-015 | 일치 | |
| OEM-FR-005 | QM | SWR-017, SWR-022 | 일치 + SWR-022 | |
| OEM-FR-006 | QM | SWR-018, SWR-022 | 일치 + SWR-022 | |
| OEM-FR-007 | QM | SWR-020, SWR-022 | 일치 + SWR-022 | |
| OEM-NFR-001 | QM | SWR-016 | 일치 | |
| OEM-NFR-002 | QM | SWR-010, SWR-011, SWR-012 | 일치 | |

**하향 커버리지: OEM 요구 13/13 (100%)**

## 2. SW 요구사항 → OEM 요구사항 (상향)

| SWR | 분류 | OEM 요구 | OEM 인터페이스 | 유스케이스 | 가정 |
|---|---|---|---|---|---|
| SWR-001 | QM | FR-001 | IF-004 | UC-01 | — |
| SWR-002 | QM | FR-001 | IF-004 | UC-01 | — |
| SWR-003 | QM | FR-002 | IF-001 | UC-02 | — |
| SWR-004 | QM | FR-001 | IF-004 | UC-01, UC-02 | A-13 |
| SWR-005 | ASIL B | SR-002 | IF-003, IF-004 | UC-03 | A-20 |
| SWR-006 | ASIL B | SR-002, FR-003 | IF-001, IF-003, IF-004 | UC-04 | A-02, A-07, A-11, A-13, A-21 |
| SWR-007 | ASIL B | SR-001 | IF-002 | UC-05 | A-03, A-04, A-05, A-15 |
| SWR-008 | ASIL B | SR-001 | IF-002 | UC-05 | A-06 |
| SWR-009 | ASIL B | SR-002 | IF-003 | UC-03, UC-04 | — |
| SWR-010 | QM | NFR-002 | — | UC-11 | A-17 |
| SWR-011 | QM | NFR-002 | — | UC-11 | A-20 |
| SWR-012 | QM | NFR-002 | — | UC-11 | — |
| SWR-013 | ASIL B | SR-003 | IF-001~004, 007~009 | UC-09 | A-05, A-09, A-12, A-16, A-19 |
| SWR-014 | QM | FR-004 | IF-006 | UC-11 | A-20 |
| SWR-015 | QM | FR-004 | IF-006 | UC-11 | A-20 |
| SWR-016 | QM | NFR-001 | — | UC-12 | — |
| SWR-017 | QM | FR-005 | IF-007 | UC-06 | A-01, A-08 |
| SWR-018 | QM | FR-006 | IF-008 | UC-07 | A-01 |
| SWR-020 | QM | FR-007 | IF-009 | UC-08 | A-14 |
| SWR-021 | ASIL B | SR-004 | IF-009 | UC-09 | A-03, A-18 |
| SWR-022 | ASIL B | SR-001~004, FR-002, FR-005~007 | — | UC-10 | A-01, A-03, A-04, A-08, A-12, A-13, A-14, A-15, A-18, A-20 |

**상향 추적: SWR 21/21이 OEM 요구에 연결 (출처 없는 SWR 0건)**

## 3. OEM 인터페이스 → SW 요구사항

| 인터페이스 | SWR | 비고 |
|---|---|---|
| OEM-IF-001 | SWR-003, SWR-006, SWR-013 | `gear`는 검증만 (A-09) |
| OEM-IF-002 | SWR-007, SWR-008, SWR-013 | |
| OEM-IF-003 | SWR-005, SWR-006, SWR-009, SWR-013 | |
| OEM-IF-004 | SWR-001, SWR-002, SWR-004, SWR-005, SWR-006, SWR-013 | 요청 시각은 스냅샷 타임스탬프 (SWR-006) |
| OEM-IF-005 | SWRS 2.2 출력 모델 (모든 출력 SWR) | 적용 feedback은 범위 밖 |
| OEM-IF-006 | SWR-014, SWR-015, SWR-022 | priority_reason → reason_code 매핑은 SWRS 3.2 |
| OEM-IF-007 | SWR-013, SWR-017 | |
| OEM-IF-008 | SWR-013, SWR-018 | |
| OEM-IF-009 | SWR-013, SWR-020, SWR-021 | |

**인터페이스 커버리지: 9/9 (100%)**

## 4. 유스케이스 → SW 요구사항

| 유스케이스 | SWR |
|---|---|
| UC-01 | 001, 002, 004 |
| UC-02 | 003, 004 |
| UC-03 | 005, 009 |
| UC-04 | 006, 009 |
| UC-05 | 007, 008 |
| UC-06 | 017 |
| UC-07 | 018 |
| UC-08 | 020 |
| UC-09 | 013, 021 |
| UC-10 | 022 |
| UC-11 | 010, 011, 012, 014, 015 |
| UC-12 | 016 |

## 5. ASIL 분류 일관성

ASIL B OEM 요구(SR-001~004)에서 도출된 SWR은 모두 ASIL B다. QM 요구 FR-003에서 도출된 SWR-006은 ASIL B 요구 SR-002의 동작을 바꾸므로 ASIL B로 상향했다 (A-02). SWR-022는 ASIL B 규칙의 우선순위를 정하므로 ASIL B다.
