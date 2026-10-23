"""盤點一個 review 的 PDF：頁數、讀不讀得出文字、是否加密、候選 DOI／arXiv ID。

用法：uv run scripts/inventory.py reviews/<slug> [--min-chars 100] [--id-pages 2]
產出 reviews/<slug>/inventory.json，並印出 markdown 表格。
DOI／arXiv ID 只是候選：前幾頁也可能出現別篇的 DOI，要對過標題才算確認。
"""
import argparse
import json
import re
import sys
from pathlib import Path

from pypdf.errors import PdfReadError

from pdfpages import open_pdf, page_texts

DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s\"<>]+", re.IGNORECASE)
ARXIV_PATTERN = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,;:)]}"


def find_doi(text):
    match = DOI_PATTERN.search(text)
    if match is None:
        return None
    return match.group(0).rstrip(TRAILING_PUNCTUATION)


def find_arxiv(text):
    match = ARXIV_PATTERN.search(text)
    return match.group(1) if match else None


def inspect_pdf(path, min_chars=100, id_pages=2):
    """讀一個 PDF 回傳盤點結果；只有使用者密碼的加密檔打不開，其餘照常讀。"""
    path = Path(path)
    result = {
        "file": path.name,
        "pages": None,
        "avgChars": None,
        "readable": False,
        "encrypted": False,
        "title": None,
        "doi": None,
        "arxiv": None,
    }
    reader, encrypted = open_pdf(path)
    result["encrypted"] = encrypted
    if reader is None:
        return result

    texts = page_texts(reader)
    head = "\n".join(texts[:id_pages])
    avg_chars = round(sum(len(text) for text in texts) / len(texts)) if texts else 0

    result["pages"] = len(texts)
    result["avgChars"] = avg_chars
    result["readable"] = avg_chars >= min_chars
    result["title"] = _metadata_title(reader)
    result["doi"] = find_doi(head)
    result["arxiv"] = find_arxiv(head)
    return result


def main(argv=None):
    args = _parse_args(argv)
    review_dir = Path(args.review_dir)
    pdf_dir = review_dir / "pdfs"
    if not pdf_dir.is_dir():
        print(f"找不到 {pdf_dir}：先建立 pdfs/ 並放入 PDF", file=sys.stderr)
        return 1

    paths = sorted(path for path in pdf_dir.iterdir() if path.suffix.lower() == ".pdf")
    rows = [_inspect_or_record_error(path, args.min_chars, args.id_pages) for path in paths]

    output = review_dir / "inventory.json"
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(_to_markdown(rows))
    return 0


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="盤點 reviews/<slug>/pdfs 裡的 PDF")
    parser.add_argument("review_dir", help="review 資料夾，例：reviews/advisor-12")
    parser.add_argument("--min-chars", type=int, default=100, help="每頁平均字元數低於此值視為讀不出文字（掃描檔）")
    parser.add_argument("--id-pages", type=int, default=2, help="只在前幾頁找 DOI／arXiv ID，避開參考文獻")
    return parser.parse_args(argv)


def _inspect_or_record_error(path, min_chars, id_pages):
    try:
        return inspect_pdf(path, min_chars, id_pages)
    except PdfReadError as error:
        return {"file": path.name, "pages": None, "readable": False, "error": str(error)}


def _metadata_title(reader):
    title = str((reader.metadata or {}).get("/Title") or "").strip()
    return title or None


def _status(row):
    if row.get("error"):
        return "壞檔"
    if row.get("encrypted") and row["pages"] is None:
        return "加密"
    if not row["readable"]:
        return "讀不出文字"
    return "可讀"


def _to_markdown(rows):
    lines = [
        "| file | pages | 狀態 | doi | arxiv | title |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        cells = [
            row["file"],
            row["pages"] if row["pages"] is not None else "",
            _status(row),
            row.get("doi") or "",
            row.get("arxiv") or "",
            row.get("title") or "",
        ]
        lines.append("| " + " | ".join(str(cell) for cell in cells) + " |")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
