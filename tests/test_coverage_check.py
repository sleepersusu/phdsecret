import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import coverage_check  # noqa: E402


def item(value, page):
    return {"value": value, "quote": f"we report {value}", "page": page}


def note(text, page):
    return {"text": text, "quote": f"evidence for {text}", "page": page}


def section(heading, page, end):
    return {"heading": heading, "page": page, "endPage": end, "purpose": "..."}


def card(structure, **narrative):
    return {
        "key": "smith2023",
        "structured": {"studyType": item("實證研究", 1), "methods": [item("Transformer", 4)]},
        "narrative": {"findings": [], "custom": {}, **narrative},
        "structure": structure,
    }


def write(card_dir, name, data):
    (card_dir / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_counts_items_whose_page_falls_in_section_range():
    result = coverage_check.check(card([section("1 Intro", 1, 2), section("2 Methods", 3, 5)]), {})

    assert [s["items"] for s in result["sections"]] == [1, 1]
    assert result["uncovered"] == []


def test_section_without_items_or_reason_is_uncovered():
    structure = [section("1 Intro", 1, 2), section("2 Methods", 3, 5), section("5 Discussion", 9, 11)]

    result = coverage_check.check(card(structure), {})

    assert result["uncovered"] == ["5 Discussion"]


def test_custom_and_narrative_items_count():
    structure = [section("4 Results", 6, 8), section("5 Discussion", 9, 11)]
    c = card(structure, findings=[note("比較好", 7)], custom={"Source of data": [note("回溯", 10)]})

    result = coverage_check.check(c, {})

    assert [s["items"] for s in result["sections"]] == [1, 1]


def test_overlapping_ranges_count_for_both_sections():
    structure = [section("2 Methods", 3, 5), section("2.3 Model", 4, 4)]

    result = coverage_check.check(card(structure), {})

    assert [s["items"] for s in result["sections"]] == [1, 1]


def test_reason_from_audit_covers_empty_section():
    structure = [section("2 Methods", 3, 5), section("6 Data access", 12, 12)]
    audit = {"sectionReasons": [{"heading": "6 Data access", "reason": "只說明資料取得流程"}]}

    result = coverage_check.check(card(structure), audit)

    assert result["uncovered"] == []
    assert result["sections"][1]["reason"] == "只說明資料取得流程"


def test_section_without_end_page_uses_start_page():
    result = coverage_check.check(card([{"heading": "2 Methods", "page": 4}]), {})

    assert result["sections"][0]["items"] == 1


def test_main_exits_zero_and_writes_coverage_when_all_covered(tmp_path):
    write(tmp_path, "card.json", card([section("2 Methods", 3, 5)]))

    code = coverage_check.main([str(tmp_path)])

    written = json.loads((tmp_path / "coverage.json").read_text(encoding="utf-8"))
    assert code == 0
    assert written["uncovered"] == []


def test_main_exits_one_when_a_section_is_uncovered(tmp_path):
    write(tmp_path, "card.json", card([section("2 Methods", 3, 5), section("5 Discussion", 9, 11)]))

    assert coverage_check.main([str(tmp_path)]) == 1


def test_main_reads_audit_reasons(tmp_path):
    write(tmp_path, "card.json", card([section("2 Methods", 3, 5), section("6 Data access", 12, 12)]))
    write(tmp_path, "audit.json", {"sectionReasons": [{"heading": "6 Data access", "reason": "只說明取得流程"}]})

    assert coverage_check.main([str(tmp_path)]) == 0


def test_main_exits_one_without_structure(tmp_path):
    write(tmp_path, "card.json", card([]))

    assert coverage_check.main([str(tmp_path)]) == 1
