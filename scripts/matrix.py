"""從所有卡片的結構化欄位產出比較矩陣 matrix.md，一篇一列。

用法：uv run scripts/matrix.py reviews/<slug>
內容直接取自已核對過引文的 card.json，矩陣本身不另附引文；要看出處點進該篇卡片。
reviews/<slug>/paper-tags.json 存在時多一欄「標籤」，內容是歸併後的類別。
"""
import json
import sys
from pathlib import Path

from cardschema import STRUCTURED, field_items


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    review_dir = Path(argv[0])
    card_paths = sorted((review_dir / "cards").glob("*/card.json"))
    if not card_paths:
        print(f"{review_dir}/cards 底下沒有 card.json", file=sys.stderr)
        return 1

    tags_path = review_dir / "paper-tags.json"
    paper_tags = json.loads(tags_path.read_text(encoding="utf-8")) if tags_path.exists() else None
    headers = [title for _, _, title in STRUCTURED] + (["標籤"] if paper_tags is not None else [])

    lines = [
        "| 論文 | " + " | ".join(headers) + " |",
        "|---|" + "---|" * len(headers),
    ]
    for path in card_paths:
        card = json.loads(path.read_text(encoding="utf-8"))
        key = card["key"]
        cells = [_cell(card.get("structured", {}).get(field)) for field, _, _ in STRUCTURED]
        if paper_tags is not None:
            cells.append(_escape("; ".join(paper_tags.get(key, {}).get("tags", []))))
        lines.append(f"| [{key}](cards/{key}/card.md) | " + " | ".join(cells) + " |")

    (review_dir / "matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"寫出 {len(card_paths)} 篇的比較矩陣到 {review_dir / 'matrix.md'}")
    return 0


def _cell(value):
    return _escape("; ".join(item["value"] for item in field_items(value)))


def _escape(text):
    return text.replace("|", "\\|") or "—"


if __name__ == "__main__":
    sys.exit(main())
