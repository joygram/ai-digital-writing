# 시연 3: DocuMeta 프레임 생성

## 목표

비정형 샘플 원문에서 반복 구조를 뽑아 DocuMeta 프레임, 출력 템플릿 계약, RAG reference chunk를 만든다.

이 단계의 핵심은 완성 문장을 쓰는 것이 아니다.
문서 구조, 필수 슬롯, 표 계약, 출력 계약, 검색 근거를 분리하는 것이다.

## 실행

저장소 루트에서 실행할 때:

```bash
uv run python demos/03-documeta-completion/generate-template-draft.py
```

`demos/03-documeta-completion` 폴더 안에서 실행할 때:

```bash
uv run python generate-template-draft.py
```

## 준비 파일

| 파일 | 의미 |
| --- | --- |
| `in/sample-official-notice.md` | 메모, 제목 후보, 하단 정보가 섞인 비정형 공문 재료 |
| `support/fallback-template-draft.md` | API 실패 시 사용하는 내부 fallback 초안 |
| `support/reference-ingest-prompt.md` | 사람이 정의한 reference chunk 분리 규칙 |
| `../.env` | Blackbox 호환 API 설정 |

`in/`에는 실행 전에 준비된 입력 자료를 둔다.
`support/`에는 최종 사용자가 아니라 구축자, 개발자, 운영 설계자가 미리 만든 워크플로 산출물을 둔다.
실제 제품에서는 관리 화면, 템플릿 빌더, ingest rule editor 같은 곳에서 만들어질 설정을 데모에서는 문서 파일로 단순화했다.
`out/`에는 실행 후 생성되는 결과를 모은다.

## 전체 흐름

```text
sample-official-notice.md
  -> LLM 템플릿 생성 프롬프트
  -> 템플릿 초안
  -> reference ingest 규칙 프롬프트
  -> DocuMeta 프레임
  -> reference-docs/*.md
```

| 단계 | 하는 일 | 결과 |
| --- | --- | --- |
| 샘플 원문 로드 | 비정형 공문 재료를 읽는다. | 원문 텍스트 |
| 프롬프트 구성 | 슬롯, 표, 출력 계약을 뽑도록 LLM 입력을 만든다. | `00-template-generation-prompt.md` |
| 템플릿 초안 생성 | LLM 또는 fallback으로 초안을 만든다. | `00-template-draft.md` |
| Reference ingest 규칙 구성 | 사람이 정의한 분리 규칙과 원문을 확인 가능한 프롬프트로 남긴다. | `01-reference-ingest-prompt.md` |
| Reference chunk 생성 | ingest 규칙에 따라 원문 조각을 검색 가능한 근거 문서로 분리한다. | `reference-docs/*.md` |
| 계약 고정 | 사람이 검토해 다음 시연 입력으로 고정한다. | `../04-build-writing/in/documeta.yaml` |

## 실행 후 확인

| 결과 | 파일 |
| --- | --- |
| LLM 입력 프롬프트 | `out/00-template-generation-prompt.md` |
| 템플릿 초안 | `out/00-template-draft.md` |
| Reference ingest 규칙 프롬프트 | `out/01-reference-ingest-prompt.md` |
| DocuMeta 프레임 | `../04-build-writing/in/documeta.yaml` |
| RAG reference chunk | `out/reference-docs/*.md` |

시연 3에서 LLM은 템플릿 설계 초안을 만든다.
RAG reference chunk는 사람이 정의한 ingest 규칙을 스크립트가 적용해서 생성한다.
따라서 `support/reference-ingest-prompt.md`는 LLM이 만든 결과가 아니라, 구축자가 준비한 근거 분리 정책이다.

## Reference chunk

시연 3의 reference 생성은 실제 제품의 대량 ingest를 단순화한 장면이다.
`support/reference-ingest-prompt.md`는 원문에서 어떤 줄을 읽을지, 누가 만든 업무 자료로 볼지, 어떤 슬롯의 근거로 쓸지를 정의한다.
`ReferenceChunkSpec`은 이 시연용 ingest 규칙을 코드로 옮긴 구현이다.

| 생성 파일 | 원문 기준 | 역할 |
| --- | --- | --- |
| `work-plan.md` | `- 일시:` | `schedule` 슬롯 근거 |
| `impact.md` | `- 대상과 영향 범위:` | `scope` 슬롯 근거 |
| `previous.md` | `- 사전 조치:`, `- 문의:` | `required_actions`, `contact` 슬롯 근거 |
| `mail.md` | 메일 서비스 개편 후보 | 무관 문서 반례 |

`mail.md`는 현재 공문에 넣을 근거가 아니다.
retriever가 관련 없는 문서를 제외하는지 확인하기 위한 반례다.

## 검증 기준

- `out/00-template-draft.md`에 초안 검토 경고가 남는다.
- `out/01-reference-ingest-prompt.md`에 사람이 정의한 근거 분리 규칙이 남는다.
- `../04-build-writing/in/documeta.yaml`에 `source_contract`, `table_contracts`, `hwpx_template`, `adapter_contracts`가 있다.
- `out/reference-docs/`에 작업계획서, 영향 범위, 이전 안내문, 무관 문서 chunk가 나뉘어 있다.
- reference chunk는 정답 문장이 아니라 슬롯을 채울 업무 근거로 남는다.

## 가드레일

| 위치 | 역할 |
| --- | --- |
| 템플릿 생성 프롬프트 | 허용 슬롯, placeholder 형식, 출력 섹션을 제한한다. |
| 초안 검토 경고 | 한자/중국어 표현, 잘못된 placeholder를 감지한다. |
| `support/fallback-template-draft.md` | API 실패 시 데모 중단을 막는다. |
| `source_contract` | 시연 4에서 근거가 필요한 슬롯 목록을 지정한다. |
| `generation_guardrails` | 근거 문서에 있는 내용만 사용하도록 정책을 둔다. |
| `adapter_contracts` | 출력 단계가 검증 상태를 확인하도록 한다. |

이 스캐폴딩 덕분에 시연 4는 자유 생성이 아니라, 정해진 슬롯과 근거 정책 안에서 값을 채우는 단계가 된다.

## 오픈소스 사용 지점

| 도구 | 역할 |
| --- | --- |
| `python-dotenv` | `demos/.env`에서 API 설정을 읽는다. |
| `langchain_openai.ChatOpenAI` | Blackbox 호환 API를 호출한다. |
| `langchain_core.messages` | 시스템 메시지와 사용자 메시지를 구성한다. |
| `PyYAML` | 다음 단계에서 사용할 YAML 계약을 다룬다. |

## 정리

- LLM 초안은 검토 대상이고, 최종 계약은 사람이 고정한다.
- DocuMeta는 문서 구조, 필수 슬롯, 출력 계약, 검증 정책을 담는다.
- Reference chunk는 정답 문장이 아니라 슬롯을 채울 업무 근거다.
- 시연 4는 이 계약과 근거를 받아 빈 슬롯만 채운다.
