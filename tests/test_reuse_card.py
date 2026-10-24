import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reuse_card  # noqa: E402

SOURCE = {
    "key": "smith2023", "id": "10.1000/abc", "title": "A",
    "structured": {"articleType": {"value": "原始研究", "quote": "q", "page": 1}},
    "narrative": {"findings": [{"text": "t", "quote": "q", "page": 3, "source": "audit"}],
                  "proposalRelation": [{"relation": "支持", "text": "t", "quote": "q", "page": 3}]},
    "pending": [{"field": "results", "reason": "x"}], "missingEvidence": ["narrative.findings[0]"], "auditAdded": 1,
}


def test_reuse_rewrites_key_and_drops_batch_state():
    card = reuse_card.reuse(SOURCE, "s23", clear_relation=False)

    assert card["key"] == "s23"
    assert not {"pending", "missingEvidence", "auditAdded"} & card.keys()
    assert card["narrative"]["findings"][0]["source"] == "audit"
    assert card["narrative"]["proposalRelation"] == SOURCE["narrative"]["proposalRelation"]


def test_clear_relation_empties_proposal_relation_without_touching_source():
    card = reuse_card.reuse(SOURCE, "s23", clear_relation=True)

    assert card["narrative"]["proposalRelation"] == []
    assert len(SOURCE["narrative"]["proposalRelation"]) == 1


def make_source(tmp_path, with_summary=True, source=None):
    source_dir = tmp_path / "reviews" / "old" / "cards" / "smith2023"
    source_dir.mkdir(parents=True)
    if source is None:
        source = {**SOURCE, "pending": []}
    (source_dir / "card.json").write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    if with_summary:
        (source_dir / "summary.md").write_text("摘要 [findings#1]。", encoding="utf-8")
    review = tmp_path / "reviews" / "new"
    review.mkdir(parents=True)
    return source_dir, review


def test_main_writes_a_json_and_copies_summary(tmp_path):
    source_dir, review = make_source(tmp_path)
    before = (source_dir / "card.json").read_bytes()

    code = reuse_card.main([str(review), "s23", "--source", "old/smith2023", "--clear-relation"])

    a = json.loads((review / "cards" / "s23" / "a.json").read_text(encoding="utf-8"))
    assert code == 0
    assert a["key"] == "s23" and a["narrative"]["proposalRelation"] == []
    assert (review / "cards" / "s23" / "summary.md").read_text(encoding="utf-8") == "摘要 [findings#1]。"
    assert (source_dir / "card.json").read_bytes() == before


def test_main_without_source_summary_writes_no_summary(tmp_path):
    _, review = make_source(tmp_path, with_summary=False)

    reuse_card.main([str(review), "s23", "--source", "old/smith2023"])

    assert not (review / "cards" / "s23" / "summary.md").exists()


def test_main_with_missing_source_exits_one(tmp_path):
    _, review = make_source(tmp_path)

    assert reuse_card.main([str(review), "s23", "--source", "old/nope"]) == 1


def test_main_with_pending_source_exits_three_and_writes_nothing(tmp_path, capsys):
    _, review = make_source(tmp_path, source=SOURCE)

    code = reuse_card.main([str(review), "s23", "--source", "old/smith2023"])

    assert code == 3
    assert "results" in capsys.readouterr().err
    assert not (review / "cards" / "s23" / "a.json").exists()


def test_main_copies_only_section_reasons_from_source_audit(tmp_path):
    source_dir, review = make_source(tmp_path)
    audit = {"additions": [{"field": "findings", "text": "t"}], "sectionReasons": [{"section": "Methods", "reason": "只有方法學"}]}
    (source_dir / "audit.json").write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")

    reuse_card.main([str(review), "s23", "--source", "old/smith2023"])

    written = json.loads((review / "cards" / "s23" / "audit.json").read_text(encoding="utf-8"))
    assert written == {"sectionReasons": audit["sectionReasons"]}


def test_main_without_source_audit_writes_no_audit(tmp_path):
    _, review = make_source(tmp_path)

    reuse_card.main([str(review), "s23", "--source", "old/smith2023"])

    assert not (review / "cards" / "s23" / "audit.json").exists()
