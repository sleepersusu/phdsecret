"""依訊號排出本批論文的建議閱讀順序，寫 reading-order.md。

用法：uv run scripts/reading_order.py reviews/<slug>
只用已存在的資料（卡片、references.csv、無提案模式的 research-gaps.md），不引入新資訊。
排序：回顧類先讀建立全貌 → 被本批多篇引用的奠基論文 → 依模式最可能改變提案（衝突／已有人做過）
或最常被當成研究空白證據的 → key。每篇附上由訊號產生的理由。
"""
import csv
import json
import sys
from pathlib import Path

REVIEW_TYPES = {"敘述性回顧", "系統性回顧", "統合分析", "範疇回顧"}
NO_PROPOSAL = "無提案"


def rank(papers, cards, ref_rows, mode, gaps_text, summaries):
    """回傳排好序的 [{key, title, hasCard, hasSummary, signals}]；沒有卡片的排最後。"""
    cited = {}
    for row in ref_rows:
        key = row.get("inCorpus")
        if key:
            cited[key] = max(cited.get(key, 0), int(row.get("citedByCount") or 0))

    entries = []
    for paper in papers:
        key = paper["key"]
        card = cards.get(key)
        entry = {"key": key, "title": paper.get("title") or (card or {}).get("title") or key,
                 "hasCard": card is not None, "hasSummary": key in summaries}
        if card is None:
            entry["signals"], entry["sort"] = ["卡片未完成"], (1, 0, 0, 0, key)
        else:
            review, count = _is_review(card), cited.get(key, 0)
            third = gaps_text.count(f"[{key}, p.") if mode == NO_PROPOSAL else _proposal_hits(card)
            entry["signals"] = _signals(review, count, third, mode)
            entry["sort"] = (0, -int(review), -count, -third, key)
        entries.append(entry)
    entries.sort(key=lambda e: e["sort"])
    for entry in entries:
        del entry["sort"]
    return entries


def render(entries):
    lines = ["# 建議閱讀順序", "", "| # | 論文 | 理由 | 連結 |", "|---|---|---|---|"]
    for number, entry in enumerate(entries, start=1):
        key = entry["key"]
        links = ([f"[摘要](cards/{key}/summary.md)"] if entry["hasSummary"] else []) + \
                ([f"[卡片](cards/{key}/card.md)"] if entry["hasCard"] else [])
        title = entry["title"].replace("|", "\\|")
        lines.append(f"| {number} | {title} | {'；'.join(entry['signals'])} | {'・'.join(links) or '—'} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    review = Path(argv[0])
    papers_path = review / "papers.json"
    if not papers_path.exists():
        print(f"找不到 {papers_path}", file=sys.stderr)
        return 1
    papers = json.loads(papers_path.read_text(encoding="utf-8"))
    cards, summaries = {}, set()
    for paper in papers:
        card_dir = review / "cards" / paper["key"]
        if (card_dir / "card.json").exists():
            cards[paper["key"]] = json.loads((card_dir / "card.json").read_text(encoding="utf-8"))
        if (card_dir / "summary.md").exists():
            summaries.add(paper["key"])
    refs_path = review / "references.csv"
    ref_rows = list(csv.DictReader(refs_path.open(encoding="utf-8"))) if refs_path.exists() else []
    protocol_path = review / "protocol.md"
    mode = NO_PROPOSAL if protocol_path.exists() and "模式：無提案" in protocol_path.read_text(encoding="utf-8") else "已有提案"
    gaps_path = review / "research-gaps.md"
    gaps_text = gaps_path.read_text(encoding="utf-8") if mode == NO_PROPOSAL and gaps_path.exists() else ""

    entries = rank(papers, cards, ref_rows, mode, gaps_text, summaries)
    (review / "reading-order.md").write_text(render(entries), encoding="utf-8")
    print(f"寫出 {len(entries)} 篇的閱讀順序（{mode}模式）")
    return 0


def _is_review(card):
    structured = card.get("structured", {})
    article = structured.get("articleType")
    if isinstance(article, dict):
        return article.get("value") in REVIEW_TYPES
    study = structured.get("studyType")
    return isinstance(study, dict) and study.get("value") == "review"


def _proposal_hits(card):
    relations = card.get("narrative", {}).get("proposalRelation") or []
    return sum(1 for r in relations if r.get("relation") in ("衝突", "已有人做過"))


def _signals(review, count, third, mode):
    signals = (["回顧類"] if review else []) + ([f"被本批 {count} 篇引用"] if count else [])
    if third:
        signals.append(f"研究空白引用 {third} 次" if mode == NO_PROPOSAL else f"與提案衝突或已有人做過 {third} 項")
    return signals or ["無特殊訊號"]


if __name__ == "__main__":
    sys.exit(main())
