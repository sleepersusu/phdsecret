"""打開 PDF 並逐頁取文字；只有設了開啟密碼的檔打不開，只限制權限的加密檔照常讀。"""
from pypdf import PdfReader


def open_pdf(path):
    """回傳 (reader, encrypted)；打不開時 reader 為 None。"""
    reader = PdfReader(path)
    if not reader.is_encrypted:
        return reader, False
    return (reader if reader.decrypt("") else None), True


def page_texts(reader):
    return [(page.extract_text() or "").strip() for page in reader.pages]
