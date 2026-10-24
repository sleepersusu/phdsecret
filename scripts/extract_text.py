"""把論文 PDF 與提案轉成純文字，放在 reviews/<slug>/text/，agent 一律從這裡抄引文。

用法：uv run scripts/extract_text.py reviews/<slug> [--proposal proposal/<檔名>]
論文寫成 text/<檔名去副檔名>.txt，每頁以「=== p.N ===」開頭（N 是 PDF 的第幾頁，不是期刊印的頁碼）。
提案寫成 text/proposal.txt，不分頁；支援 .md、.txt、.pdf、.docx。
"""
import argparse
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf.errors import PdfReadError

from pdfpages import open_pdf, page_texts

PLAIN_TEXT_SUFFIXES = {".md", ".txt"}


def main(argv=None):
    args = _parse_args(argv)
    review_dir = Path(args.review_dir)
    pdf_dir = review_dir / "pdfs"
    text_dir = review_dir / "text"
    if not pdf_dir.is_dir():
        print(f"找不到 {pdf_dir}", file=sys.stderr)
        return 1
    text_dir.mkdir(exist_ok=True)

    written = 0
    for path in sorted(p for p in pdf_dir.iterdir() if p.suffix.lower() == ".pdf"):
        pages = _read_pages(path)
        if pages is None:
            continue
        marked = "".join(f"=== p.{number} ===\n{text}\n" for number, text in enumerate(pages, start=1))
        (text_dir / f"{path.stem}.txt").write_text(marked, encoding="utf-8")
        written += 1

    if args.proposal:
        proposal = _proposal_text(Path(args.proposal))
        if proposal is None:
            return 1
        (text_dir / "proposal.txt").write_text(proposal, encoding="utf-8")

    print(f"寫出 {written} 篇論文的文字到 {text_dir}" + ("，含提案" if args.proposal else ""))
    return 0


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="論文與提案轉純文字")
    parser.add_argument("review_dir", help="review 資料夾，例：reviews/advisor-12")
    parser.add_argument("--proposal", help="提案檔路徑")
    return parser.parse_args(argv)


def _read_pages(path):
    try:
        reader, _ = open_pdf(path)
    except PdfReadError as error:
        print(f"略過 {path.name}：讀不出來（{error}）", file=sys.stderr)
        return None
    if reader is None:
        print(f"略過 {path.name}：有開啟密碼", file=sys.stderr)
        return None
    return page_texts(reader)


def _proposal_text(path):
    suffix = path.suffix.lower()
    if suffix in PLAIN_TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        pages = _read_pages(path)
        return None if pages is None else "\n".join(pages) + "\n"
    if suffix == ".docx":
        return _docx_text(path)

    print(f"不支援的提案格式 {suffix}：請另存成 .docx、.pdf 或 .md", file=sys.stderr)
    return None


def _docx_text(path):
    """依文件順序取段落與表格：提案常把納入條件、萃取欄位放在表格裡，漏掉表格會讓對照誤判成「提案沒提到」。"""
    document = Document(path)
    lines = []
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            paragraph = Paragraph(child, document)
            text = paragraph.text.strip()
            if text:
                lines.append(_heading_prefix(paragraph.style.name) + text)
        elif child.tag == qn("w:tbl"):
            lines += _table_lines(Table(child, document))
    return "\n".join(lines) + "\n"


def _table_lines(table):
    """每列一行，儲存格以「 | 」分隔；合併儲存格在 python-docx 會重複出現，相鄰重複的只留一個。"""
    lines = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            text = " ".join(cell.text.split())
            if not cells or text != cells[-1]:
                cells.append(text)
        if any(cells):
            lines.append(" | ".join(cells))
    return lines


def _heading_prefix(style_name):
    if style_name == "Title":
        return "# "
    if style_name.startswith("Heading ") and style_name.split()[-1].isdigit():
        return "#" * int(style_name.split()[-1]) + " "
    return ""


if __name__ == "__main__":
    sys.exit(main())
