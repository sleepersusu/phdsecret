"""把甲的卡片（a.json）套上 judge 的裁決（judge.json）與 auditor 的補漏（audit.json），合成最終卡片 card.json 與 card.md。

用法：uv run scripts/build_card.py reviews/<slug>/cards/<key>
diff.json 列出的不一致欄位，judge 判不出來或沒裁決的，記進 pending；
甲乙各自下的領域標籤（structured.topics）不比對，取聯集：b.json 裡名稱不重複的接在甲的後面。
auditor 補到卡片沒有的欄位、或對已有值的單值欄位（研究類型、文章類型）提出補充，也記進 pending（單值欄位只能有一個，要人看）；
引文空白、頁碼不對、引文含雙引號或換行的，記進 missingEvidence。兩者都會在 card.md 標 ⚠。
補漏項目帶 source=audit，card.md 標「（補漏）」，讓人知道哪些是第二輪才找到的。
"""
import json
import sys
from pathlib import Path

from cardschema import DUAL_NARRATIVE, NARRATIVE, SINGLE_VALUE_FIELDS, STRUCTURED, TOPICS, field_items, name_key

NOT_MENTIONED = "- 原文未提及"
FORBIDDEN_IN_QUOTE = ('"', "“", "”", "\n")
STRUCTURED_FIELDS = {field for field, _, _ in STRUCTURED}
AUDIT_MARK = "（補漏）"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    card_dir = Path(argv[0])
    card = _load(card_dir / "a.json")
    _merge_topics(card, _load(card_dir / "b.json", {}))
    diff = _load(card_dir / "diff.json", {"disagreements": []})
    judge = _load(card_dir / "judge.json", {"decisions": []})
    audit = _load(card_dir / "audit.json", {})

    card["pending"] = _apply_judge(card, diff, judge)
    card["auditAdded"] = _apply_audit(card, audit, card["pending"])
    card["missingEvidence"] = _missing_evidence(card)

    (card_dir / "card.json").write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (card_dir / "card.md").write_text(render(card), encoding="utf-8")
    print(f"{card['key']}: 待裁決 {len(card['pending'])}、缺引文 {len(card['missingEvidence'])}、補漏 {card['auditAdded']}")
    return 0


def render(card):
    key = card["key"]
    structured = card.get("structured", {})
    narrative = card.get("narrative", {})
    study = structured.get("studyType")
    article = structured.get("articleType")

    lines = [
        f"# {card.get('title') or key}",
        "",
        f"- id：{card.get('id') or '待確認'}",
        f"- 檔案：{key}.pdf",
        f"- 研究類型：{study['value']} {_cite(key, study)}" if study else "- 研究類型：原文未提及",
        f"- 文章類型：{article['value']} {_cite(key, article)}" if article else "- 文章類型：原文未提及",
    ]
    _section(lines, "## 領域標籤", key, structured.get(TOPICS), "value")
    _section(lines, "## 研究問題", key, narrative.get("researchQuestion"), "text")
    lines += ["", "## 研究設計"]
    _section(lines, "### 資料來源", key, structured.get("dataSources"), "value")
    _section(lines, "### 樣本數", key, structured.get("sampleSize"), "value")
    _section(lines, "### 方法", key, structured.get("methods"), "value")
    _section(lines, "### 說明", key, narrative.get("designNotes"), "text")
    lines += ["", "## 主要發現"]
    _section(lines, "### 數字", key, structured.get("results"), "value")
    _section(lines, "### 結論", key, narrative.get("findings"), "text")
    _section(lines, "## 貢獻", key, narrative.get("contributions"), "text")
    _section(lines, "## 限制", key, narrative.get("limitations"), "text")
    _structure_table(lines, key, card.get("structure", []))
    _proposal_relation(lines, key, narrative.get("proposalRelation", []))

    for name, items in (narrative.get("custom") or {}).items():
        _section(lines, f"## {name}", key, items, "text")
    if card.get("pending"):
        lines += ["", "## ⚠ 待本人裁決"] + [f"- {p['field']}：{p['reason']}" for p in card["pending"]]
    if card.get("missingEvidence"):
        lines += ["", "## ⚠ 缺引文"] + [f"- {path}" for path in card["missingEvidence"]]
    return "\n".join(lines) + "\n"


def _load(path, default=None):
    if not path.exists():
        if default is None:
            raise SystemExit(f"找不到 {path}")
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _merge_topics(card, other):
    """甲乙的標籤取聯集；名稱正規化後相同的只留甲的那筆。"""
    structured = card.setdefault("structured", {})
    mine = structured.get(TOPICS) or []
    seen = {name_key(t.get("value")) for t in mine}
    extra = []
    for topic in (other.get("structured") or {}).get(TOPICS) or []:
        key = name_key(topic.get("value"))
        if key and key not in seen:
            seen.add(key)
            extra.append(topic)
    if mine or extra:
        structured[TOPICS] = mine + extra


def _apply_judge(card, diff, judge):
    decisions = {d["field"]: d for d in judge.get("decisions", [])}
    pending = []
    for disagreement in diff.get("disagreements", []):
        field = disagreement["field"]
        decision = decisions.get(field)
        if decision is None:
            pending.append({"field": field, "reason": "judge 沒有裁決這個欄位"})
        elif decision.get("status") == "resolved":
            value = decision["value"]
            if field in SINGLE_VALUE_FIELDS and isinstance(value, list):
                if len(value) != 1:
                    pending.append({"field": field, "reason": f"judge 對單值欄位給了 {len(value)} 個值，請本人確認"})
                    continue
                value = value[0]
            target = "structured" if field in STRUCTURED_FIELDS else "narrative"
            card.setdefault(target, {})[field] = value
        else:
            pending.append({"field": field, "reason": decision.get("reason", "judge 判不出來")})
    return pending


def _apply_audit(card, audit, pending):
    """把 auditor 補的項目附上 source=audit 接到對應欄位尾端，回傳補了幾項。"""
    added = 0
    for field, items in (audit.get("additions") or {}).items():
        items = [dict(item, source="audit") for item in items]
        structured = card.setdefault("structured", {})
        narrative = card.setdefault("narrative", {})
        if field in SINGLE_VALUE_FIELDS:
            if structured.get(field) or not items:
                pending.append({"field": field, "reason": "auditor 對單值欄位提出補充；這個欄位只能有一個值，請本人確認"})
                continue
            structured[field] = items[0]
            added += 1
            continue
        if field.startswith("custom."):
            container, name = narrative.setdefault("custom", {}), field[len("custom."):]
        elif field in STRUCTURED_FIELDS:
            container, name = structured, field
        elif field in DUAL_NARRATIVE:
            container, name = narrative, field
        else:
            pending.append({"field": field, "reason": "auditor 補了卡片沒有的欄位"})
            continue
        container[name] = (container.get(name) or []) + items
        added += len(items)
    return added


def _audit_mark(item):
    return AUDIT_MARK if item.get("source") == "audit" else ""


def _missing_evidence(card):
    flagged = []
    for field, _, _ in STRUCTURED:
        value = card.get("structured", {}).get(field)
        prefix = f"structured.{field}"
        if isinstance(value, dict):
            flagged += [prefix] if not _has_evidence(value) else []
        else:
            flagged += [f"{prefix}[{i}]" for i, item in enumerate(field_items(value)) if not _has_evidence(item)]

    flagged += [
        f"structured.{TOPICS}[{i}]" for i, item in enumerate(card.get("structured", {}).get(TOPICS) or [])
        if not _has_evidence(item)
    ]

    narrative = card.get("narrative", {})
    for field, _ in NARRATIVE:
        flagged += [f"narrative.{field}[{i}]" for i, item in enumerate(narrative.get(field) or []) if not _has_evidence(item)]
    for i, item in enumerate(narrative.get("proposalRelation") or []):
        if not _has_evidence(item):
            flagged.append(f"narrative.proposalRelation[{i}]")
        elif item.get("proposalQuote") and not _usable_quote(item["proposalQuote"]):
            flagged.append(f"narrative.proposalRelation[{i}].proposalQuote")
    for name, items in (narrative.get("custom") or {}).items():
        flagged += [f"narrative.custom.{name}[{i}]" for i, item in enumerate(items) if not _has_evidence(item)]
    flagged += [
        f"structure[{i}]" for i, row in enumerate(card.get("structure", []))
        if not _has_evidence({"quote": row.get("heading"), "page": row.get("page")})
    ]
    return flagged


def _has_evidence(item):
    page = item.get("page")
    return _usable_quote(item.get("quote")) and isinstance(page, int) and page >= 1


def _usable_quote(quote):
    return bool(quote and quote.strip()) and not any(mark in quote for mark in FORBIDDEN_IN_QUOTE)


def _cite(key, item):
    return f'"{item["quote"]}" [{key}, p.{item["page"]}]' if _has_evidence(item) else "⚠ 缺引文"


def _section(lines, heading, key, items, label):
    lines += ["", heading]
    if not items:
        lines.append(NOT_MENTIONED)
        return
    lines += [f"- {item.get(label, '')} {_cite(key, item)}{_audit_mark(item)}" for item in items]


def _structure_table(lines, key, rows):
    lines += ["", "## 結構拆解"]
    if not rows:
        lines.append(NOT_MENTIONED)
        return
    lines += ["| 節 | 頁 | 在做什麼 |", "|---|---|---|"]
    for row in rows:
        heading = _cite(key, {"quote": row.get("heading"), "page": row.get("page")})
        end = row.get("endPage")
        pages = f"{row.get('page')}–{end}" if end and end != row.get("page") else f"{row.get('page')}"
        lines.append(f"| {heading} | {pages} | {row.get('purpose', '')} |")


def _proposal_relation(lines, key, items):
    lines += ["", "## 跟提案的關係"]
    if not items:
        lines.append(NOT_MENTIONED)
        return
    for item in items:
        line = f"- 【{item.get('relation', '')}】{item.get('text', '')} {_cite(key, item)}"
        if item.get("proposalQuote") and _usable_quote(item["proposalQuote"]):
            line += f'；提案："{item["proposalQuote"]}" [proposal]'
        line += _audit_mark(item)
        lines.append(line)


if __name__ == "__main__":
    sys.exit(main())
