import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = Path(__file__).resolve().parent
INPUT_DIR = DEMO_DIR / "in"
SUPPORT_DIR = DEMO_DIR / "support"
OUTPUT_DIR = DEMO_DIR / "out"

SAMPLE_PATH = INPUT_DIR / "sample-official-notice.md"
FALLBACK_DRAFT_PATH = SUPPORT_DIR / "fallback-template-draft.md"
ENV_PATH = ROOT / "demos" / ".env"
PROMPT_PATH = OUTPUT_DIR / "00-template-generation-prompt.md"
REFERENCE_PROMPT_PATH = OUTPUT_DIR / "01-reference-ingest-prompt.md"
DRAFT_PATH = OUTPUT_DIR / "00-template-draft.md"
REFERENCE_OUTPUT_DIR = OUTPUT_DIR / "reference-docs"
BLACKBOX_API_BASE_URL = "https://api.blackbox.ai"
BLACKBOX_TIMEOUT_SECONDS = 30
REFERENCE_INGEST_PROMPT_PATH = SUPPORT_DIR / "reference-ingest-prompt.md"

load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class ReferenceChunkSpec:
    file_name: str
    source_prefix: str
    producer: str
    purpose: str
    evidence_label: str
    target_slots: tuple[str, ...]


def print_step(number: int, title: str) -> None:
    print(f"\n[{number}. {title}]")


def build_prompt(sample_document: str) -> str:
    prompt = f"""# 템플릿 초안 생성 프롬프트

아래 샘플 원문을 분석해서 출력 템플릿 설계 초안을 만들어라.

## 목표

- 반복되는 고정 블록과 매번 바뀌는 값을 분리한다.
- 바뀌는 값은 슬롯으로 정의한다.
- 표 구조는 표 계약으로 정의한다.
- 출력 순서는 블록 목록으로 정의한다.
- 큐엠디와 타이프스트 템플릿에는 문서 본문을 직접 쓰지 말고 주입 위치만 둔다.

## 출력 형식

Markdown으로 작성한다.
모든 설명과 제목은 한국어만 사용한다.
중국어, 일본어, 한자 표현을 절대 쓰지 않는다. 예: 候选, 同样, 正式, 惯例 금지.
영어 설명 문장을 쓰지 않는다.
섹션 제목은 반드시 아래 목록의 문장을 그대로 쓴다.
아래 허용 슬롯 이름 외의 새 슬롯을 만들지 않는다.
영향 항목은 scope에 포함해서 설명하고 impact 슬롯을 만들지 않는다.
수신과 경유를 섞지 않는다. recipient는 "전체 직원", via는 "각 부서장"이다.
contact에는 담당 부서, 담당자, 내선 번호를 함께 둔다.
표 계약은 YAML 형태로 작성하고 row_slot_matrix에 허용 슬롯 이름만 넣는다.
JSON, 반복 문법, 임의 키, 임의 슬롯을 쓰지 않는다.
placeholder는 반드시 중괄호 두 쌍 형식으로 쓴다. 예: {{{{ title }}}}
단일 중괄호 형식은 절대 쓰지 않는다. 예: {{ title }} 금지.
큐엠디와 타이프스트 예시는 완성 문장이 아니라 placeholder 중심의 짧은 골격만 쓴다.
타이프스트 예시는 `#let title = "{{ title }}"` 형식을 따른다.

`title`, `purpose_sentence`, `schedule`, `scope`, `required_actions`, `contact`, `attachment`, `recipient`, `via`, `sender_title`, `doc_number`, `date`, `officer`, `phone`, `postal_code`, `address`, `email`, `disclosure`

반드시 아래 섹션을 포함한다.

1. 슬롯 후보
2. table_contracts 후보
3. hwpx_template.blocks 후보
4. QMD 템플릿 placeholder 후보
5. TYP 템플릿 placeholder 후보
6. 사람이 검토해야 할 지점

## 샘플 공문

{sample_document}
"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_PATH.write_text(prompt, encoding="utf-8")
    return prompt


def call_llm_if_available(prompt: str) -> tuple[str, str]:
    # 템플릿 생성도 LLM이 도울 수 있음을 보여주는 어댑터 지점.
    api_key = os.getenv("API_KEY")
    api_model = os.getenv("API_MODEL", "blackboxai/x-ai/grok-code-fast-1:free")
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        if not api_key:
            return "", "fallback template draft (API_KEY 없음)"

        model = ChatOpenAI(
            model=api_model,
            api_key=api_key,
            base_url=BLACKBOX_API_BASE_URL,
            temperature=0,
            timeout=BLACKBOX_TIMEOUT_SECONDS,
        )
        system_prompt = (
            "너는 한국어 공문 템플릿 설계자다. "
            "응답에는 한국어와 코드 식별자만 쓴다. "
            "중국어, 일본어, 한자 표현을 절대 쓰지 않는다. "
            "placeholder는 반드시 {{ slot }} 형식만 쓴다."
        )
        response = model.invoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
        return str(response.content), f"Blackbox-compatible LLM API ({api_model})"
    except ModuleNotFoundError:
        return "", "fallback template draft (LLM API 의존성 없음)"
    except Exception as exc:
        return "", f"fallback template draft ({type(exc).__name__})"


def fallback_draft() -> str:
    return FALLBACK_DRAFT_PATH.read_text(encoding="utf-8").strip()


def write_draft(llm_output: str, source: str) -> None:
    draft = llm_output.strip() if llm_output.strip() else fallback_draft()
    review_warnings = []
    if re.search(r"[\u4e00-\u9fff]", draft):
        review_warnings.append("한자/중국어 표현이 섞여 있어 사람이 한국어 용어로 정리해야 함")
    if re.search(r"(?<!\{)\{ [a-z_]+ \}(?!\})|\{[a-z_]+\}", draft):
        review_warnings.append("단일 중괄호 placeholder가 있어 {{ slot }} 형식으로 정리해야 함")
    warning_text = "\n".join(f"- {warning}" for warning in review_warnings) or "- 특이사항 없음"
    content = f"""# LLM 템플릿 생성 결과

## 호출 결과

- {source}

## 초안 검토 경고

{warning_text}

{draft}
"""
    DRAFT_PATH.write_text(content, encoding="utf-8")


def find_line(sample_document: str, prefix: str) -> str:
    for line in sample_document.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith(prefix):
            return stripped_line.removeprefix(prefix).strip()
    raise ValueError(f"샘플 원문에서 reference chunk를 만들 수 없습니다: {prefix}")


def reference_chunk_specs() -> list[ReferenceChunkSpec]:
    # 강의용 ingest 설계도: 어떤 원문 조각을 어떤 검색 chunk와 슬롯 근거로 분리할지 보여준다.
    return [
        ReferenceChunkSpec("work-plan.md", "- 일시:", "정보화지원팀 운영 담당자", "schedule 슬롯 근거", "점검 작업계획서", ("schedule",)),
        ReferenceChunkSpec("impact.md", "- 대상과 영향 범위:", "정보화지원팀 서비스 담당자", "scope 슬롯 근거", "영향범위", ("scope",)),
        ReferenceChunkSpec(
            "previous.md",
            "- 사전 조치:",
            "총무팀 공문 담당자",
            "required_actions와 contact 슬롯 근거",
            "이전안내문",
            ("required_actions", "contact"),
        ),
        ReferenceChunkSpec(
            "mail.md",
            "- 메일 서비스 개편은",
            "정보화지원팀 서비스 담당자",
            "현재 공문과 무관한 문서가 검색에서 제외되는지 확인",
            "무관문서",
            (),
        ),
    ]


def write_reference_ingest_prompt(sample_document: str) -> None:
    ingest_prompt = REFERENCE_INGEST_PROMPT_PATH.read_text(encoding="utf-8").strip()
    content = f"""{ingest_prompt}

## 샘플 원문

{sample_document}
"""
    REFERENCE_PROMPT_PATH.write_text(content, encoding="utf-8")


def evidence_for_spec(sample_document: str, spec: ReferenceChunkSpec) -> str:
    evidence = find_line(sample_document, spec.source_prefix)
    if spec.file_name == "previous.md":
        contact = find_line(sample_document, "- 문의:")
        return f"{evidence}. 문의처 {contact}."
    if spec.file_name == "mail.md":
        return "메일 서비스 개편은 " + evidence.split("이며,", 1)[0].strip()
    return evidence


def build_reference_doc(sample_document: str, spec: ReferenceChunkSpec) -> str:
    target_slots = ", ".join(spec.target_slots) if spec.target_slots else "없음"
    evidence = evidence_for_spec(sample_document, spec)
    return f"""RAG 세트 생성: 시연 3 ingest step
원천: sample-official-notice.md / {spec.source_prefix}
업무상 작성 주체: {spec.producer}
사용 목적: {spec.purpose}
대상 슬롯: {target_slots}

{spec.evidence_label}: {evidence}
"""


def write_reference_docs(sample_document: str) -> list[Path]:
    # 시연 4의 RAG가 읽을 근거 chunk를 시연 3의 원천 문서에서 만든다.
    reference_docs = {
        spec.file_name: build_reference_doc(sample_document, spec)
        for spec in reference_chunk_specs()
    }

    REFERENCE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written_paths = []
    for file_name, content in reference_docs.items():
        reference_path = REFERENCE_OUTPUT_DIR / file_name
        reference_path.write_text(content.strip() + "\n", encoding="utf-8")
        written_paths.append(reference_path)
    return written_paths


def main() -> None:
    print("[템플릿 초안 생성 데모]")

    print_step(1, "샘플 공문 로드")
    sample_document = SAMPLE_PATH.read_text(encoding="utf-8").strip()
    print(f"- 파일: {SAMPLE_PATH}")
    print(f"- 샘플 길이: {len(sample_document)} chars")

    print_step(2, "프롬프트 구성")
    prompt = build_prompt(sample_document)
    print(f"- 저장 위치: {PROMPT_PATH}")
    print(f"- 프롬프트 길이: {len(prompt)} chars")

    print_step(3, "LLM 호출")
    llm_output, source = call_llm_if_available(prompt)
    print(f"- 호출 결과: {source}")
    print("- 응답 상태:", "LLM 응답 수신" if llm_output else "fallback 사용")

    print_step(4, "템플릿 초안 저장")
    write_draft(llm_output, source)
    print(f"- 초안 결과: {DRAFT_PATH}")
    print("- 검토 기준: 한자/외국어 섞임, placeholder 누락, 슬롯명 불일치 확인")

    print_step(5, "RAG reference 생성")
    write_reference_ingest_prompt(sample_document)
    print(f"- ingest 규칙 프롬프트: {REFERENCE_PROMPT_PATH}")
    reference_paths = write_reference_docs(sample_document)
    for reference_path in reference_paths:
        print(f"- reference: {reference_path}")

    print("- 다음 단계: 사람이 초안과 reference를 검토해서 시연 4 입력 계약으로 고정")


if __name__ == "__main__":
    main()
