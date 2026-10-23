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
