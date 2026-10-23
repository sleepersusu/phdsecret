"""停 1 盤點後比對文獻庫，列出本批中以前讀過、可以沿用舊卡片的論文，寫 known.json。

用法：uv run scripts/library_lookup.py reviews/<slug> [--library library]
只列 primary 在別批的篇：primary 就在本批，代表是本批自己做的卡片，沒有東西可沿用。
文獻庫還沒建立時當作空庫。
"""
import argparse
import json
import sys
from pathlib import Path

from paperid import canonical_id


def lookup(papers, index, review_name):
    known = []
    for paper in papers:
        cid = canonical_id(paper.get("id"))
        primary = (index.get("papers", {}).get(cid) or {}).get("primary") if cid else None
        if primary and primary["review"] != review_name:
            known.append({"key": paper["key"], "id": cid,
                          "source": {"review": primary["review"], "key": primary["key"]}})
    return known


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    review = Path(args.review_dir)
    papers_path = review / "papers.json"
    if not papers_path.exists():
        print(f"找不到 {papers_path}", file=sys.stderr)
        return 1
    index_path = Path(args.library) / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    papers = json.loads(papers_path.read_text(encoding="utf-8"))

    known = lookup(papers, index, review.name)
    (review / "known.json").write_text(json.dumps(known, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"以前讀過、可沿用舊卡片的論文 {len(known)} 篇" + "".join(
        f"\n- {k['key']} ← {k['source']['review']}/{k['source']['key']}" for k in known))
    return 0


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="比對文獻庫，列出本批以前讀過的論文")
    parser.add_argument("review_dir")
    parser.add_argument("--library", default="library")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
