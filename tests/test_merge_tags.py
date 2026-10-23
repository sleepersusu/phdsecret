import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import merge_tags  # noqa: E402

LIBRARY = {"tags": {
    "失智症": {"synonyms": ["Dementia"], "source": "agent"},
    "認知障礙": {"synonyms": ["cognitive impairment"], "source": "user"},
}}


def test_new_category_is_created_with_raw_as_synonym():
    tags, accepted, rejected = merge_tags.merge(LIBRARY, [
        {"raw": "Alzheimer's disease", "canonical": "阿茲海默症", "new": True}])

    assert tags["tags"]["阿茲海默症"] == {"synonyms": ["Alzheimer's disease"], "source": "agent"}
    assert len(accepted) == 1 and rejected == []


def test_new_category_named_like_raw_has_no_synonym():
    tags, _, _ = merge_tags.merge(LIBRARY, [{"raw": "穿戴式裝置", "canonical": "穿戴式裝置", "new": True}])

    assert tags["tags"]["穿戴式裝置"]["synonyms"] == []


def test_synonym_is_added_to_agent_category():
    tags, _, _ = merge_tags.merge(LIBRARY, [{"raw": "失智", "canonical": "失智症", "new": False}])

    assert tags["tags"]["失智症"]["synonyms"] == ["Dementia", "失智"]


def test_raw_already_in_dictionary_is_rejected_case_insensitively():
    _, accepted, rejected = merge_tags.merge(LIBRARY, [{"raw": "dementia", "canonical": "失智症", "new": False}])

    assert accepted == []
    assert rejected[0]["rejected"] == "這個寫法已在字典裡"


def test_new_with_existing_category_name_is_rejected():
    _, _, rejected = merge_tags.merge(LIBRARY, [{"raw": "dementia syndrome", "canonical": "失智症", "new": True}])

    assert rejected[0]["rejected"] == "標成新類別，但類別名已在字典裡"


def test_existing_category_that_does_not_exist_is_rejected():
    _, _, rejected = merge_tags.merge(LIBRARY, [{"raw": "PD", "canonical": "帕金森氏症", "new": False}])

    assert rejected[0]["rejected"] == "標成歸入既有類別，但字典沒有這個類別"


def test_user_category_is_not_extended_by_agent():
    tags, _, rejected = merge_tags.merge(LIBRARY, [{"raw": "MCI", "canonical": "認知障礙", "new": False}])

    assert rejected[0]["rejected"] == "本人管理的類別，不由 agent 擴充"
    assert tags["tags"]["認知障礙"]["synonyms"] == ["cognitive impairment"]


def test_input_library_is_not_mutated():
    before = json.dumps(LIBRARY, ensure_ascii=False, sort_keys=True)

    merge_tags.merge(LIBRARY, [{"raw": "失智", "canonical": "失智症", "new": False}])

    assert json.dumps(LIBRARY, ensure_ascii=False, sort_keys=True) == before


def test_main_creates_library_and_writes_report(tmp_path):
    review = tmp_path / "reviews" / "r1"
    review.mkdir(parents=True)
    (review / "tag-proposals.json").write_text(json.dumps({"proposals": [
        {"raw": "Dementia", "canonical": "失智症", "new": True},
        {"raw": "dementia", "canonical": "失智症", "new": False},
    ]}, ensure_ascii=False), encoding="utf-8")
    library = tmp_path / "library"

    code = merge_tags.main([str(review), "--library", str(library)])

    tags = json.loads((library / "tags.json").read_text(encoding="utf-8"))
    report = json.loads((review / "tag-merge-report.json").read_text(encoding="utf-8"))
    assert code == 0
    assert tags["tags"]["失智症"]["synonyms"] == ["Dementia"]
    assert len(report["accepted"]) == 1 and len(report["rejected"]) == 1


def test_main_without_proposals_exits_one(tmp_path):
    assert merge_tags.main([str(tmp_path), "--library", str(tmp_path / "library")]) == 1


def test_entry_without_source_is_not_extended_and_gets_no_source():
    library = {"tags": {"舊類別": {"synonyms": ["a"]}}}

    tags, accepted, rejected = merge_tags.merge(library, [{"raw": "b", "canonical": "舊類別", "new": False}])

    assert rejected[0]["rejected"] == "本人管理的類別，不由 agent 擴充"
    assert tags["tags"]["舊類別"] == {"synonyms": ["a"]}


def test_entry_with_unknown_source_is_not_extended():
    library = {"tags": {"手動類別": {"synonyms": ["a"], "source": "manual"}}}

    _, accepted, rejected = merge_tags.merge(library, [{"raw": "b", "canonical": "手動類別", "new": False}])

    assert accepted == []
    assert rejected[0]["rejected"] == "本人管理的類別，不由 agent 擴充"


def test_extra_fields_on_existing_entries_are_preserved():
    library = {"tags": {"失智症": {"synonyms": ["Dementia"], "source": "agent", "note": "本人備註"}}}

    tags, _, _ = merge_tags.merge(library, [{"raw": "失智", "canonical": "失智症", "new": False}])

    assert tags["tags"]["失智症"] == {"synonyms": ["Dementia", "失智"], "source": "agent", "note": "本人備註"}


def test_new_flag_must_be_literal_true():
    tags, accepted, rejected = merge_tags.merge(LIBRARY, [
        {"raw": "Alzheimer's disease", "canonical": "阿茲海默症", "new": "yes"}])

    assert accepted == []
    assert rejected[0]["rejected"] == "標成歸入既有類別，但字典沒有這個類別"
    assert "阿茲海默症" not in tags["tags"]


def test_main_with_only_rejected_proposals_leaves_library_untouched(tmp_path):
    review = tmp_path / "reviews" / "r1"
    review.mkdir(parents=True)
    (review / "tag-proposals.json").write_text(json.dumps({"proposals": [
        {"raw": "PD", "canonical": "帕金森氏症", "new": False},
    ]}, ensure_ascii=False), encoding="utf-8")
    library = tmp_path / "library"
    library.mkdir()
    original = '{"tags": {"失智症": {"synonyms": ["Dementia"], "source": "agent", "note": "原樣"}}}'
    (library / "tags.json").write_bytes(original.encode("utf-8"))

    code = merge_tags.main([str(review), "--library", str(library)])

    assert code == 0
    assert (library / "tags.json").read_bytes() == original.encode("utf-8")
    report = json.loads((review / "tag-merge-report.json").read_text(encoding="utf-8"))
    assert len(report["rejected"]) == 1


def test_main_leaves_no_temp_file_in_library(tmp_path):
    review = tmp_path / "reviews" / "r1"
    review.mkdir(parents=True)
    (review / "tag-proposals.json").write_text(json.dumps({"proposals": [
        {"raw": "Dementia", "canonical": "失智症", "new": True},
    ]}, ensure_ascii=False), encoding="utf-8")
    library = tmp_path / "library"

    merge_tags.main([str(review), "--library", str(library)])

    assert sorted(p.name for p in library.iterdir()) == ["tags.json"]
