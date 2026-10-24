"""從 Zotero 7 本機 API 讀一個資料夾，把 PDF 複製進 reviews/<slug>/pdfs/，寫 search/zotero-pull.json。

用法：uv run scripts/zotero_pull.py reviews/<slug> --collection <名稱> [--base http://localhost:23119/api]
本機 API 唯讀、不需金鑰；Zotero 要開著，且「設定 → 進階」勾選允許其他應用程式通訊。
資料夾的條目是平的清單：論文與它的 PDF 附件並列，附件以 parentItem 指回論文；
附件的 links.enclosure.href 是 file:// 網址，直接指向 ~/Zotero/storage 的檔案（2026-10-24 以本人的 Zotero 7 驗證）。
只複製不搬移，也不覆蓋 pdfs/ 已有的檔案（以獨占模式 "xb" 建立，撞名就記入 skipped）；
同一篇有多個 PDF 附件時取 API 順序中第一個存在的檔案；沒有 PDF 的論文、沒有書目資料的單獨 PDF 列出來讓本人處理。
"""
import argparse
import http.client
import json
import re
import shutil
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

from paperid import canonical_id

DEFAULT_BASE = "http://localhost:23119/api"
CONNECT_HINT = "連不上 Zotero 本機 API：請確認 Zotero 已開啟，且「設定 → 進階」已勾選「允許此電腦上的其他應用程式與 Zotero 通訊」"
EXTRA_ID = re.compile(r"^(?:arXiv|PMID):\s*\S+", re.IGNORECASE | re.MULTILINE)
YEAR = re.compile(r"\d{4}")
PAGE = 100


class ZoteroUnavailable(Exception):
    pass


def fetch_json(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ConnectionError, TimeoutError, http.client.HTTPException, ValueError) as error:
        raise ZoteroUnavailable(str(error)) from error


def collection_items(base, name, fetch=fetch_json):
    """回傳 (資料夾 key, 條目清單)；找不到資料夾時回 (None, 現有資料夾名稱)。"""
    collections = fetch(f"{base}/users/0/collections?limit={PAGE}")
    match = next((c for c in collections if c["data"]["name"] == name), None)
    if match is None:
        return None, [c["data"]["name"] for c in collections]
    items, start = [], 0
    while True:
        page = fetch(f"{base}/users/0/collections/{match['key']}/items?limit={PAGE}&start={start}")
        items += page
        if len(page) < PAGE:
            return match["key"], items
        start += PAGE


def base_key(data):
    """第一作者姓氏（轉 ASCII、去非英數、小寫）＋年份；姓氏轉不出 ASCII 時用標題第一個英數詞；無年份用 nd。"""
    creators = data.get("creators") or []
    first = next((c for c in creators if c.get("creatorType", "author") == "author"), creators[0] if creators else {})
    word = _ascii(first.get("lastName") or first.get("name") or "")
    if not word:
        match = re.search(r"[a-z0-9]+", _ascii_spaced(data.get("title") or ""))
        word = match.group(0) if match else "paper"
    year = YEAR.search(data.get("date") or "")
    return word + (year.group(0) if year else "nd")


def pull(items, pdf_dir):
    pdf_dir = Path(pdf_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    attachments, loose, papers = {}, [], []
    for item in items:
        data = item["data"]
        if data.get("itemType") == "attachment":
            if data.get("contentType") != "application/pdf":
                continue
            if data.get("parentItem"):
                attachments.setdefault(data["parentItem"], []).append(_file_path(item))
            else:
                loose.append({"title": data.get("title") or data.get("filename") or "", "zoteroKey": item["key"]})
        elif data.get("itemType") != "note":
            papers.append(item)

    result = {"pulled": [], "noPdf": [], "skipped": [], "noMetadata": loose}
    used = {}
    for item in sorted(papers, key=lambda i: (base_key(i["data"]), (i["data"].get("title") or "").casefold())):
        data = item["data"]
        title, pid = data.get("title") or "", _paper_id(data)
        source = next((p for p in attachments.get(item["key"], []) if p is not None and p.exists()), None)
        if source is None:
            result["noPdf"].append({"title": title, "id": pid, "zoteroKey": item["key"]})
            continue
        base = base_key(data)
        count = used.get(base, 0)
        used[base] = count + 1
        key = base + _suffix(count)
        target = pdf_dir / f"{key}.pdf"
        try:
            with open(source, "rb") as src, open(target, "xb") as dst:
                shutil.copyfileobj(src, dst)
        except FileExistsError:
            result["skipped"].append({"key": key, "title": title})
            continue
        result["pulled"].append({"key": key, "id": pid, "title": title, "zoteroKey": item["key"]})
    return result


def main(argv=None, fetch=fetch_json):
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    review = Path(args.review_dir)
    try:
        key, items = collection_items(args.base, args.collection, fetch)
    except ZoteroUnavailable:
        print(CONNECT_HINT, file=sys.stderr)
        return 1
    if key is None:
        print(f"找不到 Zotero 資料夾「{args.collection}」；現有：{'、'.join(items) or '（無）'}", file=sys.stderr)
        return 1

    result = pull(items, review / "pdfs")
    (review / "search").mkdir(parents=True, exist_ok=True)
    (review / "search" / "zotero-pull.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                                       encoding="utf-8")
    print(f"複製 {len(result['pulled'])} 篇；缺 PDF {len(result['noPdf'])} 篇；已存在未覆蓋 {len(result['skipped'])} 篇；"
          f"沒有書目資料的 PDF {len(result['noMetadata'])} 個")
    for entry in result["noMetadata"]:
        print(f"- 沒有書目資料：{entry['title']}（在 Zotero 對它按右鍵 →「擷取 PDF 的中繼資料」後重跑）")
    return 0


def _file_path(item):
    href = (item.get("links", {}).get("enclosure") or {}).get("href", "")
    return Path(unquote(urlparse(href).path)) if href.startswith("file://") else None


def _paper_id(data):
    cid = canonical_id(data.get("DOI"))
    if cid:
        return cid
    match = EXTRA_ID.search(data.get("extra") or "")
    return canonical_id(match.group(0)) if match else None


def _suffix(count):
    """第 0 篇沒有後綴，之後依序 a…z、aa、ab…（26 進位，同名論文超過 26 篇也不會出錯）。"""
    letters = ""
    while count > 0:
        count, rest = divmod(count - 1, 26)
        letters = "abcdefghijklmnopqrstuvwxyz"[rest] + letters
    return letters


def _ascii(text):
    return re.sub(r"[^a-z0-9]", "", _ascii_spaced(text))


def _ascii_spaced(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="從 Zotero 本機 API 把一個資料夾的 PDF 複製進流水線")
    parser.add_argument("review_dir")
    parser.add_argument("--collection", required=True)
    parser.add_argument("--base", default=DEFAULT_BASE)
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
