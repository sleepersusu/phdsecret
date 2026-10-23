"""從所有 reviews/* 產出可重建的跨批次文獻庫：index.json、matrix.md、references.csv。

用法：uv run scripts/library_build.py [--reviews reviews] [--out library]
這三個檔都是衍生檔，刪了也能從 reviews/ 重建，所以每次整個重寫。
同一資料夾的 tags.json 是本人與 agent 共同維護的標籤字典、不是衍生檔，這支腳本絕不讀寫它。
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import merge_refs
from cardschema import STRUCTURED
from matrix import _cell, _escape
from paperid import canonical_id

FUZZY = 0.9


def load_reviews(reviews_dir):
    """讀每個含 papers.json 的 review：論文清單、更新時間、卡片、歸併標籤、參考文獻。"""
    reviews = []
    for review_dir in sorted(p for p in Path(reviews_dir).iterdir() if (p / "papers.json").exists()):
        cards = {}
        for path in sorted((review_dir / "cards").glob("*/card.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            cards[data["key"]] = data
        reviews.append({
            "name": review_dir.name,
            "papers": _load(review_dir / "papers.json", []),
            "updatedAt": _load(review_dir / "state.json", {}).get("updatedAt", ""),
            "cards": cards,
            "paperTags": _load(review_dir / "paper-tags.json", {}),
            "references": _read_csv(review_dir / "references.csv"),
        })
    return reviews


def build_index(reviews):
    """以正規識別碼合併各批的同一篇；primary 取有卡片且批次最近更新者，同時間依 review 名稱。"""
    by_name = {review["name"]: review for review in reviews}
    papers, unindexed = {}, []
    for review in reviews:
        for paper in review["papers"]:
            key = paper["key"]
            cid = canonical_id(paper.get("id"))
            if cid is None:
                unindexed.append({"review": review["name"], "key": key, "reason": "id 待確認"})
                continue
            entry = papers.setdefault(cid, {"title": paper.get("title") or "", "primary": None, "appearances": []})
            entry["appearances"].append({"review": review["name"], "key": key, "hasCard": key in review["cards"]})

    for entry in papers.values():
        entry["articleType"], entry["tags"] = None, []
        with_card = sorted((a for a in entry["appearances"] if a["hasCard"]), key=lambda a: a["review"])
        if not with_card:
            continue
        best = max(with_card, key=lambda a: by_name[a["review"]]["updatedAt"])
        entry["primary"] = {"review": best["review"], "key": best["key"]}
        review = by_name[best["review"]]
        tags = review["paperTags"].get(best["key"]) or {}
        article = review["cards"][best["key"]].get("structured", {}).get("articleType")
        entry["articleType"] = tags.get("articleType") or (article.get("value") if isinstance(article, dict) else None)
        entry["tags"] = tags.get("tags", [])
    return {"papers": papers, "unindexed": unindexed}


def render_matrix(index, reviews):
    """每篇一列，取 primary 的卡片；沒有卡片的篇不列。"""
    by_name = {review["name"]: review for review in reviews}
    headers = [title for _, _, title in STRUCTURED] + ["標籤", "批次"]
    lines = ["| 論文 | " + " | ".join(headers) + " |", "|---|" + "---|" * len(headers)]
    entries = sorted((e for e in index["papers"].values() if e["primary"]),
                     key=lambda e: (e["primary"]["review"], e["primary"]["key"]))
    for entry in entries:
        review, key = entry["primary"]["review"], entry["primary"]["key"]
        card = by_name[review]["cards"][key]
        cells = [_cell(card.get("structured", {}).get(field)) for field, _, _ in STRUCTURED]
        cells.append(_escape("; ".join(entry["tags"])))
        cells.append(_escape("; ".join(sorted({a["review"] for a in entry["appearances"]}))))
        lines.append(f"| [{key}](../reviews/{review}/cards/{key}/card.md) | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def build_references(index, reviews):
    """各批 references.csv 已去重、已核對；依 citedBy 展開成 <review>/<key> 的引用後，沿用 merge_refs 的分組合併。"""
    entries = []
    for review in reviews:
        for row in review["references"]:
            ref = {"doi": row.get("doi") or None, "title": row.get("title") or "", "year": row.get("year") or "",
                   "firstAuthor": row.get("firstAuthor") or "", "raw": row.get("raw") or ""}
            for cited in filter(None, (row.get("citedBy") or "").split(";")):
                entries.append((f"{review['name']}/{cited}", ref))
    groups = merge_refs._group(entries, FUZZY)
    corpus = [{"key": cid, "id": cid, "title": entry["title"]} for cid, entry in index["papers"].items()]
    return merge_refs._rows(groups, corpus, FUZZY)


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    reviews_dir = Path(args.reviews)
    if not reviews_dir.is_dir():
        print(f"找不到 {reviews_dir}", file=sys.stderr)
        return 1
    reviews = load_reviews(reviews_dir)
    if not reviews:
        print(f"{reviews_dir} 底下沒有任何含 papers.json 的 review", file=sys.stderr)
        return 1

    index = build_index(reviews)
    rows = build_references(index, reviews)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "matrix.md").write_text(render_matrix(index, reviews), encoding="utf-8")
    with open(out / "references.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=merge_refs.CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    multi = sum(1 for e in index["papers"].values() if len({a["review"] for a in e["appearances"]}) >= 2)
    print(f"文獻庫 {len(index['papers'])} 篇（跨 2 批以上 {multi} 篇）、未索引 {len(index['unindexed'])} 篇、"
          f"參考文獻去重後 {len(rows)} 筆")
    return 0


def _load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _read_csv(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="從所有 review 產出跨批次文獻庫")
    parser.add_argument("--reviews", default="reviews")
    parser.add_argument("--out", default="library")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
