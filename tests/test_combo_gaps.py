import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import combo_gaps  # noqa: E402


def item(value):
    return {"value": value, "quote": f"we use {value}", "page": 3}


def card(key, methods, sources):
    return {"key": key, "structured": {"methods": [item(m) for m in methods], "dataSources": [item(s) for s in sources]}}


CARDS = [
    card("a", ["Transformer"], ["MIMIC-IV"]),
    card("b", ["LSTM"], ["MIMIC-IV", "eICU"]),
    card("c", ["transformer"], ["eICU"]),
    card("d", ["XGBoost"], ["UK Biobank"]),
]


def test_lists_methods_with_normalized_names():
    result = combo_gaps.analyze(CARDS)

    assert result["methods"] == [
        {"name": "LSTM", "papers": ["b"]},
        {"name": "Transformer", "papers": ["a", "c"]},
        {"name": "XGBoost", "papers": ["d"]},
    ]


def test_pairs_in_the_same_card_are_used():
    used = {(u["method"], u["dataSource"]) for u in combo_gaps.analyze(CARDS)["used"]}

    assert used == {
        ("Transformer", "MIMIC-IV"), ("LSTM", "MIMIC-IV"), ("LSTM", "eICU"),
        ("Transformer", "eICU"), ("XGBoost", "UK Biobank"),
    }


def test_unused_sorted_by_paper_count_then_name():
    unused = combo_gaps.analyze(CARDS)["unused"]

    assert [(u["method"], u["dataSource"]) for u in unused] == [
        ("Transformer", "UK Biobank"),
        ("XGBoost", "eICU"),
        ("XGBoost", "MIMIC-IV"),
        ("LSTM", "UK Biobank"),
    ]
    assert unused[0]["methodPapers"] == ["a", "c"]
    assert unused[0]["dataPapers"] == ["d"]


def test_main_writes_combo_gaps_json(tmp_path):
    for c in CARDS:
        card_dir = tmp_path / "cards" / c["key"]
        card_dir.mkdir(parents=True)
        (card_dir / "card.json").write_text(json.dumps(c), encoding="utf-8")

    code = combo_gaps.main([str(tmp_path)])

    written = json.loads((tmp_path / "combo-gaps.json").read_text(encoding="utf-8"))
    assert code == 0
    assert len(written["unused"]) == 4


def test_main_without_cards_exits_one(tmp_path):
    assert combo_gaps.main([str(tmp_path)]) == 1
