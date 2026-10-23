"""合併這批論文的參考文獻：同一篇只留一筆，標出被幾篇、被哪幾篇引用。

用法：uv run scripts/merge_refs.py reviews/<slug> [--fuzzy 0.9]
讀 refs/<key>.json（subagent 抽出的參考文獻）、refs/<key>.count.json（另一個 subagent 數的條數）、papers.json（本批論文）。
寫出 references.csv（依被引用次數排序）與 refs-report.json（raw 對不上原文的、條數不符的）。
比對順序：DOI → 標題＋年份 → 標題相似度（同年、達門檻才合併，並標 uncertain 讓人複查）。
raw 在原文那一頁找不到的參考文獻視為抽錯，不併入。
"""
import argparse
import csv
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import paperid
import quote_check

NON_WORD = re.compile(r"[\W_]+")
CSV_FIELDS = ["refId", "title", "firstAuthor", "year", "doi", "citedByCount", "citedBy", "inCorpus", "uncertain", "raw"]


def main(argv=None):
    args = _parse_args(argv)
    review = Path(args.review_dir)
    ref_paths = sorted(p for p in (review / "refs").glob("*.json") if not p.name.endswith(".count.json"))
    if not ref_paths:
        print(f"{review}/refs 底下沒有參考文獻檔", file=sys.stderr)
        return 1
    papers_path = review / "papers.json"
    papers = json.loads(papers_path.read_text(encoding="utf-8")) if papers_path.exists() else []

    entries, unverified, mismatches = _load_entries(review, ref_paths)
    groups = _group(entries, args.fuzzy)
    rows = _rows(groups, papers, args.fuzzy)

    with open(review / "references.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "papers": len(ref_paths),
        "rawCount": len(entries) + len(unverified),
        "unique": len(rows),
        "coreCount": sum(1 for row in rows if row["citedByCount"] >= 2),
        "uncertainCount": sum(1 for row in rows if row["uncertain"]),
        "unverified": unverified,
        "countMismatch": mismatches,
    }
    (review / "refs-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _print_summary(report, rows)
    return 0


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="合併並去重參考文獻")
    parser.add_argument("review_dir", help="review 資料夾，例：reviews/advisor-12")
    parser.add_argument("--fuzzy", type=float, default=0.9, help="標題相似度達此值（且同年）才視為同一篇")
    return parser.parse_args(argv)


def _load_entries(review, ref_paths):
    entries, unverified, mismatches = [], [], []
    for path in ref_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        key, refs = data["key"], data["references"]
        for ref in refs:
            if quote_check.check(review, key, ref.get("page"), ref.get("raw", ""))["ok"]:
                entries.append((key, ref))
            else:
                unverified.append({"key": key, "title": ref.get("title"), "page": ref.get("page"), "raw": ref.get("raw")})

        count_path = path.with_name(f"{key}.count.json")
        if count_path.exists():
            counted = json.loads(count_path.read_text(encoding="utf-8"))["count"]
            if counted != len(refs):
                mismatches.append({"key": key, "extracted": len(refs), "counted": counted})
    return entries, unverified, mismatches


def _group(entries, fuzzy):
    groups, by_doi, by_title = [], {}, {}
    for key, ref in entries:
        doi = paperid.normalize_doi(ref.get("doi"))
        title_key = _title_key(ref.get("title"))
        year = str(ref.get("year") or "")

        group = by_doi.get(doi) if doi else None
        if group is None and title_key:
            group = by_title.get((title_key, year))
        uncertain = False
        if group is None and title_key:
            group = _fuzzy_match(groups, key, title_key, year, fuzzy)
            uncertain = group is not None
        if group is None:
            group = {"refs": [], "doi": None, "titleKey": title_key, "year": year, "uncertain": False}
            groups.append(group)

        if doi and group["doi"] and doi != group["doi"]:
            uncertain = True
        group["refs"].append((key, ref))
        group["uncertain"] = group["uncertain"] or uncertain
        if doi:
            group["doi"] = group["doi"] or doi
            by_doi.setdefault(doi, group)
        if title_key:
            by_title.setdefault((title_key, year), group)
    return groups


def _fuzzy_match(groups, key, title_key, year, fuzzy):
    """同一篇論文列成兩筆的，就是作者認定的兩篇（例：同作者同年的 Scalable／Sparse GP-VAE），不靠相似度合併。"""
    for group in groups:
        if any(cited_by == key for cited_by, _ in group["refs"]):
            continue
        if group["year"] == year and group["titleKey"] and _similar(title_key, group["titleKey"], fuzzy):
            return group
    return None


def _similar(a, b, threshold):
    matcher = SequenceMatcher(None, a, b)
    return matcher.quick_ratio() >= threshold and matcher.ratio() >= threshold


def _rows(groups, papers, fuzzy):
    rows = []
    for group in groups:
        first_ref = group["refs"][0][1]
        cited_by = sorted({key for key, _ in group["refs"]})
        title = next((ref["title"] for _, ref in group["refs"] if ref.get("title")), "")
        rows.append({
            "title": title,
            "firstAuthor": first_ref.get("firstAuthor") or "",
            "year": group["year"],
            "doi": group["doi"] or "",
            "citedByCount": len(cited_by),
            "citedBy": ";".join(cited_by),
            "inCorpus": _corpus_key(group, papers, fuzzy),
            "uncertain": "y" if group["uncertain"] else "",
            "raw": first_ref.get("raw", ""),
        })
    rows.sort(key=lambda row: (-row["citedByCount"], row["title"].casefold()))
    for number, row in enumerate(rows, start=1):
        row["refId"] = f"r{number:03d}"
    return rows


def _corpus_key(group, papers, fuzzy):
    for paper in papers:
        if group["doi"] and group["doi"] in paperid.doi_aliases(paper.get("id")):
            return paper["key"]
        paper_title = _title_key(paper.get("title"))
        if paper_title and group["titleKey"] and _similar(paper_title, group["titleKey"], fuzzy):
            return paper["key"]
    return ""


def _title_key(title):
    return NON_WORD.sub("", title.casefold()) if title else ""


def _print_summary(report, rows):
    print(
        f"{report['papers']} 篇論文、原始 {report['rawCount']} 筆 → 去重後 {report['unique']} 筆；"
        f"被 2 篇以上引用 {report['coreCount']} 筆；模糊合併待複查 {report['uncertainCount']} 筆"
    )
    if report["unverified"]:
        print(f"⚠ raw 在原文找不到、未併入：{len(report['unverified'])} 筆")
    for mismatch in report["countMismatch"]:
        print(f"⚠ {mismatch['key']} 抽出 {mismatch['extracted']} 筆，另一個 agent 數到 {mismatch['counted']} 筆")
    for row in rows[:10]:
        print(f"- {row['citedByCount']} 篇｜{row['title']}（{row['year']}）")


if __name__ == "__main__":
    sys.exit(main())
