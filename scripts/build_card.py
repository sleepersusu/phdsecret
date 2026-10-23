"""把甲的卡片（a.json）套上 judge 的裁決（judge.json），合成最終卡片 card.json 與 card.md。

用法：uv run scripts/build_card.py reviews/<slug>/cards/<key>
diff.json 列出的不一致欄位，judge 判不出來或沒裁決的，記進 pending；
引文空白、頁碼不對、引文含雙引號或換行的，記進 missingEvidence。兩者都會在 card.md 標 ⚠。
"""
import json
import sys
from pathlib import Path

from cardschema import NARRATIVE, STRUCTURED, field_items

NOT_MENTIONED = "- 原文未提及"
FORBIDDEN_IN_QUOTE = ('"', "“", "”", "\n")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    card_dir = Path(argv[0])
    card = _load(card_dir / "a.json")
    diff = _load(card_dir / "diff.json", {"disagreements": []})
    judge = _load(card_dir / "judge.json", {"decisions": []})

    card["pending"] = _apply_judge(card, diff, judge)
    card["missingEvidence"] = _missing_evidence(card)

    (card_dir / "card.json").write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (card_dir / "card.md").write_text(render(card), encoding="utf-8")
    print(f"{card['key']}: 待裁決 {len(card['pending'])}、缺引文 {len(card['missingEvidence'])}")
    return 0


def render(card):
    key = card["key"]
    structured = card.get("structured", {})
    narrative = card.get("narrative", {})
    study = structured.get("studyType")

    lines = [
        f"# {card.get('title') or key}",
        "",
        f"- id：{card.get('id') or '待確認'}",
        f"- 檔案：{key}.pdf",
        f"- 研究類型：{study['value']} {_cite(key, study)}" if study else "- 研究類型：原文未提及",
    ]
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


def _apply_judge(card, diff, judge):
    decisions = {d["field"]: d for d in judge.get("decisions", [])}
    pending = []
    for disagreement in diff.get("disagreements", []):
        field = disagreement["field"]
        decision = decisions.get(field)
        if decision is None:
            pending.append({"field": field, "reason": "judge 沒有裁決這個欄位"})
        elif decision.get("status") == "resolved":
            card["structured"][field] = decision["value"]
        else:
            pending.append({"field": field, "reason": decision.get("reason", "judge 判不出來")})
    return pending


def _missing_evidence(card):
    flagged = []
    for field, _, _ in STRUCTURED:
        value = card.get("structured", {}).get(field)
        prefix = f"structured.{field}"
        if isinstance(value, dict):
            flagged += [prefix] if not _has_evidence(value) else []
        else:
            flagged += [f"{prefix}[{i}]" for i, item in enumerate(field_items(value)) if not _has_evidence(item)]

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
    lines += [f"- {item.get(label, '')} {_cite(key, item)}" for item in items]


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
        lines.append(line)


if __name__ == "__main__":
    sys.exit(main())
