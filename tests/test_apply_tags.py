import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import apply_tags  # noqa: E402

LIBRARY = {"tags": {
    "失智症": {"synonyms": ["Dementia"], "source": "agent"},
    "穿戴式裝置": {"synonyms": ["wearable devices"], "source": "user"},
}}


def topic(value):
    return {"value": value, "quote": f"about {value}", "page": 1}


def card(key, topics, article="原始研究"):
    return {"key": key, "structured": {"articleType": {"value": article, "quote": "q", "page": 1},
                                       "topics": [topic(t) for t in topics]}}


def test_synonyms_map_to_category_case_insensitively():
    result = apply_tags.build([card("a", ["dementia", "Wearable Devices"])], LIBRARY, {})

    assert result["a"]["tags"] == ["失智症", "穿戴式裝置"]
    assert result["a"]["raw"] == ["dementia", "Wearable Devices"]
    assert result["a"]["unmapped"] == []


def test_unmapped_raw_is_kept_and_listed():
    result = apply_tags.build([card("a", ["Dementia", "介入研究"])], LIBRARY, {})

    assert result["a"]["tags"] == ["介入研究", "失智症"]
    assert result["a"]["unmapped"] == ["介入研究"]


def test_overrides_add_and_remove_with_remove_last():
    overrides = {"a": {"add": ["老化", "失智症"], "remove": ["穿戴式裝置", "老化"]}}

    result = apply_tags.build([card("a", ["wearable devices"])], LIBRARY, overrides)

    assert result["a"]["tags"] == ["失智症"]


def test_article_type_is_carried_over():
    result = apply_tags.build([card("a", [], article="系統性回顧")], LIBRARY, {})

    assert result["a"]["articleType"] == "系統性回顧"


def test_card_without_article_type_gives_none():
    result = apply_tags.build([{"key": "a", "structured": {}}], LIBRARY, {})

    assert result["a"] == {"articleType": None, "tags": [], "raw": [], "unmapped": []}


def test_main_writes_paper_tags_and_leaves_cards_unchanged(tmp_path):
    card_dir = tmp_path / "reviews" / "r1" / "cards" / "a"
    card_dir.mkdir(parents=True)
    original = json.dumps(card("a", ["Dementia"]), ensure_ascii=False)
    (card_dir / "card.json").write_text(original, encoding="utf-8")
    library = tmp_path / "library"
    library.mkdir()
    (library / "tags.json").write_text(json.dumps(LIBRARY, ensure_ascii=False), encoding="utf-8")
    review = tmp_path / "reviews" / "r1"
    (review / "tag-overrides.json").write_text(json.dumps({"a": {"add": ["老化"]}}, ensure_ascii=False), encoding="utf-8")

    code = apply_tags.main([str(review), "--library", str(library)])

    written = json.loads((review / "paper-tags.json").read_text(encoding="utf-8"))
    assert code == 0
    assert written["a"]["tags"] == ["失智症", "老化"]
    assert (card_dir / "card.json").read_text(encoding="utf-8") == original


def test_main_without_library_file_treats_all_as_unmapped(tmp_path):
    card_dir = tmp_path / "cards" / "a"
    card_dir.mkdir(parents=True)
    (card_dir / "card.json").write_text(json.dumps(card("a", ["Dementia"]), ensure_ascii=False), encoding="utf-8")

    code = apply_tags.main([str(tmp_path), "--library", str(tmp_path / "missing")])

    written = json.loads((tmp_path / "paper-tags.json").read_text(encoding="utf-8"))
    assert code == 0
    assert written["a"]["unmapped"] == ["Dementia"]


def test_main_without_cards_exits_one(tmp_path):
    assert apply_tags.main([str(tmp_path), "--library", str(tmp_path / "library")]) == 1
