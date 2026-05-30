import os
import warnings
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI

ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = Path(__file__).resolve().parent
INPUT_DIR = DEMO_DIR / "in"
OUTPUT_DIR = DEMO_DIR / "out"
DOCUMETA_DEMO_DIR = ROOT / "demos" / "03-documeta-completion"

DOCUMETA_PATH = INPUT_DIR / "documeta.yaml"
QUERY_PATH = INPUT_DIR / "query.txt"
REFERENCE_DOCS_DIR = DOCUMETA_DEMO_DIR / "out" / "reference-docs"
ENV_PATH = ROOT / "demos" / ".env"
PROMPT_PATH = OUTPUT_DIR / "04-rag-llm-prompt.md"
FINAL_DOCUMETA_PATH = OUTPUT_DIR / "final-documeta.yaml"
VALIDATION_REPORT_PATH = OUTPUT_DIR / "04-rag-validation-report.md"
INGEST_REPORT_PATH = OUTPUT_DIR / "04-reference-ingest-report.md"

BLACKBOX_API_BASE_URL = "https://api.blackbox.ai"
BLACKBOX_TIMEOUT_SECONDS = 30
REFERENCE_DOCUMENT_CONTEXT = {
    "work-plan": {
        "prepared_by": "시연 3 ingest step",
        "producer": "정보화지원팀 운영 담당자",
        "context": "시스템 점검 전 내부 작업계획서에서 발췌한 일정 근거",
        "purpose": "schedule 슬롯을 채우기 위한 1차 근거",
    },
    "impact": {
        "prepared_by": "시연 3 ingest step",
        "producer": "정보화지원팀 서비스 담당자",
        "context": "점검 중 제한되는 업무시스템 범위를 정리한 영향 범위 메모",
        "purpose": "scope 슬롯을 채우기 위한 1차 근거",
    },
    "previous": {
        "prepared_by": "시연 3 ingest step",
        "producer": "총무팀 공문 담당자",
        "context": "이전 안내문에서 재사용 가능한 사전 조치와 문의처 문구를 발췌",
        "purpose": "required_actions와 contact 슬롯을 채우기 위한 참고 근거",
    },
    "mail": {
        "prepared_by": "시연 3 ingest step",
        "producer": "정보화지원팀 서비스 담당자",
        "context": "메일 서비스 개편 별도 공지 메모",
        "purpose": "현재 공문과 무관한 문서가 검색에서 제외되는지 보여주는 반례",
    },
}

load_dotenv(ENV_PATH)


class KeywordEmbeddings(Embeddings):
    """Small deterministic embedding so the FAISS demo is stable."""

    # retriever는 시연 3에서 확정한 reference-docs/*.md 중에서 점검 일정, 영향 범위, 조치, 문의처 근거를 찾는다.
    # 실제 제품에서는 OpenAI/Hugging Face embedding 등 다양한 모델을 쓰지만, 강연에서는 안정적 결과를 위해 키워드 벡터를 쓴다.
    keywords = ["점검", "작업계획서", "영향범위", "이전안내문", "전자결재", "문서", "열람", "조치", "문의처", "저장", "긴급", "결재"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [1.0 if keyword in text else 0.0 for keyword in self.keywords]
        magnitude = sum(value * value for value in vector) ** 0.5
        return [value / magnitude for value in vector] if magnitude else vector


def reference_paths() -> list[Path]:
    if not REFERENCE_DOCS_DIR.exists() or not list(REFERENCE_DOCS_DIR.glob("*.md")):
        raise FileNotFoundError(
            f"{REFERENCE_DOCS_DIR}가 없습니다. 먼저 `uv run python demos/03-documeta-completion/generate-template-draft.py`를 실행하세요."
        )
    return sorted(REFERENCE_DOCS_DIR.glob("*.md"))


def document_from_reference(path: Path) -> Document:
    document_id = path.stem
    content = path.read_text(encoding="utf-8").strip()
    evidence_text = content.rsplit("\n\n", 1)[-1].strip()
    reference_context = REFERENCE_DOCUMENT_CONTEXT.get(document_id, {})
    return Document(
        page_content=content,
        metadata={
            "id": document_id,
            "doc_id": document_id,
            "chunk_id": f"{document_id}-001",
            "source_path": str(path.relative_to(ROOT)),
            "evidence_text": evidence_text,
            **reference_context,
        },
    )


def write_ingest_report(documents: list[Document]) -> None:
    report_rows = "\n".join(
        "\n".join(
            [
                f"## {doc.metadata['doc_id']}",
                "",
                f"- source_path: {doc.metadata['source_path']}",
                f"- chunk_id: {doc.metadata['chunk_id']}",
                f"- 작성 주체: {doc.metadata.get('producer', '')}",
                f"- 사용 목적: {doc.metadata.get('purpose', '')}",
                f"- evidence_text: {doc.metadata['evidence_text']}",
                "",
            ]
        )
        for doc in documents
    )
    INGEST_REPORT_PATH.write_text(
        f"""# 시연 4 Reference Ingest Report

시연 4는 시연 3이 만든 Markdown reference chunk를 LangChain `Document`로 변환한 뒤 FAISS에 넣는다.
이 보고서는 파일 ingest 결과와 각 chunk metadata를 확인하기 위한 강의용 출력이다.

{report_rows}
""",
        encoding="utf-8",
    )


def ingest_reference_documents() -> list[Document]:
    # RAG ingest adapter: reference Markdown 파일을 LangChain Document + metadata로 바꾼다.
    documents = []
    for path in reference_paths():
        documents.append(document_from_reference(path))
    write_ingest_report(documents)
    return documents


def build_retriever(documents: list[Document]):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from langchain_community.vectorstores import FAISS

    # FAISS가 query.txt와 가까운 근거 3개를 골라 LLM 프롬프트에 넘긴다.
    return FAISS.from_documents(documents, KeywordEmbeddings()).as_retriever(search_kwargs={"k": 3})


def format_docs(documents: list[Document]) -> str:
    # 검색된 Document 객체를 LLM이 읽기 쉬운 근거 목록 텍스트로 바꾼다.
    return "\n".join(
        "\n".join(
            [
                f"- 문서 id: {doc.metadata['id']}",
                f"  RAG 세트 준비: {doc.metadata.get('prepared_by', '미상')}",
                f"  작성 주체: {doc.metadata.get('producer', '미상')}",
                f"  작성 맥락: {doc.metadata.get('context', '미상')}",
                f"  시연 역할: {doc.metadata.get('purpose', '미상')}",
                f"  원문 조각: {doc.page_content}",
            ]
        )
        for doc in documents
    )


def extract_yaml(text: str) -> dict:
    # LLM 응답은 최종 DocuMeta YAML, 문자열 응답을 dict로.
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    parsed = yaml.safe_load(raw)
    if not isinstance(parsed, dict):
        raise ValueError("LLM output is not a YAML object")
    return parsed


def validate(documeta: dict) -> list[str]:
    # 출력 패키징으로 넘기기 전에 공문에 필요한 핵심 슬롯이 채워졌는지만 확인한다.
    required_slots = ["title", "purpose_sentence", "schedule", "scope", "required_actions", "contact"]
    errors = [slot for slot in required_slots if not documeta.get("slots", {}).get(slot)]
    return [f"필수 슬롯 누락: {slot}" for slot in errors]


def restore_contracts(completed_documeta: dict, frame: dict) -> dict:
    # LLM이 출력 중 계약 영역을 빠뜨려도 감사 매핑과 출력 계약은 원본 프레임에서 유지한다.
    for key in ["source_contract", "table_contracts", "hwpx_template", "adapter_contracts", "output_targets"]:
        completed_documeta.setdefault(key, frame.get(key))
    return completed_documeta


def build_slot_source_map(documeta: dict, retrieved_docs: list[Document]) -> dict:
    # 감사 매핑: 완성된 슬롯이 어떤 FAISS 검색 chunk에서 왔는지 metadata로 남긴다.
    slots = documeta.get("slots", {})
    required_slots = documeta.get("source_contract", {}).get("required_slots", [])
    slot_keywords = {
        "schedule": ["작업계획서", "19:00", "22:00"],
        "scope": ["영향범위", "전자결재", "열람"],
        "required_actions": ["저장", "긴급", "사전 처리"],
        "contact": ["문의처", "정보화지원팀", "1234"],
    }
    source_map = {}
    for slot in required_slots:
        value = str(slots.get(slot, "")).strip()
        keywords = slot_keywords.get(slot, [])
        matched_doc = next(
            (
                doc
                for doc in retrieved_docs
                if (value and value in doc.metadata.get("evidence_text", doc.page_content))
                or any(keyword in doc.metadata.get("evidence_text", doc.page_content) for keyword in keywords)
            ),
            None,
        )
        if matched_doc:
            source_map[slot] = {
                "value": value,
                "doc_id": matched_doc.metadata["doc_id"],
                "chunk_id": matched_doc.metadata["chunk_id"],
                "source_path": matched_doc.metadata["source_path"],
                "prepared_by": matched_doc.metadata.get("prepared_by", ""),
                "producer": matched_doc.metadata.get("producer", ""),
                "context": matched_doc.metadata.get("context", ""),
            }
    return source_map


def validate_slot_source_map(documeta: dict, source_map: dict) -> list[str]:
    required_slots = documeta.get("source_contract", {}).get("required_slots", [])
    return [f"감사 매핑 누락: {slot}" for slot in required_slots if slot not in source_map]


def write_outputs(documeta: dict, retrieved_docs: list[Document], prompt_text: str, errors: list[str]) -> list[str]:
    # 시연 4의 다음 단계(output-package.py)가 읽을 final-documeta.yaml과 검증 보고서 작성.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    documeta["retrieved_reference_ids"] = [doc.metadata["id"] for doc in retrieved_docs]
    documeta["slot_source_map"] = build_slot_source_map(documeta, retrieved_docs)
    all_errors = errors + validate_slot_source_map(documeta, documeta["slot_source_map"])
    documeta["output_status"] = "출력 가능" if not all_errors else "보류"
    documeta["validation"] = {"status": documeta["output_status"], "errors": all_errors}

    PROMPT_PATH.write_text(prompt_text, encoding="utf-8")
    FINAL_DOCUMETA_PATH.write_text(yaml.safe_dump(documeta, allow_unicode=True, sort_keys=False), encoding="utf-8")

    slots = documeta["slots"]
    report = f"""# 시연 4 RAG 검증 보고서

## 검색 근거

{format_docs(retrieved_docs)}

## 핵심 슬롯

- title: {slots.get("title")}
- schedule: {slots.get("schedule")}
- scope: {slots.get("scope")}
- required_actions: {slots.get("required_actions")}
- contact: {slots.get("contact")}

## 감사 매핑

{yaml.safe_dump(documeta["slot_source_map"], allow_unicode=True, sort_keys=False)}

## 검증 결과

- status: {"PASS" if not all_errors else "NEEDS_FIX"}
"""
    VALIDATION_REPORT_PATH.write_text(report, encoding="utf-8")
    return all_errors


def main() -> None:
    print("[시연 4 RAG 슬롯 완성 파이프라인]")
    print("documents -> FAISS retriever -> PromptTemplate -> ChatOpenAI -> StrOutputParser -> YAML")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = yaml.safe_load(DOCUMETA_PATH.read_text(encoding="utf-8"))
    documeta = yaml.safe_dump(frame, allow_unicode=True, sort_keys=False)
    query = QUERY_PATH.read_text(encoding="utf-8").strip()
    # in/query.txt는 "어떤 근거를 찾을지"를 표현한다. 여기서는 점검 일정, 영향 범위, 조치, 문의처를 찾는다.
    reference_documents = ingest_reference_documents()
    print(f"- reference ingest: {len(reference_documents)} chunks from {REFERENCE_DOCS_DIR}")
    print(f"- ingest report: {INGEST_REPORT_PATH}")
    retriever = build_retriever(reference_documents)
    llm = ChatOpenAI(
        model=os.getenv("API_MODEL", "blackboxai/x-ai/grok-code-fast-1:free"),
        api_key=os.environ["API_KEY"],
        base_url=BLACKBOX_API_BASE_URL,
        temperature=0,
        timeout=BLACKBOX_TIMEOUT_SECONDS,
    )
    prompt = PromptTemplate.from_template(
        """Fill the empty DocuMeta slots using only the retrieved reference documents.
Return YAML only. Keep table_contracts, hwpx_template, and adapter_contracts unchanged.
Quote every string value.
Do not add raw reference document content fields.

DocuMeta frame:
```yaml
{documeta}
```

Retrieved reference documents:
{reference_docs}
"""
    )

    retrieved_docs: list[Document] = []

    def remember_docs(docs: list[Document]) -> str:
        # 이 파일에서만 LangChain 체인을 쓰며, 검색된 근거를 화면 출력과 검증 보고서에 재사용하려고 저장한다.
        retrieved_docs[:] = docs
        return format_docs(docs)

    # 화면에서 설명할 핵심 파이프라인:
    # LangChain은 아래 RAG 조립부에만 붙는다. output-package.py는 DocuMeta를 파일로 빌드하는 별도 단계다.
    # 1. in/documeta.yaml은 그대로 프롬프트에 들어간다.
    # 2. in/query.txt로 시연 3에서 확정한 reference-docs/*.md를 FAISS 검색한다.
    # 3. DocuMeta frame + retrieved reference documents가 PromptTemplate에서 합쳐진다.
    # 4. ChatOpenAI가 검색된 근거 안에서 빈 슬롯을 채운 YAML을 만든다.
    # 5. StrOutputParser가 메시지 객체를 문자열로 꺼낸다.
    pipeline = (
        {
            "documeta": RunnablePassthrough(),
            "reference_docs": RunnableLambda(lambda _: query) | retriever | RunnableLambda(remember_docs),
        }
        | prompt
        # 강의 중 열어볼 수 있게 실제 LLM 입력 프롬프트를 파일로 저장한다.
        | RunnableLambda(lambda prompt_value: (PROMPT_PATH.write_text(prompt_value.to_string(), encoding="utf-8"), prompt_value)[1])
        | llm
        | StrOutputParser()
    )

    # 체인 입력은 미완성 DocuMeta 프레임이고, 체인 출력은 슬롯이 채워진 DocuMeta YAML 문자열이다.
    llm_text = pipeline.invoke(documeta)
    completed_documeta = restore_contracts(extract_yaml(llm_text), frame)
    errors = validate(completed_documeta)
    errors = write_outputs(completed_documeta, retrieved_docs, PROMPT_PATH.read_text(encoding="utf-8"), errors)

    slots = completed_documeta["slots"]
    print("\n[검색 근거]")
    for doc in retrieved_docs:
        print(f"- {doc.metadata['id']}: {doc.page_content}")
    print("\n[완성 슬롯]")
    for slot in ["title", "schedule", "scope", "required_actions", "contact"]:
        print(f"- {slot}: {slots.get(slot)}")
    print("\n[FAISS 검색 문서 id]")
    for doc in retrieved_docs:
        print(f"- {doc.metadata['id']}")
    print("\n[감사 매핑: 슬롯 -> FAISS chunk]")
    for slot, source in completed_documeta.get("slot_source_map", {}).items():
        print(f"- {slot}: {source['doc_id']} / {source['chunk_id']}")
    print("\n[출력]")
    print(f"- prompt: {PROMPT_PATH}")
    print(f"- final_documeta: {FINAL_DOCUMETA_PATH}")
    print(f"- validation: {'PASS' if not errors else 'NEEDS_FIX'}")


if __name__ == "__main__":
    main()
