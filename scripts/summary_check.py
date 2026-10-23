"""檢查精簡摘要：每句都有來源標記、標記都對得到卡片項目、涵蓋研究問題／設計／結論／限制四塊。

用法：uv run scripts/summary_check.py reviews/<slug>/cards/<key>
讀 summary.md 與 card.json。摘要只能改寫卡片裡核對過的項目，所以每句都要指回卡片；
四塊必須涵蓋，避免摘要只挑好話講（卡片上該塊本來就空的不強制）。有問題 exit 1。
"""
import json
import re
import sys
from pathlib import Path

from cardschema import DUAL_NARRATIVE, SINGLE_VALUE_FIELDS, STRUCTURED, TOPICS, field_items

MARKER = re.compile(r"\[([A-Za-z]+(?:\.[^\]#]+)?)(?:#(\d+))?\]")
SENTENCE_BREAK = re.compile(r"(?<=[。！？])|(?<=\.)\s+|\n+")
STRUCTURED_FIELDS = {field for field, _, _ in STRUCTURED}
BLOCKS = [
    ("研究問題", ["researchQuestion"]),
    ("研究設計", ["methods", "designNotes", "dataSources"]),
    ("結論", ["findings", "results"]),
    ("限制", ["limitations"]),
]


def check(text, card):
    """回傳問題清單；空清單代表通過。"""
    problems, used = [], set()
    for sentence in _sentences(text):
        markers = MARKER.findall(sentence)
        if not markers:
            problems.append(f"無來源：{sentence}")
            continue
        for field, number in markers:
            index = int(number) if number else None
            if _resolves(card, field, index):
                used.add(field)
            else:
                problems.append(f"標記無效：[{field}#{number}]" if number else f"標記無效：[{field}]")
    for block, fields in BLOCKS:
        if any(_items(card, f) for f in fields) and not used.intersection(fields):
            problems.append(f"缺少{block}")
    return problems


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    card_dir = Path(argv[0])
    summary_path, card_path = card_dir / "summary.md", card_dir / "card.json"
    for path in (summary_path, card_path):
        if not path.exists():
            print(f"找不到 {path}", file=sys.stderr)
            return 1
    card = json.loads(card_path.read_text(encoding="utf-8"))
    problems = check(summary_path.read_text(encoding="utf-8"), card)
    key = card.get("key")
    if problems:
        print(f"{key}: 摘要有 {len(problems)} 個問題" + "".join(f"\n- {p}" for p in problems))
        return 1
    print(f"{key}: 摘要通過")
    return 0


def _sentences(text):
    lines = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    return [s.strip() for s in SENTENCE_BREAK.split("\n".join(lines)) if s and s.strip()]


def _items(card, field):
    structured, narrative = card.get("structured", {}), card.get("narrative", {})
    if field.startswith("custom."):
        return (narrative.get("custom") or {}).get(field[len("custom."):]) or []
    if field == TOPICS:
        return structured.get(TOPICS) or []
    if field in STRUCTURED_FIELDS:
        return field_items(structured.get(field))
    if field in DUAL_NARRATIVE:
        return narrative.get(field) or []
    return []


def _resolves(card, field, index):
    """單值欄位不帶編號；其餘欄位要帶編號且在範圍內。"""
    items = _items(card, field)
    if field in SINGLE_VALUE_FIELDS:
        return index is None and bool(items)
    return index is not None and 1 <= index <= len(items)


if __name__ == "__main__":
    sys.exit(main())
