"""依標籤字典把每篇卡片的原始標籤歸到類別，套上本人的單篇修改，寫出 paper-tags.json。

用法：uv run scripts/apply_tags.py reviews/<slug> [--library library]
卡片本身不改：card.json 保留原始標籤與引文當證據，歸併結果只寫在 paper-tags.json；
本人改了 library/tags.json 或 reviews/<slug>/tag-overrides.json 之後重跑即可。
"""
import argparse
import json
import sys
from pathlib import Path

from cardschema import TOPICS


def build(cards, library, overrides):
    """回傳 {key: {articleType, tags, raw, unmapped}}；對不到字典的原始寫法保留原字並列入 unmapped。"""
    lookup = {}
    for name, entry in library.get("tags", {}).items():
        lookup[name.casefold()] = name
        for synonym in entry.get("synonyms", []):
            lookup[synonym.casefold()] = name

    result = {}
    for card in cards:
        structured = card.get("structured", {})
        raw = [t["value"] for t in structured.get(TOPICS) or [] if t.get("value")]
        tags, unmapped = set(), []
        for value in raw:
            name = lookup.get(value.strip().casefold())
            if name:
                tags.add(name)
            else:
                tags.add(value.strip())
                unmapped.append(value)
        override = overrides.get(card["key"], {})
        tags.update(override.get("add", []))
        tags.difference_update(override.get("remove", []))
        article = structured.get("articleType")
        result[card["key"]] = {
            "articleType": article.get("value") if isinstance(article, dict) else None,
            "tags": sorted(tags, key=str.casefold),
            "raw": raw,
            "unmapped": unmapped,
        }
    return result


def main(argv=None):
    args = _parse_args(argv)
    review = Path(args.review_dir)
    card_paths = sorted((review / "cards").glob("*/card.json"))
    if not card_paths:
        print(f"{review}/cards 底下沒有 card.json", file=sys.stderr)
        return 1
    cards = [json.loads(path.read_text(encoding="utf-8")) for path in card_paths]
    library = _load(Path(args.library) / "tags.json", {"tags": {}})
    overrides = _load(review / "tag-overrides.json", {})

    result = build(cards, library, overrides)

    (review / "paper-tags.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unmapped = sum(len(entry["unmapped"]) for entry in result.values())
    print(f"寫出 {len(result)} 篇的標籤；字典沒有的寫法 {unmapped} 個")
    return 0


def _load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="依標籤字典產出每篇論文的歸併標籤")
    parser.add_argument("review_dir")
    parser.add_argument("--library", default="library")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
