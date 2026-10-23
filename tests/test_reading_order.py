import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reading_order  # noqa: E402


def card(key, article=None, study=None, conflicts=0):
    structured = {}
    if article:
        structured["articleType"] = {"value": article, "quote": "q", "page": 1}
    if study:
        structured["studyType"] = {"value": study, "quote": "q", "page": 1}
    relations = [{"relation": "衝突", "text": "t", "quote": "q", "page": 1}] * conflicts
    return {"key": key, "title": f"T {key}", "structured": structured, "narrative": {"proposalRelation": relations}}


def papers(*keys):
    return [{"key": k, "title": f"T {k}"} for k in keys]


def order(entries):
    return [e["key"] for e in entries]


def test_review_types_come_first():
    cards = {"a": card("a", article="原始研究"), "b": card("b", article="系統性回顧")}
    refs = [{"inCorpus": "a", "citedByCount": "5"}]

    assert order(reading_order.rank(papers("a", "b"), cards, refs, "已有提案", "", set())) == ["b", "a"]


def test_study_type_review_is_fallback_without_article_type():
    cards = {"a": card("a"), "b": card("b", study="review")}

    assert order(reading_order.rank(papers("a", "b"), cards, [], "已有提案", "", set())) == ["b", "a"]


def test_in_batch_citations_order_next():
    cards = {"a": card("a"), "b": card("b")}
    refs = [{"inCorpus": "b", "citedByCount": "3"}, {"inCorpus": "", "citedByCount": "9"}]

    entries = reading_order.rank(papers("a", "b"), cards, refs, "已有提案", "", set())

    assert order(entries) == ["b", "a"]
    assert entries[0]["signals"] == ["被本批 3 篇引用"]


def test_proposal_mode_uses_conflicts():
    cards = {"a": card("a"), "b": card("b", conflicts=2)}

    entries = reading_order.rank(papers("a", "b"), cards, [], "已有提案", "", set())

    assert order(entries) == ["b", "a"]
    assert entries[0]["signals"] == ["與提案衝突或已有人做過 2 項"]


def test_no_proposal_mode_uses_research_gap_citations():
    cards = {"a": card("a", conflicts=5), "b": card("b")}
    gaps = '- x "q" [b, p.3]；"q" [b, p.4]\n- y "q" [a, p.1]'

    entries = reading_order.rank(papers("a", "b"), cards, [], "無提案", gaps, set())

    assert order(entries) == ["b", "a"]
    assert entries[0]["signals"] == ["研究空白引用 2 次"]
    assert entries[1]["signals"] == ["研究空白引用 1 次"]


def test_ties_break_by_key_and_no_signal_text():
    cards = {"b": card("b"), "a": card("a")}

    entries = reading_order.rank(papers("b", "a"), cards, [], "已有提案", "", set())

    assert order(entries) == ["a", "b"]
    assert entries[0]["signals"] == ["無特殊訊號"]


def test_paper_without_card_goes_last():
    entries = reading_order.rank(papers("a", "z"), {"z": card("z")}, [], "已有提案", "", set())

    assert order(entries) == ["z", "a"]
    assert entries[1]["signals"] == ["卡片未完成"]


def test_review_signal_text():
    entries = reading_order.rank(papers("a"), {"a": card("a", article="範疇回顧")}, [], "已有提案", "", set())

    assert entries[0]["signals"] == ["回顧類"]


def test_render_links_summary_only_when_present():
    entries = reading_order.rank(papers("a", "b"), {"a": card("a"), "b": card("b")}, [], "已有提案", "", {"a"})

    md = reading_order.render(entries)

    assert "| 1 | T a | 無特殊訊號 | [摘要](cards/a/summary.md)・[卡片](cards/a/card.md) |" in md
    assert "| 2 | T b | 無特殊訊號 | [卡片](cards/b/card.md) |" in md


def test_main_reads_mode_and_tolerates_missing_research_gaps(tmp_path):
    (tmp_path / "papers.json").write_text(json.dumps(papers("a"), ensure_ascii=False), encoding="utf-8")
    (tmp_path / "protocol.md").write_text("## 模式\n\n- 模式：無提案\n", encoding="utf-8")
    card_dir = tmp_path / "cards" / "a"
    card_dir.mkdir(parents=True)
    (card_dir / "card.json").write_text(json.dumps(card("a"), ensure_ascii=False), encoding="utf-8")

    code = reading_order.main([str(tmp_path)])

    md = (tmp_path / "reading-order.md").read_text(encoding="utf-8")
    assert code == 0
    assert md.startswith("# 建議閱讀順序")
    assert "| 1 | T a | 無特殊訊號 |" in md


def test_main_without_papers_exits_one(tmp_path):
    assert reading_order.main([str(tmp_path)]) == 1
