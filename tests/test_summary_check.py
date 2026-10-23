import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import summary_check  # noqa: E402


def item(value, page=3):
    return {"value": value, "quote": f"we report {value}", "page": page}


def note(text, page=3):
    return {"text": text, "quote": f"evidence for {text}", "page": page}


def card(**narrative_overrides):
    narrative = {
        "researchQuestion": [note("能否提早預測")],
        "designNotes": [],
        "findings": [note("比既有分數好"), note("外部驗證下降")],
        "contributions": [],
        "limitations": [note("單一醫院")],
        "proposalRelation": [],
        "custom": {"Source of data": [note("回溯性資料")]},
    }
    narrative.update(narrative_overrides)
    return {
        "key": "smith2023",
        "structured": {
            "studyType": item("實證研究", 1),
            "articleType": item("原始研究", 1),
            "methods": [item("Transformer")],
            "results": [item("AUROC 0.89")],
            "topics": [item("敗血症", 1)],
        },
        "narrative": narrative,
    }


GOOD = "這篇想知道能否提早預測 [researchQuestion#1]。作者用 Transformer [methods#1]。結果比既有分數好 [findings#1]。但只用單一醫院資料 [limitations#1]。"


def test_good_summary_passes():
    assert summary_check.check(GOOD, card()) == []


def test_sentence_without_marker_is_reported():
    problems = summary_check.check(GOOD + "這是很重要的研究。", card())

    assert problems == ["無來源：這是很重要的研究。"]


def test_marker_for_unknown_field_is_invalid():
    problems = summary_check.check(GOOD + "經費來自 NIH [funding#1]。", card())

    assert problems == ["標記無效：[funding#1]"]


def test_marker_index_out_of_range_is_invalid():
    problems = summary_check.check(GOOD + "另有發現 [findings#3]。", card())

    assert problems == ["標記無效：[findings#3]"]


def test_single_value_and_topic_markers_are_valid():
    text = GOOD + "這是原始研究 [articleType]，屬實證研究 [studyType]，主題是敗血症 [topics#1]。"

    assert summary_check.check(text, card()) == []


def test_single_value_marker_with_index_is_invalid():
    problems = summary_check.check(GOOD + "這是原始研究 [articleType#1]。", card())

    assert problems == ["標記無效：[articleType#1]"]


def test_custom_marker_resolves():
    assert summary_check.check(GOOD + "資料是回溯性的 [custom.Source of data#1]。", card()) == []


def test_missing_limitation_block_is_reported():
    text = "這篇想知道能否提早預測 [researchQuestion#1]。作者用 Transformer [methods#1]。結果比既有分數好 [findings#1]。"

    assert summary_check.check(text, card()) == ["缺少限制"]


def test_empty_limitations_on_card_are_not_required():
    text = "這篇想知道能否提早預測 [researchQuestion#1]。作者用 Transformer [methods#1]。結果比既有分數好 [findings#1]。"

    assert summary_check.check(text, card(limitations=[])) == []


def test_design_block_satisfied_by_design_notes():
    c = card(designNotes=[note("回溯性世代")])
    c["structured"]["methods"] = []
    text = "這篇想知道能否提早預測 [researchQuestion#1]。採回溯性世代 [designNotes#1]。結果比既有分數好 [findings#1]。但只用單一醫院資料 [limitations#1]。"

    assert summary_check.check(text, c) == []


def test_main_exit_codes(tmp_path):
    (tmp_path / "card.json").write_text(json.dumps(card(), ensure_ascii=False), encoding="utf-8")
    (tmp_path / "summary.md").write_text(GOOD, encoding="utf-8")
    assert summary_check.main([str(tmp_path)]) == 0

    (tmp_path / "summary.md").write_text(GOOD + "沒有來源的句子。", encoding="utf-8")
    assert summary_check.main([str(tmp_path)]) == 1


def test_main_without_summary_exits_one(tmp_path):
    (tmp_path / "card.json").write_text(json.dumps(card(), ensure_ascii=False), encoding="utf-8")

    assert summary_check.main([str(tmp_path)]) == 1
