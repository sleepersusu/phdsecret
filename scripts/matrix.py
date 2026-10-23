"""從所有卡片的結構化欄位產出比較矩陣 matrix.md，一篇一列。

用法：uv run scripts/matrix.py reviews/<slug>
內容直接取自已核對過引文的 card.json，矩陣本身不另附引文；要看出處點進該篇卡片。
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

    lines = [
        "| 論文 | " + " | ".join(title for _, _, title in STRUCTURED) + " |",
        "|---|" + "---|" * len(STRUCTURED),
    ]
    for path in card_paths:
        card = json.loads(path.read_text(encoding="utf-8"))
        key = card["key"]
        cells = [_cell(card.get("structured", {}).get(field)) for field, _, _ in STRUCTURED]
        lines.append(f"| [{key}](cards/{key}/card.md) | " + " | ".join(cells) + " |")

    (review_dir / "matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"寫出 {len(card_paths)} 篇的比較矩陣到 {review_dir / 'matrix.md'}")
    return 0


def _cell(value):
    text = "; ".join(item["value"] for item in field_items(value))
    return text.replace("|", "\\|") or "—"


if __name__ == "__main__":
    sys.exit(main())
