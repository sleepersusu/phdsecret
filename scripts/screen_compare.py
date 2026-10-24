"""比對兩個篩選者的判斷，歸成收、排除、留給本人三類，輸出候選清單 CSV、匯入 Zotero 用的 RIS 與流程數字。

用法：uv run scripts/screen_compare.py reviews/<slug> [--final]
讀 search/pool.json、screen-a.json、screen-b.json。兩邊都收才收、兩邊都排除才排除，
其餘（任一邊不確定、意見不同、一邊漏判）一律留給本人，寧可多問也不錯殺。
flow.json 是論文方法段要交代的篩選流程數字，screenCheck 記每位篩選者漏判（pool 有、decision 沒有）與
多判（decision 有、pool 沒有）的篇數；篩選者寫的 id 先過 canonical_id 再比對。
RIS 識別碼：DOI 寫 DO；arXiv 寫 DO（10.48550/arXiv.<id>）加 UR；PMID 只寫 UR。Zotero 匯入時把 N1 當成子筆記
而非 Extra，寫在 N1 的 id 回不來；arXiv 的 DOI 則能經 canonical_id 對回同一篇。N1 只用來放 status（僅 candidates.ris）。
--final：讀 search/decisions.json（{"<id>": "include"|"exclude"}，toUser 每篇都要有），
寫 search/final.ris（included 加本人收的 toUser，不帶 status），並在 flow.json 補 final、userIncluded、userExcluded。
"""
import csv
import json
import sys
from pathlib import Path

from paperid import canonical_id

CSV_FIELDS = ["id", "title", "year", "authors", "venue", "routes", "status",
              "criterionA", "criterionB", "reasonA", "reasonB"]


def _by_id(screen):
    return {canonical_id(str(d["id"])) or d["id"]: d for d in screen.get("decisions", [])}


def screen_check(pool, a, b):
    ids = {p["id"] for p in pool}
    out = {}
    for name, screen in (("a", a), ("b", b)):
        decided = set(_by_id(screen))
        out[name] = {"missing": len(ids - decided), "unknown": len(decided - ids)}
    return out


def compare(pool, a, b):
    by_a, by_b = _by_id(a), _by_id(b)
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


def _one_line(value):
    """RIS 一行一個欄位，值裡的換行或空行會被當成新欄位或記錄分隔，所以一律壓成一行。"""
    return " ".join(str(value).split())


def to_ris(rows, with_status=True):
    """只收 included 與 toUser；識別碼寫法見模組說明。"""
    lines = []
    for row in rows:
        if row["status"] not in ("included", "toUser"):
            continue
        lines += ["TY  - JOUR", f"TI  - {_one_line(row.get('title') or '')}"]
        lines += [f"AU  - {_one_line(author)}" for author in row.get("authors") or []]
        if row.get("year"):
            lines.append(f"PY  - {_one_line(row['year'])}")
        if row.get("venue"):
            lines.append(f"JO  - {_one_line(row['venue'])}")
        identifier = row["id"]
        if identifier.startswith("10."):
            lines.append(f"DO  - {_one_line(identifier)}")
        elif identifier.startswith("arxiv:"):
            arxiv = _one_line(identifier[len('arxiv:'):])
            lines += [f"DO  - 10.48550/arXiv.{arxiv}", f"UR  - https://arxiv.org/abs/{arxiv}"]
        elif identifier.startswith("pmid:"):
            lines.append(f"UR  - https://pubmed.ncbi.nlm.nih.gov/{_one_line(identifier[len('pmid:'):])}/")
        if row.get("abstract"):
            lines.append(f"AB  - {_one_line(row['abstract'])}")
        if with_status:
            lines.append(f"N1  - status: {row['status']}")
        lines += ["ER  - ", ""]
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    final = "--final" in argv
    argv = [a for a in argv if a != "--final"]
    search = Path(argv[0]) / "search"
    paths = {name: search / f"{name}.json" for name in ("pool", "screen-a", "screen-b")}
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        print("缺少檔案：" + "、".join(missing), file=sys.stderr)
        return 1
    data = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in paths.items()}

    rows = compare(data["pool"]["pool"], data["screen-a"], data["screen-b"])
    numbers = flow(data["pool"].get("counts", {}), rows)
    if final:
        return _write_final(search, rows, numbers)
    numbers["screenCheck"] = screen_check(data["pool"]["pool"], data["screen-a"], data["screen-b"])
    with open(search / "candidates.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({**{k: row.get(k, "") for k in CSV_FIELDS},
                             "authors": "; ".join(row.get("authors") or []),
                             "routes": ";".join(r for r in row.get("routes") or [] if r)})
    (search / "candidates.ris").write_text(to_ris(rows), encoding="utf-8")
    (search / "flow.json").write_text(json.dumps(numbers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("　".join(f"{k} {v}" for k, v in numbers.items() if k != "screenCheck"))
    for name, counts in numbers["screenCheck"].items():
        if counts["missing"] or counts["unknown"]:
            print(f"警告：篩選者 {name.upper()} 漏判 {counts['missing']} 篇、多判（不在候選池）{counts['unknown']} 篇")
    return 0


def _write_final(search, rows, numbers):
    path = search / "decisions.json"
    if not path.exists():
        print(f"缺少 {path}：請先把本人對 toUser 每篇的決定寫成 {{\"<id>\": \"include\"|\"exclude\"}}", file=sys.stderr)
        return 1
    decided = {canonical_id(str(k)) or k: v for k, v in json.loads(path.read_text(encoding="utf-8")).items()}
    undecided = [r["id"] for r in rows if r["status"] == "toUser" and decided.get(r["id"]) not in ("include", "exclude")]
    if undecided:
        print("decisions.json 缺少這些 toUser 論文的決定（每篇都要有 include 或 exclude）：" + "、".join(undecided),
              file=sys.stderr)
        return 1
    kept = [r for r in rows if r["status"] == "included" or (r["status"] == "toUser" and decided[r["id"]] == "include")]
    user_in = sum(1 for r in kept if r["status"] == "toUser")
    (search / "final.ris").write_text(to_ris(kept, with_status=False), encoding="utf-8")
    flow_path = search / "flow.json"
    existing = json.loads(flow_path.read_text(encoding="utf-8")) if flow_path.exists() else numbers
    existing.update({"final": len(kept), "userIncluded": user_in, "userExcluded": numbers["toUser"] - user_in})
    flow_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"final {len(kept)}（機器收 {len(kept) - user_in}＋本人收 {user_in}；本人排除 {numbers['toUser'] - user_in}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
