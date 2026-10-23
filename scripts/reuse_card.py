"""把文獻庫裡以前做過的卡片複製成本批的 a.json，給沿用流程接著合成、核對。

用法：uv run scripts/reuse_card.py reviews/<slug> <key> --source <review>/<key> [--clear-relation]
key 改成本批的 key：引文標記會照新 key 渲染，再用本批 PDF 核對，對不上就代表 PDF 版本不同。
上一批的待裁決、缺引文、補漏計數是那一批的狀態，不帶過來，由本批重新合成。
無提案模式加 --clear-relation：沒有提案可對照，跟提案的關係清空。來源有 summary.md 就一併複製。
"""
import argparse
import copy
import json
import sys
from pathlib import Path

BATCH_STATE = ("pending", "missingEvidence", "auditAdded")


def reuse(source_card, new_key, clear_relation):
    card = {k: copy.deepcopy(v) for k, v in source_card.items() if k not in BATCH_STATE}
    card["key"] = new_key
    if clear_relation:
        card.setdefault("narrative", {})["proposalRelation"] = []
    return card


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    review = Path(args.review_dir)
    source_dir = review.parent / Path(args.source).parent.name / "cards" / Path(args.source).name
    source_path = source_dir / "card.json"
    if not source_path.exists():
        print(f"找不到來源卡片 {source_path}", file=sys.stderr)
        return 1

    card = reuse(json.loads(source_path.read_text(encoding="utf-8")), args.key, args.clear_relation)
    target = review / "cards" / args.key
    target.mkdir(parents=True, exist_ok=True)
    (target / "a.json").write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = source_dir / "summary.md"
    if summary.exists():
        (target / "summary.md").write_text(summary.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"{args.key}: 沿用 {args.source}" + ("，摘要一併複製" if summary.exists() else "，來源沒有摘要"))
    return 0


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="把文獻庫裡的舊卡片複製成本批的 a.json")
    parser.add_argument("review_dir")
    parser.add_argument("key")
    parser.add_argument("--source", required=True, help="<review>/<key>")
    parser.add_argument("--clear-relation", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
