"""檢查卡片的每個一級章節：至少一項引文落在該節頁碼範圍內，或 auditor 寫明為何沒有。

用法：uv run scripts/coverage_check.py reviews/<slug>/cards/<key>
讀 card.json（必要）與 audit.json（可選），寫出 coverage.json。
被引用 0 次的章節通常代表那幾頁漏讀了；既沒項目也沒理由的章節、或卡片沒有章節拆解時 exit 1。
"""
import json
import sys
from pathlib import Path

from cardschema import DUAL_NARRATIVE, STRUCTURED, field_items


def check(card, audit):
    """回傳 {sections: [{heading, page, endPage, items, reason}], uncovered: [heading]}。"""
    pages = _item_pages(card)
    reasons = {r.get("heading"): r.get("reason") for r in audit.get("sectionReasons", [])}
    sections = []
    for row in card.get("structure", []):
        start = row.get("page")
        end = row.get("endPage") or start
        count = sum(1 for page in pages if isinstance(start, int) and start <= page <= end)
        sections.append({
            "heading": row.get("heading"),
            "page": start,
            "endPage": end,
            "items": count,
            "reason": reasons.get(row.get("heading")),
        })
    uncovered = [s["heading"] for s in sections if s["items"] == 0 and not s["reason"]]
    return {"sections": sections, "uncovered": uncovered}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    card_dir = Path(argv[0])
    card_path = card_dir / "card.json"
    if not card_path.exists():
        print(f"找不到 {card_path}", file=sys.stderr)
        return 1
    card = json.loads(card_path.read_text(encoding="utf-8"))
    audit_path = card_dir / "audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}

    result = check(card, audit)
    (card_dir / "coverage.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    key = card.get("key")
    if not result["sections"]:
        print(f"{key}: 沒有章節拆解，無法檢查涵蓋", file=sys.stderr)
        return 1
    for s in result["sections"]:
        reason = f"；理由：{s['reason']}" if s["items"] == 0 and s["reason"] else ""
        print(f"- {s['heading']}（p.{s['page']}–{s['endPage']}）：{s['items']} 項{reason}")
    if result["uncovered"]:
        print(f"{key}: 未涵蓋 {len(result['uncovered'])} 節：{'、'.join(result['uncovered'])}")
        return 1
    print(f"{key}: 章節全部涵蓋")
    return 0


def _item_pages(card):
    narrative = card.get("narrative", {})
    items = [item for field, _, _ in STRUCTURED for item in field_items(card.get("structured", {}).get(field))]
    items += [item for field in DUAL_NARRATIVE for item in narrative.get(field) or []]
    items += [item for values in (narrative.get("custom") or {}).values() for item in values]
    return [item.get("page") for item in items if isinstance(item.get("page"), int)]


if __name__ == "__main__":
    sys.exit(main())
