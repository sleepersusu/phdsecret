import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import library_lookup  # noqa: E402

INDEX = {"papers": {
    "10.1000/abc": {"title": "A", "primary": {"review": "old", "key": "smith2023"}, "appearances": []},
    "10.1000/def": {"title": "D", "primary": {"review": "new", "key": "d"}, "appearances": []},
    "10.1000/ghi": {"title": "G", "primary": None, "appearances": []},
}}


def test_paper_with_primary_in_other_review_is_known():
    known = library_lookup.lookup([{"key": "s23", "id": "https://doi.org/10.1000/ABC"}], INDEX, "new")

    assert known == [{"key": "s23", "id": "10.1000/abc", "source": {"review": "old", "key": "smith2023"}}]


def test_primary_in_this_review_or_missing_is_not_known():
    papers = [{"key": "d", "id": "10.1000/def"}, {"key": "g", "id": "10.1000/ghi"}, {"key": "u", "id": "id 待確認"}]

    assert library_lookup.lookup(papers, INDEX, "new") == []


def test_main_writes_known_json(tmp_path):
    review = tmp_path / "reviews" / "new"
    review.mkdir(parents=True)
    (review / "papers.json").write_text(json.dumps([{"key": "s23", "id": "10.1000/abc"}]), encoding="utf-8")
    library = tmp_path / "library"
    library.mkdir()
    (library / "index.json").write_text(json.dumps(INDEX), encoding="utf-8")

    code = library_lookup.main([str(review), "--library", str(library)])

    assert code == 0
    assert json.loads((review / "known.json").read_text(encoding="utf-8"))[0]["source"]["review"] == "old"


def test_main_without_index_writes_empty_list(tmp_path):
    review = tmp_path / "reviews" / "new"
    review.mkdir(parents=True)
    (review / "papers.json").write_text(json.dumps([{"key": "s23", "id": "10.1000/abc"}]), encoding="utf-8")

    code = library_lookup.main([str(review), "--library", str(tmp_path / "library")])

    assert code == 0
    assert json.loads((review / "known.json").read_text(encoding="utf-8")) == []


def test_main_without_papers_exits_one(tmp_path):
    assert library_lookup.main([str(tmp_path), "--library", str(tmp_path / "library")]) == 1
