"""論文識別碼的統一寫法：同一篇論文的 DOI、arXiv、PMID 有很多種寫法，跨批次比對前先轉成同一種。

正規形式：DOI 小寫、去掉 doi.org／doi: 前綴與尾端句點；arXiv 寫成 arxiv:<id> 並去掉版本號
（v2、v3 是同一篇的修訂，arXiv 的 DOI 10.48550/arxiv.<id> 也視為同一篇）；PMID 寫成 pmid:<n>。
"""
import re

DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)
ARXIV_DOI = re.compile(r"^10\.48550/arxiv\.(.+)$", re.IGNORECASE)
ARXIV_ID = re.compile(r"^arxiv:\s*(.+)$", re.IGNORECASE)
ARXIV_VERSION = re.compile(r"v\d+$", re.IGNORECASE)
PMID = re.compile(r"^pmid:\s*(\d+)$", re.IGNORECASE)


def normalize_doi(value):
    """DOI 比對用：去前綴、去尾端句點、轉小寫；空值回 None。"""
    if not value:
        return None
    return DOI_PREFIX.sub("", value.strip()).rstrip(".").lower() or None


def canonical_id(raw):
    """回傳正規形式；空值、「id 待確認」或認不出來的回 None。"""
    if not raw or not raw.strip():
        return None
    value = raw.strip()
    match = PMID.match(value)
    if match:
        return f"pmid:{match.group(1)}"
    match = ARXIV_ID.match(value)
    if match:
        return _arxiv(match.group(1))
    doi = normalize_doi(value)
    if doi and doi.startswith("10."):
        match = ARXIV_DOI.match(doi)
        return _arxiv(match.group(1)) if match else doi
    return None


def doi_aliases(raw):
    """拿來對參考文獻 DOI 的集合：arXiv 轉成它的 DOI，PMID 沒有 DOI 回空集合。"""
    cid = canonical_id(raw)
    if cid is None or cid.startswith("pmid:"):
        return set()
    if cid.startswith("arxiv:"):
        return {f"10.48550/arxiv.{cid[len('arxiv:'):]}"}
    return {cid}


def _arxiv(identifier):
    return "arxiv:" + ARXIV_VERSION.sub("", identifier.strip().lower())
