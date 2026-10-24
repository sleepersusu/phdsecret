"""合併三路搜尋結果：同一篇只留一筆，排除已讀與沒有識別碼的，產出篩選用的候選池 pool.json。

用法：uv run scripts/search_merge.py reviews/<slug> [--library library]
讀 search/hits/*.json。已在 library/index.json 的篇移到 alreadyRead（讀過了不用再篩）；
canonical_id 認不出來的移到 noId（CLAUDE.md：查不到 DOI、PMID、arXiv ID 不建卡）。
同一篇被多路找到時合併 routes 與 via，其餘欄位取第一個非空值。
counts.unique 是有識別碼的不重複篇數（候選池加已讀）。
"""
import argparse
import json
import sys
from pathlib import Path

from paperid import canonical_id

FIELDS = ("title", "year", "authors", "abstract", "venue")


def merge(hits, index):
    known = index.get("papers", {})
    pool, already, no_id, seen_read = {}, [], [], set()
    for hit in hits:
        cid = canonical_id(hit.get("id"))
        if cid is None:
            no_id.append(hit)
            continue
        if cid in known:
            if cid not in seen_read:
                seen_read.add(cid)
                already.append({**hit, "id": cid})
            continue
        entry = pool.get(cid)
        if entry is None:
            pool[cid] = {"id": cid, **{f: hit.get(f) for f in FIELDS},
                         "routes": [hit.get("route")], "via": [v for v in [hit.get("via")] if v]}
            continue
        for field in FIELDS:
            if not entry.get(field) and hit.get(field):
                entry[field] = hit[field]
        if hit.get("route") not in entry["routes"]:
            entry["routes"].append(hit.get("route"))
        if hit.get("via") and hit["via"] not in entry["via"]:
            entry["via"].append(hit["via"])
    counts = {"hits": len(hits), "unique": len(pool) + len(seen_read), "alreadyRead": len(already),
              "noId": len(no_id), "pool": len(pool)}
    return {"pool": list(pool.values()), "alreadyRead": already, "noId": no_id, "counts": counts}


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    review = Path(args.review_dir)
    hit_paths = sorted((review / "search" / "hits").glob("*.json"))
    if not hit_paths:
        print(f"{review}/search/hits 底下沒有搜尋結果", file=sys.stderr)
        return 1
    hits = [h for path in hit_paths for h in json.loads(path.read_text(encoding="utf-8"))]
    index_path = Path(args.library) / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}

    result = merge(hits, index)
    (review / "search" / "pool.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    c = result["counts"]
    print(f"命中 {c['hits']} 筆 → 不重複 {c['unique']} 篇（已讀 {c['alreadyRead']}）；沒有識別碼 {c['noId']} 筆；"
          f"候選池 {c['pool']} 篇")
    return 0


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="合併三路搜尋結果成候選池")
    parser.add_argument("review_dir")
    parser.add_argument("--library", default="library")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
