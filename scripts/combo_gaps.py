"""從所有卡片的方法與資料來源，找出這批論文裡沒有一起出現過的組合，給研究空白整理當候選。

用法：uv run scripts/combo_gaps.py reviews/<slug>
寫出 combo-gaps.json。讓「沒人做過」由腳本算出來，agent 只從候選裡挑有意義的，
不憑印象宣稱；結果只代表本批論文，不代表整個領域。
"""
import json
import sys
from pathlib import Path

from cardschema import field_items, name_key


def analyze(cards):
    """回傳 {methods, dataSources, used, unused}；同一篇卡片同時有某方法與某資料來源才算用過。"""
    methods, sources, pairs = {}, {}, {}
    for card in cards:
        structured = card.get("structured", {})
        method_keys = _collect(methods, structured.get("methods"), card["key"])
        source_keys = _collect(sources, structured.get("dataSources"), card["key"])
        for m in method_keys:
            for s in source_keys:
                pairs.setdefault((m, s), set()).add(card["key"])

    used = [
        {"method": methods[m]["name"], "dataSource": sources[s]["name"], "papers": sorted(papers)}
        for (m, s), papers in pairs.items()
    ]
    used.sort(key=lambda u: (u["method"].casefold(), u["dataSource"].casefold()))

    unused = [
        {"method": mv["name"], "dataSource": sv["name"],
         "methodPapers": sorted(mv["papers"]), "dataPapers": sorted(sv["papers"])}
        for m, mv in methods.items() for s, sv in sources.items() if (m, s) not in pairs
    ]
    unused.sort(key=lambda u: (
        -(len(u["methodPapers"]) + len(u["dataPapers"])), u["method"].casefold(), u["dataSource"].casefold()
    ))
    return {"methods": _listing(methods), "dataSources": _listing(sources), "used": used, "unused": unused}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    review_dir = Path(argv[0])
    card_paths = sorted((review_dir / "cards").glob("*/card.json"))
    if not card_paths:
        print(f"{review_dir}/cards 底下沒有 card.json", file=sys.stderr)
        return 1
    cards = [json.loads(path.read_text(encoding="utf-8")) for path in card_paths]

    result = analyze(cards)
    (review_dir / "combo-gaps.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"方法 {len(result['methods'])} 個、資料來源 {len(result['dataSources'])} 個；"
        f"用過的組合 {len(result['used'])}、沒用過的組合 {len(result['unused'])}"
    )
    return 0


def _collect(registry, value, paper_key):
    """把一張卡片某欄位的名稱登記進 registry（同名合併、顯示名取第一次出現），回傳這張卡片用到的名稱鍵。"""
    keys = []
    for item in field_items(value):
        name = item.get("value") or ""
        key = name_key(name)
        if not key:
            continue
        entry = registry.setdefault(key, {"name": name, "papers": []})
        if paper_key not in entry["papers"]:
            entry["papers"].append(paper_key)
        if key not in keys:
            keys.append(key)
    return keys


def _listing(registry):
    entries = [{"name": v["name"], "papers": sorted(v["papers"])} for v in registry.values()]
    return sorted(entries, key=lambda e: e["name"].casefold())


if __name__ == "__main__":
    sys.exit(main())
