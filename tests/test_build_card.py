import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_card  # noqa: E402


def item(value, page=3):
    return {"value": value, "quote": f"we report {value}", "page": page}


def note(text, page=2):
    return {"text": text, "quote": f"evidence for {text}", "page": page}


def full_card():
    return {
        "key": "smith2023",
        "id": "10.1000/xyz",
        "title": "Sepsis Prediction with Transformers",
        "structured": {
            "studyType": item("實證研究", 1),
            "dataSources": [item("MIMIC-IV")],
            "sampleSize": [item("45,121 ICU stays")],
            "methods": [item("Transformer")],
            "results": [item("AUROC 0.89")],
        },
        "narrative": {
            "researchQuestion": [note("能否提早預測敗血症")],
            "designNotes": [],
            "findings": [note("比既有分數好")],
            "contributions": [note("公開模型")],
            "limitations": [],
            "proposalRelation": [
                {"relation": "支持", "text": "同樣用 MIMIC", "quote": "we use MIMIC-IV", "page": 3,
                 "proposalQuote": "using MIMIC-IV"}
            ],
            "custom": {},
        },
        "structure": [{"heading": "2 Methods", "page": 3, "endPage": 5, "purpose": "說明資料與模型"}],
    }


def write(card_dir, name, data):
    (card_dir / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_renders_every_claim_with_citation(tmp_path):
    write(tmp_path, "a.json", full_card())

    build_card.main([str(tmp_path)])

    md = (tmp_path / "card.md").read_text(encoding="utf-8")
    assert md.startswith("# Sepsis Prediction with Transformers")
    assert '- MIMIC-IV "we report MIMIC-IV" [smith2023, p.3]' in md
    assert '| "2 Methods" [smith2023, p.3] | 3–5 | 說明資料與模型 |' in md
    assert '"using MIMIC-IV" [proposal]' in md


def test_empty_section_says_not_mentioned(tmp_path):
    write(tmp_path, "a.json", full_card())

    build_card.main([str(tmp_path)])

    md = (tmp_path / "card.md").read_text(encoding="utf-8")
    assert "## 限制\n- 原文未提及" in md


def test_judge_resolution_replaces_field(tmp_path):
    write(tmp_path, "a.json", full_card())
    write(tmp_path, "diff.json", {"disagreements": [{"field": "results"}]})
    write(tmp_path, "judge.json", {"decisions": [
        {"field": "results", "status": "resolved", "value": [item("AUROC 0.89"), item("AUROC 0.76", 7)],
         "reason": "乙多抓到外部驗證"}
    ]})

    build_card.main([str(tmp_path)])

    card = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    assert [r["value"] for r in card["structured"]["results"]] == ["AUROC 0.89", "AUROC 0.76"]
    assert card["pending"] == []


def test_unresolved_or_unjudged_disagreement_is_pending(tmp_path):
    write(tmp_path, "a.json", full_card())
    write(tmp_path, "diff.json", {"disagreements": [{"field": "results"}, {"field": "methods"}]})
    write(tmp_path, "judge.json", {"decisions": [
        {"field": "results", "status": "unresolved", "reason": "原文兩處數字矛盾"}
    ]})

    build_card.main([str(tmp_path)])

    card = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    md = (tmp_path / "card.md").read_text(encoding="utf-8")
    assert [p["field"] for p in card["pending"]] == ["results", "methods"]
    assert "## ⚠ 待本人裁決" in md


def test_items_without_usable_evidence_are_flagged(tmp_path):
    card = full_card()
    card["narrative"]["findings"] = [{"text": "沒附引文", "quote": "", "page": 2}]
    card["structured"]["methods"] = [{"value": "LSTM", "quote": 'the "LSTM" baseline', "page": 4}]
    write(tmp_path, "a.json", card)

    build_card.main([str(tmp_path)])

    flagged = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))["missingEvidence"]
    assert flagged == ["structured.methods[0]", "narrative.findings[0]"]
