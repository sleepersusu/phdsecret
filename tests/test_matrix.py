import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import matrix  # noqa: E402


def card(key, study_type, method):
    item = lambda value: {"value": value, "quote": "q", "page": 1}  # noqa: E731
    return {
        "key": key,
        "title": f"Title of {key}",
        "structured": {
            "studyType": item(study_type),
            "dataSources": [item("MIMIC-IV"), item("eICU")],
            "sampleSize": [item("45,121 stays")],
            "methods": [item(method)],
            "results": [item("AUROC 0.89")],
        },
    }


def test_writes_one_row_per_card_sorted_by_key(tmp_path):
    for key, study_type, method in [("zhang2022", "review", "—"), ("adams2021", "實證研究", "LSTM")]:
        card_dir = tmp_path / "cards" / key
        card_dir.mkdir(parents=True)
        (card_dir / "card.json").write_text(json.dumps(card(key, study_type, method), ensure_ascii=False), encoding="utf-8")

    code = matrix.main([str(tmp_path)])

    lines = (tmp_path / "matrix.md").read_text(encoding="utf-8").splitlines()
    rows = [line for line in lines if line.startswith("| [")]
    assert code == 0
    assert rows[0].startswith("| [adams2021](cards/adams2021/card.md) | 實證研究 | MIMIC-IV; eICU |")
    assert rows[1].startswith("| [zhang2022](cards/zhang2022/card.md) | review |")
