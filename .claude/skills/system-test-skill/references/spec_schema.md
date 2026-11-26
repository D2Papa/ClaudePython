# build_workbook.py 입력 JSON 형식

```json
{
  "project": "WiperControl",
  "test_basis": [
    {
      "id": "SRS-001",
      "title": "IGN ON 상태에서 와이퍼 스위치 LOW 시 저속 작동",
      "text": "요구사항 원문 (선택)",
      "type": "functional",
      "asil": "B",
      "assigned_id": false,
      "bva_ecp_na_reason": ""
    }
  ],
  "test_cases": [
    {
      "id": "STC-F-001",
      "sheet": "functional",
      "basis_ids": ["SRS-001"],
      "objective": "차속 하한 경계에서 기능 활성 전환 확인",
      "preconditions": "IGN=ON, 차속 0 km/h에서 2 s 유지",
      "inputs": "VehicleSpeed = 9.9 km/h → 10.0 km/h",
      "procedure": "1) ...\n2) ...",
      "expected": "1단계 후 FuncActive = 0, 2단계 후 100 ms 이내 FuncActive = 1",
      "techniques": ["경계값 분석"],
      "suggested": false,
      "gap_reason": "",
      "pict_model": "",
      "notes": ""
    }
  ],
  "pict_models": [
    {
      "name": "wiper_modes",
      "basis_ids": ["SRS-001", "SRS-002"],
      "model": "Ignition: OFF, ACC, ON\n...",
      "order": 2,
      "rows": 16
    }
  ],
  "requirement_issues": [
    {"basis_id": "SRS-004", "issue": "타임아웃 경계가 '이상'인지 '초과'인지 불명확", "impact": "STC-F-021 기대값 미확정 (제안 처리)"}
  ],
  "column_map": {}
}
```

## 필드 규칙

**test_basis**
- `type`: `functional` 또는 `non-functional`
- `assigned_id`: 원문에 ID가 없어서 스킬이 부여했으면 `true` (그러면 `text`에 원문을 넣을 것 → `베이시스 ID 매핑` 시트 생성)
- `bva_ecp_na_reason`: 입력 도메인이 없어 BVA/ECP를 적용할 수 없을 때만 사유를 적는다. 비어 있으면 이 요구사항에 BVA, ECP 케이스가 각각 1개 이상 있어야 한다.

**test_cases**
- `sheet`: `functional` 또는 `non-functional`
- `techniques`: 문자열 배열. 표준 표기: `동치 클래스 분할`, `경계값 분석`, `페어와이즈 (PICT)`, `WoW 검증`
- `suggested: true` → `제안` 표시, 커버리지 산정 제외
- `basis_ids`가 비어도 되는 경우는 `suggested: true`이고 `gap_reason`이 있을 때뿐
- `페어와이즈 (PICT)` 케이스는 `pict_model`에 `pict_models[].name`을 적는다

**pict_models**
- `rows`: `run_pict.py` 결과 행 수. 같은 모델을 참조하는 케이스 수가 이와 다르면 오류 (행을 빠뜨리면 쌍 커버리지가 깨진다)

**column_map** (양식 사용 시, `--template`와 함께)
- 내부 필드 → 양식의 헤더 텍스트. 예:
  ```json
  {"id": "TC No.", "basis_ids": "Req. ID", "objective": "Test Description",
   "preconditions": "Pre-condition", "inputs": "Input", "procedure": "Test Step",
   "expected": "Expected Result", "techniques": "Test Method", "suggested": "Remark"}
  ```
- 양식에 대응 열이 없는 필드 중 `techniques`, `suggested`는 양식 오른쪽 끝에 열을 추가해 기록한다 (기법 표기와 제안 표시는 요구된 정보이므로 버리지 않는다).
- `template_sheet`: 양식 워크북에서 케이스 시트로 쓸 시트 이름 (생략 시 첫 시트)
