아래 DocuMeta 계약과 근거만 사용해서 내부 업무시스템 점검 안내 공문을 작성해줘.

반드시 지켜야 할 출력 형식:
1. 먼저 "DocuMeta 채움 결과"라는 제목 아래 YAML을 출력한다.
2. 그 다음 "공문 초안"이라는 제목 아래 공문 본문을 출력한다.
3. 공문 초안에는 반드시 점검 정보 표를 포함한다.
4. 마지막에 "검증 결과"라는 제목 아래 필수 슬롯과 금지어 검사 결과를 표로 출력한다.
5. 근거에 없는 서비스명, 담당자, 문의처, 일정은 추가하지 않는다.

DocuMeta:
document_type: official_notice
document_subtype: system_maintenance_notice
audience: 전 직원
purpose: 내부 업무시스템 정기점검 안내

source_policy:
  allowed: 근거에 있는 값만 사용한다.
  missing_value: 근거에 없으면 "근거 없음"이라고 쓴다.
  banned_additions:
    - 메일
    - 메신저
    - 포털
    - 그룹웨어

evidence_refs:
  - id: work-plan
    text: 2026년 6월 3일 19:00-22:00 내부 업무시스템 정기점검을 실시한다.
    use_for:
      - schedule
  - id: impact
    text: 점검 중 전자결재와 문서 열람이 제한된다.
    use_for:
      - scope
  - id: previous-notice
    text: 사용자는 점검 전 작성 중인 문서를 저장하고 긴급 결재 건은 사전에 처리해야 한다. 문의처는 정보화지원팀 1234다.
    use_for:
      - required_actions
      - contact

required_slots:
  title: 내부 업무시스템 정기점검 안내
  recipient: 전 직원
  schedule: 근거에서 채움
  scope: 근거에서 채움
  required_actions: 근거에서 채움
  contact: 근거에서 채움
  attachment: 내부 업무시스템 정기점검 작업계획

table_contracts:
  notice_table:
    columns:
      - 구분
      - 내용
    rows:
      - [점검 일시, schedule]
      - [영향 범위, scope]
      - [사용자 조치, required_actions]
      - [문의처, contact]

validation_rules:
  required:
    - title
    - recipient
    - schedule
    - scope
    - required_actions
    - contact
  banned_terms:
    - 메일
    - 메신저
    - 포털
    - 그룹웨어
  output_must_include:
    - DocuMeta 채움 결과 YAML
    - 점검 정보 표
    - 검증 결과 표
