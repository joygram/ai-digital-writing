# 오픈소스로 만드는 AI 디지털 글쓰기

이 저장소는 **AI 디지털 글쓰기 강의의 공개 자료**를 담고 있다.

강의의 목적은 AI가 문장을 대신 쓰는 수준을 넘어, 조직 문서가 만들어지는 조건과 근거, 검증, 출력 과정을 공개된 도구와 재현 가능한 예제로 설명하는 것이다. 발표 자료와 데모 코드는 DocuMeta, RAG, Quarto, Typst, HWPX 출력 흐름을 하나의 문서 작성 파이프라인으로 보여준다.

## 공개 프레젠테이션

- GitHub Pages: <https://joygram.github.io/ai-digital-writing/>
- 발표 원고: [docs/presentation.md](docs/presentation.md)

이 프레젠테이션은 다음 내용을 공개한다.

1. 업무 문서가 문장만으로 완성되지 않는 이유
2. 문서를 이루는 대상, 형식, 근거, 출력 조건
3. DocuMeta로 문서의 필수 슬롯과 검증 규칙을 분리하는 방법
4. RAG로 근거 문서를 연결하고 감사 가능한 슬롯 출처를 남기는 방법
5. Quarto, Typst, HWPX로 최종 산출물을 만드는 공개 도구 기반 흐름

## 저장소 구성

## 지금 봐야 할 파일

1. [docs/timetable.md](docs/timetable.md)  
   2시간 전체 시간표

2. [docs/presentation.md](docs/presentation.md)  
   발표 본문 원고

3. [docs/instructor-script.md](docs/instructor-script.md)  
   강의자가 실제로 읽거나 참고할 진행 스크립트

4. [demos/README.md](demos/README.md)  
   시연별 폴더와 실행 순서

## 시연에서 직접 쓰는 파일

### 시연 1: 챗지피티에 바로 맡기면

- [demos/01-chatgpt-direct/lecture-notes.md](demos/01-chatgpt-direct/lecture-notes.md)  
  ChatGPT에 조건 없이 요청하는 복붙용 입력
- [demos/01-chatgpt-direct/instructor-notes.md](demos/01-chatgpt-direct/instructor-notes.md)  
  실습 1 강의자 메모

### 시연 2: 짧은 docu meta만 붙여도

- [demos/02-short-documeta/lecture-notes.md](demos/02-short-documeta/lecture-notes.md)  
  DocuMeta 예시를 붙이는 복붙용 입력
- [demos/02-short-documeta/instructor-notes.md](demos/02-short-documeta/instructor-notes.md)  
  실습 2 강의자 메모
- [demos/02-short-documeta/documeta-practice-template.yaml](demos/02-short-documeta/documeta-practice-template.yaml)  
  짧은 DocuMeta 예시

### 시연 3: DocuMeta 프레임 생성

- [demos/03-documeta-completion/notes.md](demos/03-documeta-completion/notes.md)  
  템플릿 초안 생성, DocuMeta 프레임, RAG reference chunk 생성 노트
- [demos/03-documeta-completion/generate-template-draft.py](demos/03-documeta-completion/generate-template-draft.py)  
  샘플 공문을 LLM에 넣어 템플릿 초안을 생성하는 시연 스크립트
- `demos/03-documeta-completion/out/`  
  실행 후 생성되는 템플릿 초안과 RAG reference chunk

### 시연 4: RAG와 글쓰기 빌드

- [demos/04-build-writing/notes.md](demos/04-build-writing/notes.md)  
  시연 3에서 생성한 RAG reference chunk 기반 슬롯 완성과 출력 패키징 입력/출력
- [demos/04-build-writing/rag-slot-flow.py](demos/04-build-writing/rag-slot-flow.py)  
  FAISS + Blackbox LLM + 검증으로 `final-documeta.yaml`을 만드는 시연 스크립트
- [demos/04-build-writing/output-package.py](demos/04-build-writing/output-package.py)  
  완성형 DocuMeta를 Quarto / Typst / HWPX로 내보내는 시연 스크립트

## 실행 후 생성되는 파일

시연 결과는 각 시연 폴더의 `out/` 아래에 생긴다.

## 데모 실행 준비

시연 3-4는 Python 패키지 외에 `uv`, `quarto`, `typst` CLI가 필요하다.

Linux(Ubuntu/Debian 계열):

```bash
./scripts/setup-demo-linux.sh
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-demo-windows.ps1
```

설치 스크립트가 하는 일:

1. `uv` 설치 또는 확인
2. `quarto` 설치 또는 확인
3. `typst` 설치 또는 확인
4. `uv sync`로 Python 3.11-3.12 가상환경과 데모 의존성 준비
5. `demos/.env`가 없으면 `demos/.env.example`에서 생성
6. `uv`, `python`, `quarto`, `typst` 버전 출력

설치 후 `demos/.env`의 `API_KEY`를 실제 Blackbox 호환 API 키로 바꾼다.

수동으로 준비할 때는 아래 순서를 따른다.

```bash
uv sync
cp demos/.env.example demos/.env
uv run python --version
quarto --version
typst --version
```

HWPX 결과 확인은 `assets/vsix/deukhwp.vsix`를 설치한 DeukHwp 편집기에서 한다.
HWPX 파일 생성 보조 어댑터는 `demos/04-build-writing/support/hwpx_adapter.py`에 숨겨 두었다.

API 환경변수는 `demos/.env` 한 곳에서만 읽는다.

- `demos/04-build-writing/out/final-documeta.yaml`: 시연 4의 RAG 슬롯 완성 결과
- `demos/04-build-writing/out/final-package/*.qmd`: Quarto 원고
- `demos/04-build-writing/out/final-package/*.typ`: Typst 원고
- `demos/04-build-writing/out/final-package/*.html`: Quarto 렌더링 결과
- `demos/04-build-writing/out/final-package/*.pdf`: Typst 렌더링 결과
- `demos/04-build-writing/out/final-package/*.hwpx`: HWPX 결과

## 헷갈리기 쉬운 파일

- `slides/ai-writing-slides.qmd`  
  슬라이드 소스다. 강의 흐름을 바꿀 때가 아니면 먼저 볼 파일은 아니다.

- `ai-writing-slides.html`, `ai-writing-presentation.pdf`, `ai-writing-slides.tex`  
  렌더링 산출물이다. 원본 문서가 아니라 결과물이며 git에는 올리지 않는다.

- PPTX 산출물  
  현재 강의 운영본은 PDF 기준이다. PPTX는 생성하거나 관리하지 않는다.

## 권장 열람 순서

강의 준비할 때는 이 순서가 가장 덜 헷갈린다.

1. `docs/timetable.md`
2. `docs/instructor-script.md`
3. `demos/README.md`
4. `demos/01-chatgpt-direct/lecture-notes.md`
5. `demos/02-short-documeta/lecture-notes.md`
6. `demos/03-documeta-completion/notes.md`
7. `demos/04-build-writing/notes.md`
8. 필요할 때만 `docs/presentation.md`
