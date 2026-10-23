"""比對兩個萃取者各自寫的卡片（a.json、b.json），列出不一致的欄位交給 judge。

用法：uv run scripts/diff_cards.py reviews/<slug>/cards/<key>
寫出 diff.json。寧可多報：誤報只多花一次 judge，漏報就是卡片錯了沒人發現。
結構化欄位比值；敘述欄位是自由文字比不了字面，改以引文位置判斷是不是同一項。
"""
import json
import re
import sys
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import Path

from cardschema import DUAL_NARRATIVE, STRUCTURED, field_items, name_key
from textnorm import loosen

NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
THOUSANDS = re.compile(r"^\d{1,3}(?:,\d{3})+(?:\.\d+)?$")
MIN_SHARED_CHARS = 25


def compare(a, b):
    """回傳不一致清單 [{field, a, b, detail}]；a、b 是兩張卡片的 structured。"""
    disagreements = []
    for field, kind, _ in STRUCTURED:
        if (field in a) != (field in b):
            detail = "只有一邊有這個欄位"
        elif field not in a:
            continue
        else:
            detail = COMPARATORS[kind](field_items(a[field]), field_items(b[field]))
        if detail:
            disagreements.append({
                "field": field,
                "a": _values(a.get(field)),
                "b": _values(b.get(field)),
                "detail": detail,
            })
    return disagreements


def compare_narrative(a, b):
    """回傳敘述欄位的不一致清單 [{field, kind, onlyA, onlyB, detail}]；a、b 是兩張卡片的 narrative。"""
    disagreements = []
    for field in DUAL_NARRATIVE:
        if field not in a and field not in b:
            continue
        if (field in a) != (field in b):
            only_a, only_b, detail = a.get(field) or [], b.get(field) or [], "只有一邊有這個欄位"
        else:
            only_a, only_b = _unmatched(a[field] or [], b[field] or [], same_relation=field == "proposalRelation")
            if not only_a and not only_b:
                continue
            detail = f"只有甲 {len(only_a)} 項；只有乙 {len(only_b)} 項"
        disagreements.append({"field": field, "kind": "narrative", "onlyA": only_a, "onlyB": only_b, "detail": detail})
    return disagreements


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    card_dir = Path(argv[0])
    a_path, b_path = card_dir / "a.json", card_dir / "b.json"
    if not a_path.exists() or not b_path.exists():
        print(f"{card_dir} 要同時有 a.json 與 b.json", file=sys.stderr)
        return 1

    a = json.loads(a_path.read_text(encoding="utf-8"))
    b = json.loads(b_path.read_text(encoding="utf-8"))
    disagreements = compare(a.get("structured", {}), b.get("structured", {}))
    disagreements += compare_narrative(a.get("narrative", {}), b.get("narrative", {}))

    result = {"key": a.get("key"), "disagreements": disagreements}
    (card_dir / "diff.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{a.get('key')}: {len(disagreements)} 個欄位不一致" + "".join(f"\n- {d['field']}：{d['detail']}" for d in disagreements))
    return 0


def _unmatched(a_items, b_items, same_relation):
    """一對一配對，重疊越長越先配；回傳配不上的（只有甲, 只有乙）。"""
    pairs = []
    for i, x in enumerate(a_items):
        for j, y in enumerate(b_items):
            if same_relation and x.get("relation") != y.get("relation"):
                continue
            score = _match_score(x, y)
            if score:
                pairs.append((-score, i, j))
    used_a, used_b = set(), set()
    for _, i, j in sorted(pairs):
        if i not in used_a and j not in used_b:
            used_a.add(i)
            used_b.add(j)
    return (
        [x for i, x in enumerate(a_items) if i not in used_a],
        [y for j, y in enumerate(b_items) if j not in used_b],
    )


def _match_score(x, y):
    """同頁且引文重疊才算同一項：一方包含另一方，或共同子字串達 MIN_SHARED_CHARS；回傳重疊長度，配不上回 0。"""
    if x.get("page") != y.get("page"):
        return 0
    qx, qy = loosen(x.get("quote") or ""), loosen(y.get("quote") or "")
    if not qx or not qy:
        return 0
    shared = SequenceMatcher(None, qx, qy, autojunk=False).find_longest_match(0, len(qx), 0, len(qy)).size
    return shared if shared >= min(MIN_SHARED_CHARS, len(qx), len(qy)) else 0


def _values(value):
    return [item.get("value") for item in field_items(value)]


def _compare_enum(a_items, b_items):
    a_value = a_items[0]["value"].strip() if a_items else ""
    b_value = b_items[0]["value"].strip() if b_items else ""
    return None if a_value == b_value else f"甲「{a_value}」／乙「{b_value}」"


def _compare_names(a_items, b_items):
    return _set_detail(
        {name_key(item["value"]): item["value"] for item in a_items},
        {name_key(item["value"]): item["value"] for item in b_items},
    )


def _compare_numbers(a_items, b_items):
    return _set_detail(_numbers(a_items), _numbers(b_items))


def _set_detail(a_map, b_map):
    only_a = [a_map[key] for key in a_map.keys() - b_map.keys()]
    only_b = [b_map[key] for key in b_map.keys() - a_map.keys()]
    if not only_a and not only_b:
        return None
    return f"只有甲：{', '.join(sorted(only_a)) or '—'}；只有乙：{', '.join(sorted(only_b)) or '—'}"


def _numbers(items):
    found = {}
    for item in items:
        for raw in NUMBER.findall(item["value"]):
            cleaned = raw.replace(",", "") if THOUSANDS.match(raw) else raw.replace(",", ".")
            found[str(Decimal(cleaned).normalize())] = raw
    return found


COMPARATORS = {"enum": _compare_enum, "names": _compare_names, "numbers": _compare_numbers}


if __name__ == "__main__":
    sys.exit(main())
