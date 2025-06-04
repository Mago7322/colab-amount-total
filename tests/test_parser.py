import pandas as pd
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from src.parser import parse_pdf_totals


def create_sample_pdf(path: str) -> None:
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
    c = canvas.Canvas(path)
    c.setFont("HeiseiMin-W3", 12)
    lines = [
        "Dummy heading",
        "No ブロック 個別取引先 伝票番号 発注日 納品日 仕入計上日 入力日",
        "000001 01 5555 1234 2023/01/01 2023/01/02 2023/01/03 1,500 1234 ホームセンターA 10仕入 2023/01/04",
        "000002 02 6666 2222 2023/02/01 2023/02/02 2023/02/03 2,000 5678 ホームセンターB 20仕入 2023/02/04",
        "000003 01 5555 3333 2023/03/01 2023/03/02 2023/03/03 500 1234 ホームセンターA 10仕入 2023/03/04",
    ]
    text = c.beginText(40, 800)
    for ln in lines:
        text.textLine(ln)
    c.drawText(text)
    c.showPage()
    c.save()


def test_parse_pdf_totals(tmp_path: Path) -> None:
    pdf_file = tmp_path / "sample.pdf"
    create_sample_pdf(str(pdf_file))

    df = parse_pdf_totals(str(pdf_file)).sort_values("カーマコード").reset_index(drop=True)

    expected = pd.DataFrame(
        {
            "カーマコード": ["1234", "5678"],
            "店名": ["ホームセンターA", "ホームセンターB"],
            "合計金額": [2000.0, 2000.0],
        }
    )

    pd.testing.assert_frame_equal(df, expected)
