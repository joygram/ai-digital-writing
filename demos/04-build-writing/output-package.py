import importlib.util
import copy
import shutil
import html
import os
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = Path(__file__).resolve().parent
INPUT_DIR = DEMO_DIR / "in"
OUTPUT_DIR = DEMO_DIR / "out"
out_dir = OUTPUT_DIR / "final-package"
out_dir.mkdir(parents=True, exist_ok=True)

# 시연 4는 RAG로 완성한 DocuMeta를 하나의 입력으로 사용한다.
final_documeta_path = OUTPUT_DIR / "final-documeta.yaml"
default_documeta_frame_path = INPUT_DIR / "documeta.yaml"
qmd_template_path = INPUT_DIR / "templates" / "official-notice.qmd.template"
typ_template_path = INPUT_DIR / "templates" / "official-notice.typ.template"
summary_path = out_dir / "output-summary.md"
default_hwpx_generator_path = DEMO_DIR / "support" / "hwpx_adapter.py"


def merge_missing(target: dict, defaults: dict) -> dict:
    # LLM이 출력 템플릿 일부를 빠뜨려도 원본 DocuMeta 프레임의 계약을 유지한다.
    for key, value in defaults.items():
        if key not in target or target[key] is None:
            target[key] = value
        elif isinstance(target[key], dict) and isinstance(value, dict):
            merge_missing(target[key], value)
    return target


def load_documeta() -> tuple[dict, Path]:
    # RAG 슬롯 완성을 먼저 돌렸는지 확인하고, 부족한 출력 계약은 기본 프레임에서 보강한다.
    if not final_documeta_path.exists():
        raise FileNotFoundError(
            f"{final_documeta_path}가 없습니다. 먼저 `uv run python demos/04-build-writing/rag-slot-flow.py`를 실행하세요."
        )
    documeta = yaml.safe_load(final_documeta_path.read_text(encoding="utf-8"))
    if default_documeta_frame_path.exists():
        defaults = yaml.safe_load(default_documeta_frame_path.read_text(encoding="utf-8"))
        documeta = merge_missing(documeta, defaults)
    documeta.setdefault("output_status", "출력 가능")
    return documeta, final_documeta_path


def assert_output_allowed(documeta: dict) -> None:
    # 검증을 통과한 DocuMeta만 파일 패키징 단계로 넘긴다.
    if documeta.get("output_status") != "출력 가능":
        raise RuntimeError(f"output_status={documeta.get('output_status')} 상태라 출력 패키징을 중단합니다.")


def reference_summary(documeta: dict) -> str:
    refs = documeta.get("retrieved_reference_ids", [])
    return ", ".join(str(item) for item in refs)


def audit_summary(documeta: dict) -> str:
    source_map = documeta.get("slot_source_map", {})
    return ", ".join(f"{slot}->{source.get('chunk_id')}" for slot, source in source_map.items())


def slot_value(documeta: dict, name: str) -> str:
    if name == "output_status":
        return str(documeta.get("output_status", ""))
    if name == "reference_summary":
        return reference_summary(documeta)
    if name == "audit_summary":
        return audit_summary(documeta)
    return str(documeta.get("slots", {}).get(name, name))


def render_template(text: str, documeta: dict) -> str:
    rendered = text
    for name in set(part.split("}}", 1)[0].strip() for part in rendered.split("{{")[1:]):
        rendered = rendered.replace(f"{{{{ {name} }}}}", slot_value(documeta, name))
        rendered = rendered.replace(f"{{{{{name}}}}}", slot_value(documeta, name))
    return rendered


def fill_template(text: str, values: dict[str, str]) -> str:
    rendered = text
    for name, value in values.items():
        rendered = rendered.replace(f"{{{{ {name} }}}}", value)
        rendered = rendered.replace(f"{{{{{name}}}}}", value)
    return rendered


def contract_rows(documeta: dict, contract_name: str) -> list[list[str]]:
    contract = documeta.get("table_contracts", {}).get(contract_name, {})
    if "row_slot_matrix" in contract:
        return [[slot_value(documeta, cell) if cell else "" for cell in row] for row in contract["row_slot_matrix"]]
    rows = []
    for row in contract.get("rows", []):
        rendered_row = []
        for index, cell in enumerate(row):
            rendered_row.append(str(cell) if index % 2 == 0 else slot_value(documeta, cell))
        rows.append(rendered_row)
    return rows


def block_table_html(documeta: dict, block: dict) -> str:
    if "contract" in block:
        contract = documeta.get("table_contracts", {}).get(block["contract"], {})
        columns = contract.get("columns")
        rows = contract_rows(documeta, block["contract"])
    else:
        columns = None
        rows = [[str(label), slot_value(documeta, slot)] for label, slot in block.get("rows", [])]

    table_class = "approval-table" if block.get("contract") == "approval_table" else "doc-table"
    parts = [f'<table class="{table_class}">']
    if columns:
        parts.append("<tr>" + "".join(f"<th>{html.escape(str(column))}</th>" for column in columns) + "</tr>")
    for row in rows:
        parts.append("<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>")
    parts.append("</table>")
    return "\n".join(parts)


def html_blocks(documeta: dict) -> str:
    parts = ['<div class="official-doc">']
    has_verify_block = False
    for block in documeta.get("hwpx_template", {}).get("blocks", []):
        block_type = block.get("type")
        if block_type == "table":
            parts.append(block_table_html(documeta, block))
        elif block_type == "heading":
            level = "h1" if block.get("level") == 1 else "h2"
            css_class = "org-name" if block.get("level") == 1 else "sender-title"
            parts.append(f'<{level} class="{css_class}">{html.escape(slot_value(documeta, block["slot"]))}</{level}>')
        elif block_type == "line":
            parts.append('<hr class="doc-line" />')
        elif block_type == "paragraph":
            text = block.get("template") or block.get("text", "")
            if "output_status" in text:
                has_verify_block = True
            parts.append(f"<p>{html.escape(render_template(text, documeta))}</p>")
    if not has_verify_block:
        parts.append(f'<div class="verify-line">출력 검증: {html.escape(str(documeta["output_status"]))} / FAISS 검색 문서: {html.escape(reference_summary(documeta))}</div>')
    parts.append("</div>")
    return "\n".join(parts)


def qmd_text(documeta: dict) -> str:
    # Quarto 어댑터: 외부 QMD 템플릿에 DocuMeta block/table 계약을 주입한다.
    slots = documeta["slots"]
    targets = "\n".join(f"  - {target}" for target in documeta.get("output_targets", []))
    return fill_template(
        qmd_template_path.read_text(encoding="utf-8"),
        {
            "title": slots["title"],
            "document_type": documeta.get("document_subtype", documeta.get("document_type", "")),
            "output_targets_yaml": targets,
            "date": slots["date"],
            "html_blocks": html_blocks(documeta),
        },
    )


def typ_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").replace("@", "\\@")


def typ_table(documeta: dict, block: dict) -> str:
    if "contract" in block:
        contract = documeta.get("table_contracts", {}).get(block["contract"], {})
        columns = contract.get("columns")
        rows = contract_rows(documeta, block["contract"])
    else:
        columns = None
        rows = [[str(label), slot_value(documeta, slot)] for label, slot in block.get("rows", [])]

    width_count = len(columns or rows[0])
    cells = []
    if columns:
        cells.extend(f"label-cell([{typ_escape(str(column))}])" for column in columns)
    for row in rows:
        cells.extend(f"body-cell([{typ_escape(cell)}])" for cell in row)
    return f"#table(columns: ({', '.join(['1fr'] * width_count)}), stroke: thin-line, inset: (x: 2mm, y: 1.5mm), {', '.join(cells)})"


def typ_blocks(documeta: dict) -> str:
    parts = []
    has_verify_block = False
    for block in documeta.get("hwpx_template", {}).get("blocks", []):
        block_type = block.get("type")
        if block_type == "table":
            parts.append(typ_table(documeta, block))
        elif block_type == "heading":
            size = "18pt" if block.get("level") == 1 else "15pt"
            parts.append(f'#align(center)[#text(size: {size}, weight: "bold")[{typ_escape(slot_value(documeta, block["slot"]))}]]')
        elif block_type == "line":
            parts.append("#line(length: 100%, stroke: thin-line)")
        elif block_type == "paragraph":
            text = render_template(block.get("template") or block.get("text", ""), documeta)
            if "output_status" in (block.get("template") or block.get("text", "")):
                has_verify_block = True
            parts.append(typ_escape(text))
        parts.append("#v(3mm)")
    if not has_verify_block:
        parts.append(f'#text(size: 8.3pt, fill: rgb("555555"))[출력 검증: {typ_escape(str(documeta["output_status"]))} / FAISS 검색 문서: {typ_escape(reference_summary(documeta))}]')
    return "\n".join(parts)


def typ_text(documeta: dict) -> str:
    # Typst 어댑터: 외부 TYP 템플릿에 DocuMeta block/table 계약을 주입한다.
    return fill_template(
        typ_template_path.read_text(encoding="utf-8"),
        {"typ_blocks": typ_blocks(documeta)},
    )


def render_hwpx(documeta: dict) -> Path:
    # HWPX 어댑터: 로컬 생성기에 DocuMeta를 넘겨 제출 후보 파일을 만든다.
    hwpx_documeta = copy.deepcopy(documeta)
    hwpx_documeta["hwpx_template"]["blocks"] = [
        block
        for block in hwpx_documeta.get("hwpx_template", {}).get("blocks", [])
        if "output_status" not in (block.get("template") or block.get("text", ""))
    ]
    generator_path = Path(os.getenv("HWPX_GENERATOR_PATH", str(default_hwpx_generator_path)))
    if not generator_path.exists():
        return render_fallback_hwpx(hwpx_documeta, generator_path)
    spec = importlib.util.spec_from_file_location(
        "generate_hwpx",
        generator_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render_hwpx(hwpx_documeta)


def render_fallback_hwpx(documeta: dict, missing_generator_path: Path) -> Path:
    # 강의용 fallback: 외부 HWPX 생성기가 없는 환경에서도 슬롯 검증 흐름을 끝까지 보여준다.
    fallback_path = out_dir / "system-notice-documeta-fallback.hwpx"
    slots = documeta.get("slots", {})
    section_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<section>
  <notice>
    <title>{html.escape(str(slots.get("title", "")))}</title>
    <schedule>{html.escape(str(slots.get("schedule", "")))}</schedule>
    <scope>{html.escape(str(slots.get("scope", "")))}</scope>
    <required_actions>{html.escape(str(slots.get("required_actions", "")))}</required_actions>
    <contact>{html.escape(str(slots.get("contact", "")))}</contact>
    <fallback_generator>missing: {html.escape(str(missing_generator_path))}</fallback_generator>
  </notice>
</section>
"""
    with ZipFile(fallback_path, "w", ZIP_DEFLATED) as hwpx:
        hwpx.writestr("mimetype", "application/hwp+zip")
        hwpx.writestr("Contents/section0.xml", section_xml)
    return fallback_path


def render_html(qmd_path: Path) -> Path:
    # Quarto CLI 렌더링.
    if shutil.which("quarto") is None:
        raise FileNotFoundError("quarto CLI가 PATH에 없습니다. Quarto 설치 후 다시 실행하세요.")
    subprocess.run(
        ["quarto", "render", str(qmd_path), "--to", "html"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return qmd_path.with_suffix(".html")


def render_pdf(typ_path: Path) -> Path:
    # Typst CLI 렌더링.
    if shutil.which("typst") is None:
        raise FileNotFoundError("typst CLI가 PATH에 없습니다. Typst 설치 후 다시 실행하세요.")
    pdf_path = typ_path.with_suffix(".pdf")
    subprocess.run(
        ["typst", "compile", str(typ_path), str(pdf_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return pdf_path


def write_output_summary(documeta: dict, source_path: Path, html_path: Path, pdf_path: Path, target_hwpx: Path) -> Path:
    # 강의 화면에서 입력, 출력, 핵심 슬롯을 한 번에 확인하는 요약 파일.
    summary = f"""# 시연 4 출력 요약

## 입력

- DocuMeta: {source_path}
- QMD template: {qmd_template_path}
- TYP template: {typ_template_path}
- output_status: {documeta.get('output_status', '')}

## 출력 파일

- Quarto HTML: {html_path}
- Typst PDF: {pdf_path}
- HWPX: {target_hwpx}

## 표 계약

- approval_table: {len(documeta['table_contracts']['approval_table'].get('row_slot_matrix', []))} rows
- notice_table: {len(documeta['table_contracts']['notice_table'].get('rows', []))} rows
- footer_metadata_table: {len(documeta['table_contracts']['footer_metadata_table'].get('rows', []))} rows

## 핵심 슬롯

- title: {documeta['slots']['title']}
- schedule: {documeta['slots']['schedule']}
- scope: {documeta['slots']['scope']}
- required_actions: {documeta['slots']['required_actions']}
- contact: {documeta['slots']['contact']}

## 감사 매핑

{yaml.safe_dump(documeta.get('slot_source_map', {}), allow_unicode=True, sort_keys=False)}
"""
    summary_path.write_text(summary, encoding="utf-8")
    return summary_path


def main() -> int:
    try:
        # 1. 완성형 DocuMeta 로드와 출력 가능 상태 확인.
        documeta, source_path = load_documeta()
        assert_output_allowed(documeta)

        qmd_path = out_dir / "system-notice-documeta-generated.qmd"
        typ_path = out_dir / "system-notice-documeta-generated.typ"
        documeta_out = out_dir / "system-notice-documeta.yaml"

        # 2. 같은 DocuMeta에서 Quarto, Typst, HWPX 출력 입력을 나눈다.
        documeta_out.write_text(yaml.safe_dump(documeta, allow_unicode=True, sort_keys=False), encoding="utf-8")
        qmd_path.write_text(qmd_text(documeta), encoding="utf-8")
        typ_path.write_text(typ_text(documeta), encoding="utf-8")
        html_path = render_html(qmd_path)
        pdf_path = render_pdf(typ_path)
        hwpx_path = render_hwpx(documeta)
        target_hwpx = out_dir / "system-notice-documeta-generated.hwpx"
        target_hwpx.write_bytes(hwpx_path.read_bytes())
        output_summary = write_output_summary(documeta, source_path, html_path, pdf_path, target_hwpx)

        # 3. HWPX 내부 XML에 핵심 슬롯 값이 실제로 들어갔는지 확인한다.
        with ZipFile(target_hwpx) as hwpx:
            section_xml = hwpx.read("Contents/section0.xml").decode("utf-8", errors="replace")

        print("[DocuMeta 기반 최종 출력 패키지]")
        print("- 입력 DocuMeta:", source_path)
        print("- Quarto:", qmd_path)
        print("- Typst:", typ_path)
        print("- HTML:", html_path)
        print("- PDF:", pdf_path)
        print("- HWPX:", target_hwpx)
        print("- Summary:", output_summary)
        print("\n[DocuMeta 표 계약]")
        for contract_name, contract in documeta["table_contracts"].items():
            rows = contract.get("rows") or contract.get("row_slot_matrix") or []
            print(f"- {contract_name}: {len(rows)} rows")
        print("\n[HWPX 필수값 검증]")
        for key in ["title", "schedule", "scope", "required_actions", "contact"]:
            value = documeta["slots"][key]
            print(f"- {'PASS' if value in section_xml else 'FAIL'}: {key} = {value}")
        return 0
    except Exception as exc:
        print(f"[시연 4 중단] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
