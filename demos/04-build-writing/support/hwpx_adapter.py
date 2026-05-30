from pathlib import Path
from re import sub

import yaml
from pyhwpxlib import HwpxBuilder

DEMO_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = DEMO_DIR / "out"
DOCUMETA_PATH = OUTPUT_DIR / "final-documeta.yaml"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as source_file:
        return yaml.safe_load(source_file)


def slot_value(documeta: dict, slot_name: str) -> str:
    if slot_name == "":
        return ""
    slots = documeta.get("slots", {})
    if slot_name not in slots or slots[slot_name] in (None, ""):
        raise ValueError(f"missing required DocuMeta slot: {slot_name}")
    value = slots[slot_name]
    return str(value)


def evidence_summary(documeta: dict) -> str:
    evidence_items = documeta.get("evidence_refs", [])
    return ", ".join(str(item.get("id", item.get("title", "unknown"))) for item in evidence_items)


def render_template(documeta: dict, template: str) -> str:
    values = dict(documeta.get("slots", {}))
    values["evidence_summary"] = evidence_summary(documeta)

    def replace(match):
        key = match.group(1).strip()
        if key not in values or values[key] in (None, ""):
            raise ValueError(f"missing required template value: {key}")
        return str(values[key])

    return sub(r"\{\{\s*([^}]+?)\s*\}\}", replace, template)


def row_from_cells(documeta: dict, cells: list) -> list[str]:
    rendered_cells = []
    for cell in cells:
        cell_text = str(cell)
        if cell_text in documeta.get("slots", {}):
            rendered_cells.append(slot_value(documeta, cell_text))
        elif "{{" in cell_text:
            rendered_cells.append(render_template(documeta, cell_text))
        else:
            rendered_cells.append(cell_text)
    return rendered_cells


def table_from_contract(documeta: dict, contract_name: str) -> list[list[str]]:
    contract = documeta["table_contracts"][contract_name]
    rows = []
    if "columns" in contract:
        rows.append([str(column) for column in contract["columns"]])
    if "row_slot_matrix" in contract:
        rows.extend(row_from_cells(documeta, row) for row in contract["row_slot_matrix"])
    if "rows" in contract:
        rows.extend(row_from_cells(documeta, row) for row in contract["rows"])
    return rows


def table_rows(documeta: dict, block: dict) -> list[list[str]]:
    if "contract" in block:
        return table_from_contract(documeta, block["contract"])
    return [row_from_cells(documeta, row) for row in block["rows"]]


def as_tuple(value):
    if isinstance(value, list):
        return tuple(value)
    return value


def block_options(block: dict) -> dict:
    ignored_keys = {"type", "contract", "rows", "text", "template", "slot"}
    return {key: as_tuple(value) for key, value in block.items() if key not in ignored_keys}


def render_hwpx(documeta: dict) -> Path:
    template = documeta["hwpx_template"]
    builder = HwpxBuilder(table_preset=template.get("table_preset", "default"))

    for block in template["blocks"]:
        block_type = block["type"]
        options = block_options(block)
        if block_type == "table":
            builder.add_table(table_rows(documeta, block), **options)
        elif block_type == "heading":
            builder.add_heading(slot_value(documeta, block["slot"]), **options)
        elif block_type == "paragraph":
            text = block.get("text")
            if text is None:
                text = render_template(documeta, block["template"])
            builder.add_paragraph(text, **options)
        elif block_type == "line":
            builder.add_draw_line(**options)
        else:
            raise ValueError(f"unsupported HWPX template block: {block_type}")

    target = OUTPUT_DIR / template["output_file"]
    target.parent.mkdir(parents=True, exist_ok=True)
    builder.save(str(target))
    return target


def main() -> None:
    documeta = load_yaml(DOCUMETA_PATH)
    print(render_hwpx(documeta))


if __name__ == "__main__":
    main()
