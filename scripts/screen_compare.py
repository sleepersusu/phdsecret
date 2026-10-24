"""比對兩個篩選者的判斷，歸成收、排除、留給本人三類，輸出候選清單 CSV、匯入 Zotero 用的 RIS 與流程數字。

用法：uv run scripts/screen_compare.py reviews/<slug>
讀 search/pool.json、screen-a.json、screen-b.json。兩邊都收才收、兩邊都排除才排除，
其餘（任一邊不確定、意見不同、一邊漏判）一律留給本人，寧可多問也不錯殺。
flow.json 是論文方法段要交代的篩選流程數字。
"""
import csv
import json
import sys
from pathlib import Path

CSV_FIELDS = ["id", "title", "year", "authors", "venue", "routes", "status",
              "criterionA", "criterionB", "reasonA", "reasonB"]


def compare(pool, a, b):
    by_a = {d["id"]: d for d in a.get("decisions", [])}
    by_b = {d["id"]: d for d in b.get("decisions", [])}
    rows = []
    for paper in pool:
        x, y = by_a.get(paper["id"]) or {}, by_b.get(paper["id"]) or {}
        pair = (x.get("decision"), y.get("decision"))
        status = {("include", "include"): "included", ("exclude", "exclude"): "excluded"}.get(pair, "toUser")
        rows.append({**paper, "status": status,
                     "criterionA": x.get("criterion", ""), "criterionB": y.get("criterion", ""),
                     "reasonA": x.get("reason", ""), "reasonB": y.get("reason", "")})
    return rows


def flow(counts, rows):
    by_status = {s: sum(1 for r in rows if r["status"] == s) for s in ("included", "excluded", "toUser")}
    return {"hits": counts.get("hits", 0), "unique": counts.get("unique", 0),
            "alreadyRead": counts.get("alreadyRead", 0), "noId": counts.get("noId", 0),
            "screened": len(rows), **by_status}


def to_ris(rows):
    """只收 included 與 toUser；DOI 寫 DO，arXiv／PMID 寫進 N1，讓 Zotero 匯入後仍查得到。"""
    lines = []
    for row in rows:
        if row["status"] not in ("included", "toUser"):
            continue
        lines += ["TY  - JOUR", f"TI  - {row.get('title') or ''}"]
        lines += [f"AU  - {author}" for author in row.get("authors") or []]
        if row.get("year"):
            lines.append(f"PY  - {row['year']}")
        if row.get("venue"):
            lines.append(f"JO  - {row['venue']}")
        identifier = row["id"]
        if identifier.startswith("10."):
            lines.append(f"DO  - {identifier}")
        elif identifier.startswith("arxiv:"):
            lines.append(f"N1  - arXiv:{identifier[len('arxiv:'):]}")
        elif identifier.startswith("pmid:"):
            lines.append(f"N1  - PMID: {identifier[len('pmid:'):]}")
        if row.get("abstract"):
            lines.append(f"AB  - {row['abstract']}")
        lines += [f"N1  - status: {row['status']}", "ER  - ", ""]
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    search = Path(argv[0]) / "search"
    paths = {name: search / f"{name}.json" for name in ("pool", "screen-a", "screen-b")}
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        print("缺少檔案：" + "、".join(missing), file=sys.stderr)
        return 1
    data = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in paths.items()}

    rows = compare(data["pool"]["pool"], data["screen-a"], data["screen-b"])
    numbers = flow(data["pool"].get("counts", {}), rows)
    with open(search / "candidates.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({**{k: row.get(k, "") for k in CSV_FIELDS},
                             "authors": "; ".join(row.get("authors") or []),
                             "routes": ";".join(r for r in row.get("routes") or [] if r)})
    (search / "candidates.ris").write_text(to_ris(rows), encoding="utf-8")
    (search / "flow.json").write_text(json.dumps(numbers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("　".join(f"{k} {v}" for k, v in numbers.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
