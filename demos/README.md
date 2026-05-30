# 시연 폴더

각 시연은 번호 파일이 아니라 폴더 단위로 묶는다. 강의 노트와 해당 시연에서 쓰는 입력, 실행 파일을 같은 폴더 안에서 본다.

## 01-chatgpt-direct: 시연 1 - 챗지피티에 바로 맡기면

- [lecture-notes.md](01-chatgpt-direct/lecture-notes.md)
- [instructor-notes.md](01-chatgpt-direct/instructor-notes.md)
- 목적: 조건 없이 ChatGPT에 요청했을 때 문서 조건과 근거가 어떻게 흔들리는지 보여준다.

## 02-short-documeta: 시연 2 - 짧은 docu meta만 붙여도

- [lecture-notes.md](02-short-documeta/lecture-notes.md)
- [instructor-notes.md](02-short-documeta/instructor-notes.md)
- [documeta-practice-template.yaml](02-short-documeta/documeta-practice-template.yaml)
- 목적: 같은 요청에 짧은 DocuMeta를 붙여 문서 유형, 필수 슬롯, 검증 규칙을 분리한다.

## 03-documeta-completion: 시연 3 - DocuMeta 프레임 생성

```bash
cd demos/03-documeta-completion
uv run python generate-template-draft.py
```

- [notes.md](03-documeta-completion/notes.md)
- [generate-template-draft.py](03-documeta-completion/generate-template-draft.py)
- `in/`: 샘플 원문
- `out/`: DocuMeta 프레임과 RAG reference chunk
- 목적: 샘플 공문에서 DocuMeta 프레임, 출력 템플릿 계약, 다음 단계의 RAG reference chunk를 생성한다.

## 04-build-writing: 시연 4 - RAG와 글쓰기 빌드

```bash
cd demos/04-build-writing
uv run python rag-slot-flow.py
uv run python output-package.py
```

- [notes.md](04-build-writing/notes.md)
- [rag-slot-flow.py](04-build-writing/rag-slot-flow.py)
- [output-package.py](04-build-writing/output-package.py)
- `in/`: DocuMeta, query, 출력 템플릿
- `out/`: 완성 DocuMeta와 최종 출력 패키지
- 목적: 시연 3에서 생성한 RAG reference chunk로 DocuMeta 슬롯을 완성하고, 완성형 DocuMeta를 Quarto, Typst, HWPX 출력 패키지로 변환한다.

현재 환경 기준으로 템플릿 초안 생성, RAG 슬롯 완성, 출력 패키징은 모두 저장소 루트의 `uv` 환경에서 실행한다. `uv sync`가 Python 3.11-3.12 가상환경과 LangChain/FAISS 의존성을 준비한다.

## 실행 준비

저장소 루트에서 운영체제에 맞는 준비 스크립트를 먼저 실행한다.

Linux(Ubuntu/Debian 계열):

```bash
./scripts/setup-demo-linux.sh
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-demo-windows.ps1
```

준비 스크립트는 `uv`, `quarto`, `typst`를 설치하거나 확인하고, `uv sync`를 실행한 뒤 `demos/.env`를 만든다.

수동 준비가 필요하면 아래 명령을 실행한다.

```bash
uv sync
cp demos/.env.example demos/.env
uv run python --version
quarto --version
typst --version
```

`demos/.env`에는 Blackbox 호환 API 키와 모델명을 넣는다. 시연 4의 HWPX까지 실제 생성기로 만들려면 `HWPX_GENERATOR_PATH`에 로컬 HWPX 생성기 Python 파일 경로를 지정한다. 지정한 생성기가 없으면 강의 흐름 확인용 fallback HWPX 패키지를 만든다.

Quarto HTML과 Typst PDF 출력은 Python 패키지가 아니라 외부 CLI를 사용하므로 `quarto`와 `typst` 명령이 PATH에서 실행되어야 한다.

## 전체 실행 순서

```bash
uv run python demos/03-documeta-completion/generate-template-draft.py
uv run python demos/04-build-writing/rag-slot-flow.py
uv run python demos/04-build-writing/output-package.py
```

생성 결과는 아래에서 확인한다.

- `demos/03-documeta-completion/out/`
- `demos/04-build-writing/out/final-documeta.yaml`
- `demos/04-build-writing/out/final-package/`
