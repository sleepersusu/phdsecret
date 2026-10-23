import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import diff_cards  # noqa: E402


def item(value, page=3):
    return {"value": value, "quote": f"quote about {value}", "page": page}


def structured(**overrides):
    base = {
        "studyType": item("實證研究", 1),
        "dataSources": [item("MIMIC-IV")],
        "sampleSize": [item("45,121 ICU stays")],
        "methods": [item("Transformer")],
        "results": [item("AUROC 0.89 (internal)")],
    }
    base.update(overrides)
    return base


def test_identical_cards_have_no_disagreement():
    assert diff_cards.compare(structured(), structured()) == []


def test_names_compare_ignoring_case_and_punctuation():
    a = structured(dataSources=[item("MIMIC-IV")])
    b = structured(dataSources=[item("mimic iv")])

    assert diff_cards.compare(a, b) == []


def test_numbers_compare_ignoring_thousands_separator():
    a = structured(sampleSize=[item("45,121 ICU stays")])
    b = structured(sampleSize=[item("45121 stays")])

    assert diff_cards.compare(a, b) == []


def test_missing_result_number_is_a_disagreement():
    a = structured(results=[item("AUROC 0.89 (internal)")])
    b = structured(results=[item("AUROC 0.89 (internal)"), item("AUROC 0.76 (external)", 7)])

    disagreements = diff_cards.compare(a, b)

    assert [d["field"] for d in disagreements] == ["results"]
    assert "0.76" in disagreements[0]["detail"]


def test_study_type_must_match_exactly():
    a = structured(studyType=item("實證研究", 1))
    b = structured(studyType=item("review", 1))

    assert [d["field"] for d in diff_cards.compare(a, b)] == ["studyType"]


def test_field_missing_on_one_side_is_a_disagreement():
    a = structured()
    b = structured()
    del b["methods"]

    assert [d["field"] for d in diff_cards.compare(a, b)] == ["methods"]


def test_main_writes_diff_json(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({"key": "k", "structured": structured()}), encoding="utf-8")
    (tmp_path / "b.json").write_text(
        json.dumps({"key": "k", "structured": structured(methods=[item("LSTM")])}), encoding="utf-8"
    )

    code = diff_cards.main([str(tmp_path)])

    written = json.loads((tmp_path / "diff.json").read_text(encoding="utf-8"))
    assert code == 0
    assert [d["field"] for d in written["disagreements"]] == ["methods"]


def note(text, quote, page=3, **extra):
    return {"text": text, "quote": quote, "page": page, **extra}


def narrative(**fields):
    base = {name: [] for name in diff_cards.DUAL_NARRATIVE}
    base.update(fields)
    return base


def test_narrative_items_match_when_one_quote_contains_the_other():
    a = narrative(limitations=[note("外部資料表現差", "the model failed on external data")])
    b = narrative(limitations=[note("泛化不足", "Notably, the model failed on external data from site B")])

    assert diff_cards.compare_narrative(a, b) == []


def test_narrative_items_match_on_shared_run_of_25_chars():
    a = narrative(designNotes=[note("成人", "Overall the cohort included adult patients from two sites")])
    b = narrative(designNotes=[note("成人病人", "In summary the cohort included adult patients with sepsis")])

    assert diff_cards.compare_narrative(a, b) == []


def test_narrative_items_with_shared_run_under_25_chars_do_not_match():
    a = narrative(findings=[note("高齡死亡率高", "we observed higher mortality in older groups")])
    b = narrative(findings=[note("差異不顯著", "mortality in older groups was not significant")])

    disagreements = diff_cards.compare_narrative(a, b)

    assert [d["field"] for d in disagreements] == ["findings"]
    assert len(disagreements[0]["onlyA"]) == 1 and len(disagreements[0]["onlyB"]) == 1
    assert disagreements[0]["kind"] == "narrative"


def test_narrative_items_on_different_pages_do_not_match():
    a = narrative(findings=[note("結論", "the model failed on external data", page=3)])
    b = narrative(findings=[note("結論", "the model failed on external data", page=4)])

    assert [d["field"] for d in diff_cards.compare_narrative(a, b)] == ["findings"]


def test_narrative_matching_is_one_to_one_preferring_longest_overlap():
    a = narrative(designNotes=[note("世代", "the cohort included adult patients from two sites")])
    longer = note("世代", "the cohort included adult patients from two sites")
    shorter = note("成人", "the cohort included adult patients")
    b = narrative(designNotes=[shorter, longer])

    disagreements = diff_cards.compare_narrative(a, b)

    assert disagreements[0]["onlyA"] == []
    assert disagreements[0]["onlyB"] == [shorter]


def test_proposal_relation_with_different_relation_is_a_disagreement():
    quote = "using adult ICU stays from MIMIC-IV"
    a = narrative(proposalRelation=[note("同資料集", quote, relation="支持", proposalQuote="We will use MIMIC-IV")])
    b = narrative(proposalRelation=[note("做過了", quote, relation="已有人做過", proposalQuote="We will use MIMIC-IV")])

    disagreements = diff_cards.compare_narrative(a, b)

    assert [d["field"] for d in disagreements] == ["proposalRelation"]
    assert len(disagreements[0]["onlyA"]) == 1 and len(disagreements[0]["onlyB"]) == 1


def test_narrative_field_empty_on_both_sides_is_skipped():
    assert diff_cards.compare_narrative(narrative(), narrative()) == []


def test_narrative_field_present_on_one_side_only_is_a_disagreement():
    a = narrative()
    b = narrative()
    del b["contributions"]

    disagreements = diff_cards.compare_narrative(a, b)

    assert [d["field"] for d in disagreements] == ["contributions"]
    assert disagreements[0]["detail"] == "只有一邊有這個欄位"


def test_main_writes_structured_and_narrative_disagreements(tmp_path):
    a = {"key": "k", "structured": structured(),
         "narrative": narrative(limitations=[note("單一醫院", "data came from a single hospital in Boston", 9)])}
    b = {"key": "k", "structured": structured(methods=[item("LSTM")]), "narrative": narrative()}
    (tmp_path / "a.json").write_text(json.dumps(a, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")

    code = diff_cards.main([str(tmp_path)])

    written = json.loads((tmp_path / "diff.json").read_text(encoding="utf-8"))
    assert code == 0
    assert [d["field"] for d in written["disagreements"]] == ["methods", "limitations"]


def test_article_type_must_match_exactly():
    a = structured(articleType=item("原始研究", 1))
    b = structured(articleType=item("系統性回顧", 1))

    assert [d["field"] for d in diff_cards.compare(a, b)] == ["articleType"]


def test_topics_are_not_compared():
    a = structured(topics=[item("失智症", 1)])
    b = structured(topics=[item("Dementia", 1), item("穿戴式裝置", 2)])

    assert diff_cards.compare(a, b) == []


def test_name_key_ignores_case_and_punctuation():
    assert diff_cards.name_key("MIMIC-IV") == diff_cards.name_key("mimic iv")
