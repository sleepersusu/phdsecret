"""核對 markdown 檔裡每一則引文，是否真的出現在原文的那一頁。

用法：uv run scripts/quote_check.py reviews/<slug> <檔案.md> [...] [--require-evidence]
引文格式："原文照抄" [key, p.N]（論文）或 "原文照抄" [proposal]（提案）。
原文取自 reviews/<slug>/text/<key>.txt；先嚴格比對，比不到再寬鬆比對（忽略大小寫、空白、連字號）。
--require-evidence：草稿用，有 [@key] 引用的行必須同一行附至少一則引文。
有任何一則對不上，結束碼為 1。
"""
import argparse
import re
import sys
from pathlib import Path

from textnorm import loosen, normalize

CITATION = re.compile(
    r"[\"“](?P<quote>[^\"“”\n]+)[\"”]\s*"
    r"\[(?P<key>[^\],\[@][^\],\[]*?)(?:,\s*p\.\s*(?P<page>\d+))?\]"
)
CITEKEY = re.compile(r"\[@[^\]]+\]")
PAGE_MARKER = re.compile(r"^=== p\.(\d+) ===$", re.MULTILINE)
PROPOSAL_KEY = "proposal"


def find_citations(markdown):
    """回傳 [(行號, 引文, key, 頁碼或 None)]。"""
    found = []
    for line_number, line in enumerate(markdown.splitlines(), start=1):
        for match in CITATION.finditer(line):
            page = int(match.group("page")) if match.group("page") else None
            found.append((line_number, match.group("quote"), match.group("key").strip(), page))
    return found


def check(review_dir, key, page, quote):
    """回傳 {ok, mode, foundOn, reason}；mode 是 strict 或 loose，foundOn 是引文實際所在的頁。"""
    path = Path(review_dir) / "text" / f"{key}.txt"
    if not path.exists():
        return _fail(f"找不到 {key} 的文字檔 text/{key}.txt")

    raw = path.read_text(encoding="utf-8")
    if key == PROPOSAL_KEY:
        mode = _match_mode(quote, raw)
        return {"ok": True, "mode": mode, "foundOn": []} if mode else _fail("提案裡找不到")
    if page is None:
        return _fail("論文引文缺頁碼")

    pages = _split_pages(raw)
    if page not in pages:
        return _fail(f"{key} 沒有第 {page} 頁（共 {len(pages)} 頁）")

    mode = _match_mode(quote, pages[page])
    if mode:
        return {"ok": True, "mode": mode, "foundOn": [page]}
    found_on = [number for number, text in pages.items() if _match_mode(quote, text)]
    reason = f"第 {page} 頁找不到" + (f"，出現在第 {', '.join(map(str, found_on))} 頁" if found_on else "，全文都找不到")
    return _fail(reason, found_on)


def main(argv=None):
    parser = argparse.ArgumentParser(description="核對引文是否出現在原文那一頁")
    parser.add_argument("review_dir")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--require-evidence", action="store_true", help="有 [@key] 的行必須附引文")
    args = parser.parse_args(argv)
    review_dir = args.review_dir

    checked = failed = loose = 0
    for file in args.files:
        markdown = Path(file).read_text(encoding="utf-8")
        if args.require_evidence:
            for line_number in _lines_without_evidence(markdown):
                failed += 1
                print(f"{file}:{line_number} 有 [@key] 引用但沒有證據引文")
        for line_number, quote, key, page in find_citations(markdown):
            result = check(review_dir, key, page, quote)
            checked += 1
            if not result["ok"]:
                failed += 1
                location = f"{key}, p.{page}" if page else key
                print(f"{file}:{line_number} [{location}] {result['reason']}：\"{quote[:80]}\"")
            elif result["mode"] == "loose":
                loose += 1

    print(f"checked {checked}, failed {failed}（其中 {loose} 則靠寬鬆比對通過）")
    if checked == 0:
        print("沒有找到任何引文：檢查格式是否為 \"原文\" [key, p.N]")
        return 1
    return 1 if failed else 0


def _lines_without_evidence(markdown):
    return [
        number for number, line in enumerate(markdown.splitlines(), start=1)
        if CITEKEY.search(line) and not CITATION.search(line)
    ]


def _fail(reason, found_on=None):
    return {"ok": False, "mode": None, "foundOn": found_on or [], "reason": reason}


def _match_mode(quote, text):
    if normalize(quote) in normalize(text):
        return "strict"
    if loosen(quote) in loosen(text):
        return "loose"
    return None


def _split_pages(raw):
    parts = PAGE_MARKER.split(raw)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


if __name__ == "__main__":
    sys.exit(main())
