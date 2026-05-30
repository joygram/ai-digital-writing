# 시연 4: RAG와 글쓰기 빌드

## 목표

시연 3에서 만든 DocuMeta 프레임에 참조 문서 근거를 채우고, 하나의 DocuMeta에서 QMD, HTML, TYP, PDF, HWPX 출력 패키지를 만든다.

이 단계의 핵심은 LLM이 처음부터 문서를 새로 쓰는 것이 아니다.
이미 준비된 문서 계약과 참조 자료를 함께 사용해서 비어 있는 슬롯만 채우고, 그 값이 어떤 근거에서 왔는지 남긴다.

## 실행

저장소 루트에서 실행할 때:

```bash
uv run python demos/04-build-writing/rag-slot-flow.py
uv run python demos/04-build-writing/output-package.py
```

`demos/04-build-writing` 폴더 안에서 실행할 때:

```bash
uv run python rag-slot-flow.py
uv run python output-package.py
```

## 준비 파일

| 구분 | 파일 |
| --- | --- |
| DocuMeta 프레임 | `demos/04-build-writing/in/documeta.yaml` |
| 검색 질의 | `demos/04-build-writing/in/query.txt` |
| 시연 3에서 생성한 RAG reference chunk | `demos/03-documeta-completion/out/reference-docs/*.md` |
| QMD 템플릿 | `demos/04-build-writing/in/templates/official-notice.qmd.template` |
| TYP 템플릿 | `demos/04-build-writing/in/templates/official-notice.typ.template` |
| HWPX 보조 어댑터 | `demos/04-build-writing/support/hwpx_adapter.py` |
| API 설정 | `demos/.env` |

`in/`은 실행 전에 준비된 입력 자료다.
`out/`은 실행 후 생성되는 결과를 모아 두는 위치다.

`in/documeta.yaml`은 문서의 구조와 출력 계약을 담고 있다.
시연 4에서는 이 구조를 다시 만들지 않고, 비어 있는 슬롯만 RAG 검색 결과로 완성한다.

## 전체 흐름

```text
reference-docs/*.md
  -> LangChain Document + metadata
  -> FAISS retriever
  -> LLM 프롬프트
  -> 완성 DocuMeta
  -> QMD / HTML / TYP / PDF / HWPX
```

| 단계 | 하는 일 | 결과 |
| --- | --- | --- |
| Reference ingest | Markdown reference 파일을 `Document + metadata`로 바꾼다. | 검색 가능한 문서 목록 |
| FAISS retriever | `query.txt`와 가까운 참조 문서를 고른다. | 관련 근거 chunk |
| LLM | DocuMeta 프레임과 검색 근거를 읽고 빈 슬롯을 채운다. | 완성된 `slots` |
| 검증/감사 매핑 | 슬롯 값이 어느 근거 chunk에서 왔는지 연결한다. | `slot_source_map` |
| 출력 패키징 | 완성 DocuMeta를 템플릿에 주입한다. | QMD, HTML, TYP, PDF, HWPX |

## 참조 문서

시연 3은 샘플 공문 안에 섞여 있던 업무 메모를 작은 reference chunk로 분리한다.
시연 4는 그 결과물인 `demos/03-documeta-completion/out/reference-docs/*.md`를 검색한다.

| 업무 자료 | 이 시연에서 생성되는 chunk | 역할 |
| --- | --- | --- |
| 작업계획서 | `work-plan.md` | 점검 일시 근거 |
| 영향 범위 메모 | `impact.md` | 영향 범위 근거 |
| 이전 안내문 | `previous.md` | 사전 조치와 문의처 근거 |
| 메일 개편 메모 | `mail.md` | 현재 공문과 무관한 문서 |

`mail.md`는 관련 없는 자료가 함께 있을 때 retriever가 제외해야 하는 반례다.
검색 결과에는 `impact`, `previous`, `work-plan`이 들어가고, `mail`은 빠지는 것이 정상이다.

## 실행 후 확인

`rag-slot-flow.py` 실행 후 다음 파일이 생성된다.

| 결과 | 파일 |
| --- | --- |
| Reference ingest 보고서 | `demos/04-build-writing/out/04-reference-ingest-report.md` |
| LLM 입력 프롬프트 | `demos/04-build-writing/out/04-rag-llm-prompt.md` |
| 완성 DocuMeta | `demos/04-build-writing/out/final-documeta.yaml` |
| 검증 보고서 | `demos/04-build-writing/out/04-rag-validation-report.md` |

`output-package.py` 실행 후 다음 파일이 생성된다.

| 결과 | 파일 |
| --- | --- |
| QMD | `demos/04-build-writing/out/final-package/system-notice-documeta-generated.qmd` |
| HTML | `demos/04-build-writing/out/final-package/system-notice-documeta-generated.html` |
| TYP | `demos/04-build-writing/out/final-package/system-notice-documeta-generated.typ` |
| PDF | `demos/04-build-writing/out/final-package/system-notice-documeta-generated.pdf` |
| HWPX | `demos/04-build-writing/out/final-package/system-notice-documeta-generated.hwpx` |
| 출력 요약 | `demos/04-build-writing/out/final-package/output-summary.md` |

## 핵심 확인 지점

| 파일 | 확인할 부분 | 의미 |
| --- | --- | --- |
| `in/documeta.yaml` | `slots`의 빈 값 | 이 단계에서는 빈 슬롯만 채운다. |
| `in/documeta.yaml` | `source_contract.required_slots` | 근거 추적이 필요한 슬롯이 계약에 명시되어 있다. |
| `out/04-reference-ingest-report.md` | `doc_id`, `chunk_id`, `evidence_text` | 검색에 들어간 문서 단위를 확인한다. |
| `out/04-rag-llm-prompt.md` | `Retrieved reference documents` | LLM 입력에는 retriever가 고른 근거만 붙는다. |
| `out/final-documeta.yaml` | `retrieved_reference_ids` | 실제 검색된 reference 문서 id를 확인한다. |
| `out/final-documeta.yaml` | `slot_source_map` | 완성 슬롯이 어느 chunk에서 왔는지 확인한다. |
| `out/final-package/` | 생성된 출력 파일 | 같은 DocuMeta에서 여러 형식이 나온다. |

## 완성되는 슬롯

retriever가 고르는 주요 근거는 다음과 같다.

| 문서 id | 원문 조각 | 사용 슬롯 |
| --- | --- | --- |
| `work-plan` | `2026년 6월 3일 19:00-22:00 점검` | `schedule` |
| `impact` | `전자결재와 문서 열람 제한` | `scope` |
| `previous` | `작성 중 문서 저장, 긴급 결재 사전 처리. 문의처 정보화지원팀 1234` | `required_actions`, `contact` |

LLM은 이 근거와 DocuMeta 프레임을 함께 읽고 다음 슬롯을 완성한다.

| 슬롯 | 예시 값 | 근거 |
| --- | --- | --- |
| `title` | 내부 업무시스템 정기점검 안내 | 문서 유형과 검색 근거 |
| `purpose_sentence` | 내부 업무시스템 정기점검 목적 문장 | 공문 본문 문장 구성 |
| `schedule` | 2026년 6월 3일 19:00-22:00 | `work-plan` |
| `scope` | 전자결재와 문서 열람 제한 | `impact` |
| `required_actions` | 작성 중 문서 저장, 긴급 결재 사전 처리 | `previous` |
| `contact` | 정보화지원팀 1234 | `previous` |

최종 문서는 단순 복사 결과가 아니다.
근거 문서에서 가져온 값이 DocuMeta의 공문 구조와 출력 템플릿 계약 안에 들어가면서 새 문서가 만들어진다.

## 검증 기준

다음 조건을 만족하면 정상 흐름이다.

- `retrieved_reference_ids`에 `impact`, `previous`, `work-plan`이 있다.
- `retrieved_reference_ids`에 `mail`은 없다.
- `slot_source_map.schedule`은 `work-plan`을 가리킨다.
- `slot_source_map.scope`는 `impact`를 가리킨다.
- `slot_source_map.required_actions`와 `slot_source_map.contact`는 `previous`를 가리킨다.
- 실행 로그에 `validation: PASS`가 나온다.
- `output_status`가 `출력 가능`이다.
- 최종 QMD/HTML/PDF/HWPX 파일이 `out/final-package/`에 생성된다.

우편번호처럼 앞자리가 0인 값은 숫자가 아니라 문자열로 유지되어야 한다.
예: `04524`

## 가드레일

이 시연의 가드레일은 LLM 응답 이후에 작동하는 검증 틀이다.
LLM이 값을 만들더라도 근거 연결과 필수 계약을 통과해야 출력으로 넘어간다.

| 위치 | 역할 |
| --- | --- |
| `source_contract.required_slots` | 근거 추적이 필요한 슬롯을 지정한다. |
| `generation_guardrails.source_policy` | 근거 문서에 있는 내용만 사용하도록 정책을 둔다. |
| FAISS retriever | 무관 문서를 제외하고 관련 문서만 LLM에 전달한다. |
| `validate()` | DocuMeta 필수 구조가 유지되는지 검사한다. |
| `slot_source_map` | 완성 슬롯과 근거 chunk를 연결한다. |
| `output_status` | 검증 통과 여부를 출력 단계에 전달한다. |
| `assert_output_allowed()` | `보류` 상태의 문서는 출력 패키징을 중단한다. |

따라서 전체 순서는 `검색 -> 생성 -> 근거 매핑 -> 검증 -> 출력`이다.
LLM은 문장을 만들 수 있지만, 출력 여부는 검증 단계가 결정한다.

## 오픈소스 사용 지점

| 도구 | 역할 |
| --- | --- |
| `langchain_core.documents.Document` | 참조 문서와 metadata를 묶는다. |
| `langchain_core.embeddings.Embeddings` | FAISS용 벡터 인터페이스를 제공한다. |
| `langchain_community.vectorstores.FAISS` | 질의와 가까운 참조 문서를 찾는다. |
| `PromptTemplate`, `RunnableLambda`, `RunnablePassthrough` | 검색 결과와 DocuMeta를 LLM 입력으로 연결한다. |
| `langchain_openai.ChatOpenAI` | Blackbox 호환 API를 호출한다. |
| `StrOutputParser`, `PyYAML` | LLM 응답을 문자열과 YAML로 처리한다. |
| Quarto CLI | QMD를 HTML로 렌더링한다. |
| Typst CLI | TYP를 PDF로 컴파일한다. |
| `pyhwpxlib` | HWPX 파일을 만든다. |
| DeukHwp VSIX | 생성된 HWPX 파일을 VS Code에서 열어 확인한다. |

## 정리

- Ingest는 reference 파일을 검색 가능한 `Document + metadata`로 바꾸는 단계다.
- Retriever는 관련 근거를 고르고, LLM은 그 근거 안에서 슬롯을 채운다.
- 검증은 값이 채워졌는지뿐 아니라 근거 매핑이 남았는지 확인한다.
- 출력은 같은 DocuMeta 계약에서 여러 형식으로 갈라진다.
