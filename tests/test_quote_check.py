import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import quote_check  # noqa: E402

PAPER = (
    "=== p.1 ===\nWe propose a transformer for early sepsis predic-\ntion in the ICU.\n"
    "=== p.2 ===\nThe model achieved an AUROC of 0.89 on the internal test set.\n"
)


def make_review(tmp_path):
    texts = tmp_path / "text"
    texts.mkdir()
    (texts / "smith2023.txt").write_text(PAPER, encoding="utf-8")
    (texts / "proposal.txt").write_text("We aim to predict sepsis six hours earlier.\n", encoding="utf-8")
    return tmp_path


def test_finds_citations_with_straight_and_curly_quotes():
    markdown = (
        '- 結果 "achieved an AUROC of 0.89" [smith2023, p.2]\n'
        "- 目標 “predict sepsis six hours earlier” [proposal]\n"
    )

    found = quote_check.find_citations(markdown)

    assert found == [
        (1, "achieved an AUROC of 0.89", "smith2023", 2),
        (2, "predict sepsis six hours earlier", "proposal", None),
    ]


def test_pandoc_citekey_is_not_an_evidence_citation():
    assert quote_check.find_citations('the "Sepsis-3" [@singer2016] definition') == []


def test_require_evidence_flags_citekey_lines_without_evidence(tmp_path, capsys):
    review = make_review(tmp_path)
    draft = tmp_path / "draft.md"
    draft.write_text(
        'AUROC reached 0.89 [@smith2023].<!-- "achieved an AUROC of 0.89" [smith2023, p.2] -->\n'
        "Transformers dominate the field [@smith2023].\n",
        encoding="utf-8",
    )

    code = quote_check.main([str(review), str(draft), "--require-evidence"])

    out = capsys.readouterr().out
    assert code == 1
    assert "draft.md:2" in out
    assert "沒有證據" in out


def test_quote_on_stated_page_passes(tmp_path):
    review = make_review(tmp_path)

    result = quote_check.check(review, "smith2023", 2, "achieved an AUROC of 0.89")

    assert result["ok"] is True
    assert result["mode"] == "strict"


def test_quote_on_another_page_fails_and_says_where(tmp_path):
    review = make_review(tmp_path)

    result = quote_check.check(review, "smith2023", 1, "achieved an AUROC of 0.89")

    assert result["ok"] is False
    assert result["foundOn"] == [2]


def test_hyphenation_difference_passes_loosely(tmp_path):
    review = make_review(tmp_path)

    result = quote_check.check(review, "smith2023", 1, "early sepsis pre-diction in the ICU")

    assert result["ok"] is True
    assert result["mode"] == "loose"


def test_unknown_paper_fails(tmp_path):
    review = make_review(tmp_path)

    result = quote_check.check(review, "nobody2020", 1, "anything at all here")

    assert result["ok"] is False
    assert "nobody2020" in result["reason"]


def test_proposal_quote_checks_whole_text(tmp_path):
    review = make_review(tmp_path)

    assert quote_check.check(review, "proposal", None, "predict sepsis six hours earlier")["ok"] is True


def test_main_reports_failures_and_exit_code(tmp_path, capsys):
    review = make_review(tmp_path)
    card = tmp_path / "card.md"
    card.write_text(
        '- "achieved an AUROC of 0.89" [smith2023, p.2]\n'
        '- "achieved an AUROC of 0.95" [smith2023, p.2]\n',
        encoding="utf-8",
    )

    code = quote_check.main([str(review), str(card)])

    out = capsys.readouterr().out
    assert code == 1
    assert "checked 2, failed 1" in out
    assert "card.md:2" in out


def test_main_passes_when_all_quotes_found(tmp_path, capsys):
    review = make_review(tmp_path)
    card = tmp_path / "card.md"
    card.write_text('- "achieved an AUROC of 0.89" [smith2023, p.2]\n', encoding="utf-8")

    assert quote_check.main([str(review), str(card)]) == 0
