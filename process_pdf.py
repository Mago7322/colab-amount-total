# coding: utf-8
"""請求一覧表PDFから店舗別の合計金額を算出するスクリプト。
Google Colab上での実行を想定している。
"""

import re
import pandas as pd
import pdfplumber
from google.colab import files


def main():
    """PDFアップロードからExcel出力までの処理を行う"""
    # -- PDFファイルをアップロード --
    uploaded = files.upload()  # ユーザーにファイル選択を促す
    pdf_path = next(iter(uploaded.keys()))  # 最初にアップロードされたファイルを使用

    # -- PDFからテキストを抽出 --
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            lines.extend(text.splitlines())

    # -- ヘッダ行を検出 --
    for i, ln in enumerate(lines):
        if all(k in ln for k in ["No", "ブロック", "個別取引先", "入力日"]):
            header_idx = i
            break
    else:
        raise RuntimeError("テーブルヘッダが見つかりませんでした")

    # -- 明細データを解析 --
    records = []
    date_pat = r"\d{4}/\d{1,2}/\d{1,2}"
    for ln in lines[header_idx + 1:]:
        s = ln.strip()
        if not s or not re.match(r"^\d{6}", s):
            continue
        m0 = re.match(r"^(\d{6})\s+(\d{2})\s+(\d+)\s+(\d+)", s)
        if not m0:
            continue
        rec = {
            "No": m0.group(1),
            "ブロック": m0.group(2),
            "個別取引先": m0.group(3),
            "伝票番号": m0.group(4),
        }
        its = list(re.finditer(date_pat, s))
        if len(its) < 4:
            continue
        rec["発注日"] = its[0].group()
        rec["納品日"] = its[1].group()
        rec["仕入計上日"] = its[2].group()
        rec["入力日"] = its[-1].group()

        mid = s[its[2].end():its[-1].start()].strip()
        m_doc = re.search(r"\d{2}仕入", mid)
        if m_doc:
            rec["伝票種別"] = m_doc.group()
            mid = mid[:m_doc.start()].strip()
        else:
            rec["伝票種別"] = ""

        m_amt = re.match(r"(\d{1,3}(?:,\d{3})*)", mid)
        if m_amt:
            rec["請求額"] = m_amt.group(1)
            mid = mid[m_amt.end():].strip()
        else:
            rec["請求額"] = ""
        rec["納品先"] = mid
        records.append(rec)

    # -- DataFrame化 --
    df = pd.DataFrame(records)

    # -- 納品先情報の補完と分割 --
    def clean_store(val):
        if pd.isna(val):
            return ""
        s = str(val).replace("　", " ").strip()
        if re.match(r"^(\d{4})\s*([^\d].*)$", s):
            return s
        return ""

    df["納品先"] = df["納品先"].map(clean_store)
    df["納品先"] = df["納品先"].replace({"": pd.NA}).ffill()

    def split_store(val):
        if pd.isna(val):
            return "", ""
        s = str(val).replace("　", " ").strip()
        m = re.match(r"^(\d{4})\s*([^\d].*)$", s)
        if m:
            return m.group(1), m.group(2).strip()
        return "", val

    df["カーマコード"], df["店名"] = zip(*df["納品先"].map(split_store))

    # -- 金額の数値化 --
    df["請求額"] = (
        df["請求額"]
        .str.replace(",", "", regex=False)
        .str.replace("▲", "-", regex=False)
        .astype(float)
    )

    # -- カーマコード・店名ごとに合計金額を集計 --
    agg = (
        df.groupby(["カーマコード", "店名"], as_index=False)["請求額"]
        .sum()
        .rename(columns={"請求額": "合計金額"})
    )
    agg = agg[["カーマコード", "店名", "合計金額"]]

    # -- Excel出力 --
    output_path = "カーマ得意先管理表.xlsx"
    agg.to_excel(output_path, index=False)

    # -- ダウンロードリンク表示 --
    files.download(output_path)
    print("✅ カーマ得意先管理表.xlsx を出力しました")


if __name__ == "__main__":
    main()
