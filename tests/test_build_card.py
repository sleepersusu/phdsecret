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


def test_judge_resolution_of_narrative_field_writes_narrative(tmp_path):
    write(tmp_path, "a.json", full_card())
    write(tmp_path, "diff.json", {"disagreements": [{"field": "limitations", "kind": "narrative"}]})
    write(tmp_path, "judge.json", {"decisions": [
        {"field": "limitations", "status": "resolved", "value": [note("只在單一醫院", 9)], "reason": "乙抓到的限制屬實"}
    ]})

    build_card.main([str(tmp_path)])

    card = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    assert [n["text"] for n in card["narrative"]["limitations"]] == ["只在單一醫院"]
    assert "limitations" not in card["structured"]
    assert card["pending"] == []


def test_audit_additions_are_appended_with_source_and_marked(tmp_path):
    write(tmp_path, "a.json", full_card())
    write(tmp_path, "audit.json", {"additions": {
        "limitations": [note("只在單一醫院", 9)],
        "methods": [item("XGBoost", 5)],
        "custom.Source of data": [note("回溯性資料", 3)],
    }, "sectionReasons": []})

    build_card.main([str(tmp_path)])

    card = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    md = (tmp_path / "card.md").read_text(encoding="utf-8")
    assert card["narrative"]["limitations"][0]["source"] == "audit"
    assert [m["value"] for m in card["structured"]["methods"]] == ["Transformer", "XGBoost"]
    assert card["narrative"]["custom"]["Source of data"][0]["source"] == "audit"
    assert card["auditAdded"] == 3
    assert '- 只在單一醫院 "evidence for 只在單一醫院" [smith2023, p.9]（補漏）' in md
    assert '- XGBoost "we report XGBoost" [smith2023, p.5]（補漏）' in md
    assert '- Transformer "we report Transformer" [smith2023, p.3]\n' in md


def test_audit_addition_to_unknown_field_is_pending(tmp_path):
    write(tmp_path, "a.json", full_card())
    write(tmp_path, "audit.json", {"additions": {"funding": [note("NIH 資助", 12)]}})

    build_card.main([str(tmp_path)])

    card = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    assert card["auditAdded"] == 0
    assert [p["field"] for p in card["pending"]] == ["funding"]


def test_audit_addition_to_existing_study_type_is_pending(tmp_path):
    write(tmp_path, "a.json", full_card())
    write(tmp_path, "audit.json", {"additions": {"studyType": [item("review", 1)]}})

    build_card.main([str(tmp_path)])

    card = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    assert card["structured"]["studyType"]["value"] == "實證研究"
    assert [p["field"] for p in card["pending"]] == ["studyType"]


def test_audit_additions_are_checked_for_evidence(tmp_path):
    write(tmp_path, "a.json", full_card())
    write(tmp_path, "audit.json", {"additions": {"limitations": [{"text": "沒引文", "quote": "", "page": 9}]}})

    build_card.main([str(tmp_path)])

    card = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    assert card["missingEvidence"] == ["narrative.limitations[0]"]


def test_without_audit_file_audit_added_is_zero(tmp_path):
    write(tmp_path, "a.json", full_card())

    build_card.main([str(tmp_path)])

    card = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    md = (tmp_path / "card.md").read_text(encoding="utf-8")
    assert card["auditAdded"] == 0
    assert "（補漏）" not in md


def test_topics_are_union_of_both_extractors(tmp_path):
    card = full_card()
    card["structured"]["topics"] = [item("失智症", 1), item("Wearable devices", 2)]
    write(tmp_path, "a.json", card)
    write(tmp_path, "b.json", {"key": "smith2023", "structured": {
        "topics": [item("wearable-devices", 2), item("介入研究", 3)]}})

    build_card.main([str(tmp_path)])

    built = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    assert [t["value"] for t in built["structured"]["topics"]] == ["失智症", "Wearable devices", "介入研究"]


def test_topics_without_b_json_keep_a_only(tmp_path):
    card = full_card()
    card["structured"]["topics"] = [item("失智症", 1)]
    write(tmp_path, "a.json", card)

    build_card.main([str(tmp_path)])

    built = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    assert [t["value"] for t in built["structured"]["topics"]] == ["失智症"]


def test_renders_article_type_and_topics(tmp_path):
    card = full_card()
    card["structured"]["articleType"] = item("原始研究", 1)
    card["structured"]["topics"] = [item("失智症", 1)]
    write(tmp_path, "a.json", card)

    build_card.main([str(tmp_path)])

    md = (tmp_path / "card.md").read_text(encoding="utf-8")
    assert '- 文章類型：原始研究 "we report 原始研究" [smith2023, p.1]' in md
    assert '## 領域標籤\n- 失智症 "we report 失智症" [smith2023, p.1]' in md


def test_missing_article_type_says_not_mentioned(tmp_path):
    write(tmp_path, "a.json", full_card())

    build_card.main([str(tmp_path)])

    md = (tmp_path / "card.md").read_text(encoding="utf-8")
    assert "- 文章類型：原文未提及" in md
    assert "## 領域標籤\n- 原文未提及" in md


def test_topic_without_evidence_is_flagged(tmp_path):
    card = full_card()
    card["structured"]["topics"] = [{"value": "失智症", "quote": "", "page": 1}]
    write(tmp_path, "a.json", card)

    build_card.main([str(tmp_path)])

    built = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    assert built["missingEvidence"] == ["structured.topics[0]"]


def test_audit_addition_to_existing_article_type_is_pending(tmp_path):
    card = full_card()
    card["structured"]["articleType"] = item("原始研究", 1)
    write(tmp_path, "a.json", card)
    write(tmp_path, "audit.json", {"additions": {"articleType": [item("系統性回顧", 1)]}})

    build_card.main([str(tmp_path)])

    built = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    assert built["structured"]["articleType"]["value"] == "原始研究"
    assert [p["field"] for p in built["pending"]] == ["articleType"]


def test_judge_single_item_list_for_article_type_is_unwrapped(tmp_path):
    card = full_card()
    card["structured"]["articleType"] = item("原始研究", 1)
    write(tmp_path, "a.json", card)
    write(tmp_path, "diff.json", {"disagreements": [{"field": "articleType"}]})
    write(tmp_path, "judge.json", {"decisions": [
        {"field": "articleType", "status": "resolved", "value": [item("系統性回顧", 1)], "reason": "乙正確"}
    ]})

    build_card.main([str(tmp_path)])

    built = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    assert built["structured"]["articleType"]["value"] == "系統性回顧"
    assert built["pending"] == []
    assert "- 文章類型：系統性回顧" in (tmp_path / "card.md").read_text(encoding="utf-8")


def test_judge_multi_item_list_for_single_value_field_is_pending(tmp_path):
    card = full_card()
    card["structured"]["articleType"] = item("原始研究", 1)
    write(tmp_path, "a.json", card)
    write(tmp_path, "diff.json", {"disagreements": [{"field": "articleType"}]})
    write(tmp_path, "judge.json", {"decisions": [
        {"field": "articleType", "status": "resolved",
         "value": [item("系統性回顧", 1), item("統合分析", 1)], "reason": "兩者皆是"}
    ]})

    build_card.main([str(tmp_path)])

    built = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    assert built["structured"]["articleType"]["value"] == "原始研究"
    assert built["pending"] == [{"field": "articleType", "reason": "judge 對單值欄位給了 2 個值，請本人確認"}]


def test_judge_empty_list_for_single_value_field_is_pending(tmp_path):
    card = full_card()
    card["structured"]["articleType"] = item("原始研究", 1)
    write(tmp_path, "a.json", card)
    write(tmp_path, "diff.json", {"disagreements": [{"field": "articleType"}]})
    write(tmp_path, "judge.json", {"decisions": [
        {"field": "articleType", "status": "resolved", "value": [], "reason": "x"}
    ]})

    build_card.main([str(tmp_path)])

    built = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    assert built["pending"] == [{"field": "articleType", "reason": "judge 對單值欄位給了 0 個值，請本人確認"}]


def test_topics_with_null_structured_in_b_json_do_not_raise(tmp_path):
    card = full_card()
    card["structured"]["topics"] = [item("失智症", 1)]
    write(tmp_path, "a.json", card)
    write(tmp_path, "b.json", {"key": "smith2023", "structured": None})

    build_card.main([str(tmp_path)])

    built = json.loads((tmp_path / "card.json").read_text(encoding="utf-8"))
    assert [t["value"] for t in built["structured"]["topics"]] == ["失智症"]
