from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


OUTPUT_DIR = Path(__file__).resolve().parent


def make_cell(reference: str, value: str) -> str:
    return (
        f'<c r="{reference}" t="inlineStr">'
        f'<is><t xml:space="preserve">{escape(value)}</t></is></c>'
    )


def build_xlsx(tsv_path: Path) -> Path:
    rows = []
    for line_number, raw_line in enumerate(
        tsv_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        fields = raw_line.split("\t")
        if len(fields) != 2 or not all(fields):
            raise ValueError(f"Invalid TSV row {line_number} in {tsv_path.name}")
        rows.append((fields[0], fields[1]))

    worksheet_rows = [
        f'<row r="1">{make_cell("A1", "Hán")}{make_cell("B1", "Việt")}</row>'
    ]
    for row_number, (han, viet) in enumerate(rows, start=2):
        worksheet_rows.append(
            f'<row r="{row_number}">'
            f'{make_cell(f"A{row_number}", han)}'
            f'{make_cell(f"B{row_number}", viet)}'
            "</row>"
        )

    last_row = len(rows) + 1
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:B{last_row}"/>'
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '</sheetView></sheetViews>'
        '<cols><col min="1" max="1" width="32" customWidth="1"/>'
        '<col min="2" max="2" width="76" customWidth="1"/></cols>'
        f'<sheetData>{"".join(worksheet_rows)}</sheetData>'
        '<autoFilter ref="A1:B1"/>'
        '</worksheet>'
    )

    files = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        ),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="DONG_HANG" sheetId="1" r:id="rId1"/></sheets>'
            '</workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>'
        ),
        "xl/worksheets/sheet1.xml": worksheet,
    }

    xlsx_path = tsv_path.with_suffix(".xlsx")
    with ZipFile(xlsx_path, "w", ZIP_DEFLATED) as archive:
        for name, contents in files.items():
            archive.writestr(name, contents.encode("utf-8"))
    return xlsx_path


if __name__ == "__main__":
    for source in sorted(OUTPUT_DIR.glob("*_parallel.tsv")):
        print(build_xlsx(source).name)
