# 템플릿 초안

## 1. 슬롯 후보

```yaml
slots:
  organization: 대한디지털진흥원
  recipient: 전 직원
  via: 각 부서장
  title: null
  purpose_sentence: null
  schedule: null
  scope: null
  required_actions: null
  contact: null
  attachment: 내부 업무시스템 정기점검 작업계획
  sender_title: 대한디지털진흥원장
```

## 2. table_contracts 후보

```yaml
table_contracts:
  notice_table:
    columns: [구분, 내용]
    rows:
      - [가. 점검 일시, schedule]
      - [나. 영향 범위, scope]
      - [다. 조치 사항, required_actions]
      - [라. 문의처, contact]
  footer_metadata_table:
    rows:
      - [시행, doc_number, 접수, receipt_number]
      - [담당, officer, 전화, phone]
      - [우, postal_code, 주소, address]
      - [전자우편, email, 공개구분, disclosure]
```

## 3. hwpx_template.blocks 후보

```yaml
hwpx_template:
  blocks:
    - type: heading
      slot: organization
    - type: table
      rows:
        - [수신, recipient]
        - [(경유), via]
        - [제목, title]
    - type: paragraph
      text: "1. 귀 기관의 무궁한 발전을 기원합니다."
    - type: paragraph
      template: "2. {{ purpose_sentence }}"
    - type: table
      contract: notice_table
    - type: paragraph
      template: "붙임  {{ attachment }}  1부.  끝."
    - type: heading
      slot: sender_title
    - type: table
      contract: footer_metadata_table
```

## 4. QMD 템플릿 placeholder 후보

- `{{ title }}`
- `{{ document_type }}`
- `{{ output_targets_yaml }}`
- `{{ date }}`
- `{{ html_blocks }}`

## 5. TYP 템플릿 placeholder 후보

- `{{ title }}`
- `{{ typ_blocks }}`

## 6. 사람이 검토해야 할 지점

- 샘플 문서의 값이 고정값인지 슬롯인지 구분한다.
- 표 라벨은 고정하고 값만 슬롯으로 둔다.
- QMD/TYP 템플릿에는 본문 문장을 하드코딩하지 않는다.
- HWPX 블록 순서가 실제 공문 양식과 맞는지 확인한다.
