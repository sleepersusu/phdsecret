import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import library_build  # noqa: E402
import merge_refs  # noqa: E402


def card(key):
    return {"key": key, "title": f"T {key}", "structured": {
        "articleType": {"value": "原始研究", "quote": "q", "page": 1},
        "methods": [{"value": "LSTM", "quote": "q", "page": 2}]}}


def make_review(root, name, papers, updated="2026-10-01T00:00:00", cards=(), paper_tags=None, refs=None):
    d = root / "reviews" / name
    (d / "cards").mkdir(parents=True)
    (d / "papers.json").write_text(json.dumps(papers, ensure_ascii=False), encoding="utf-8")
    (d / "state.json").write_text(json.dumps({"stage": "stop2", "note": "", "updatedAt": updated}), encoding="utf-8")
    for key in cards:
        (d / "cards" / key).mkdir()
        (d / "cards" / key / "card.json").write_text(json.dumps(card(key), ensure_ascii=False), encoding="utf-8")
    if paper_tags is not None:
        (d / "paper-tags.json").write_text(json.dumps(paper_tags, ensure_ascii=False), encoding="utf-8")
    if refs is not None:
        with open(d / "references.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=merge_refs.CSV_FIELDS)
            writer.writeheader()
            for row in refs:
                writer.writerow({field: row.get(field, "") for field in merge_refs.CSV_FIELDS})


def build(tmp_path):
    reviews = library_build.load_reviews(tmp_path / "reviews")
    return reviews, library_build.build_index(reviews)


def test_same_doi_in_two_reviews_is_one_paper(tmp_path):
    make_review(tmp_path, "r1", [{"key": "a", "id": "https://doi.org/10.1000/ABC", "title": "A"}], cards=["a"])
    make_review(tmp_path, "r2", [{"key": "x", "id": "10.1000/abc", "title": "A"}], cards=["x"])

    _, index = build(tmp_path)

    assert list(index["papers"]) == ["10.1000/abc"]
    assert [a["review"] for a in index["papers"]["10.1000/abc"]["appearances"]] == ["r1", "r2"]


def test_primary_is_most_recently_updated_review(tmp_path):
    make_review(tmp_path, "r1", [{"key": "a", "id": "10.1000/abc", "title": "A"}], "2026-10-01T00:00:00", ["a"])
    make_review(tmp_path, "r2", [{"key": "x", "id": "10.1000/abc", "title": "A"}], "2026-10-05T00:00:00", ["x"])

    _, index = build(tmp_path)

    assert index["papers"]["10.1000/abc"]["primary"] == {"review": "r2", "key": "x"}


def test_primary_tie_breaks_by_review_name(tmp_path):
    make_review(tmp_path, "r2", [{"key": "x", "id": "10.1000/abc", "title": "A"}], cards=["x"])
    make_review(tmp_path, "r1", [{"key": "a", "id": "10.1000/abc", "title": "A"}], cards=["a"])

    _, index = build(tmp_path)

    assert index["papers"]["10.1000/abc"]["primary"] == {"review": "r1", "key": "a"}


def test_paper_without_card_has_no_primary_and_no_matrix_row(tmp_path):
    make_review(tmp_path, "r1", [{"key": "a", "id": "10.1000/abc", "title": "A"}])

    reviews, index = build(tmp_path)

    assert index["papers"]["10.1000/abc"]["primary"] is None
    assert "| [a]" not in library_build.render_matrix(index, reviews)


def test_unconfirmed_id_is_unindexed(tmp_path):
    make_review(tmp_path, "r1", [{"key": "a", "id": "id 待確認", "title": "A"}], cards=["a"])

    _, index = build(tmp_path)

    assert index["papers"] == {}
    assert index["unindexed"] == [{"review": "r1", "key": "a", "reason": "id 待確認"}]


def test_index_carries_article_type_and_tags(tmp_path):
    tags = {"a": {"articleType": "系統性回顧", "tags": ["失智症"], "raw": [], "unmapped": []}}
    make_review(tmp_path, "r1", [{"key": "a", "id": "10.1000/abc", "title": "A"}], cards=["a"], paper_tags=tags)
    make_review(tmp_path, "r2", [{"key": "b", "id": "10.1000/def", "title": "B"}], cards=["b"])

    _, index = build(tmp_path)

    assert index["papers"]["10.1000/abc"]["articleType"] == "系統性回顧"
    assert index["papers"]["10.1000/abc"]["tags"] == ["失智症"]
    assert index["papers"]["10.1000/def"]["articleType"] == "原始研究"
    assert index["papers"]["10.1000/def"]["tags"] == []


def test_matrix_links_primary_card_and_lists_reviews(tmp_path):
    tags = {"x": {"articleType": "原始研究", "tags": ["失智症"], "raw": [], "unmapped": []}}
    make_review(tmp_path, "r1", [{"key": "a", "id": "10.1000/abc", "title": "A"}], "2026-10-01T00:00:00", ["a"])
    make_review(tmp_path, "r2", [{"key": "x", "id": "10.1000/abc", "title": "A"}], "2026-10-05T00:00:00", ["x"], tags)

    reviews, index = build(tmp_path)
    md = library_build.render_matrix(index, reviews)

    assert "| 標籤 | 批次 |" in md.splitlines()[0]
    row = [line for line in md.splitlines() if line.startswith("| [x]")][0]
    assert row.startswith("| [x](../reviews/r2/cards/x/card.md) |")
    assert row.endswith("| 失智症 | r1; r2 |")


def test_references_merge_across_reviews_and_mark_corpus(tmp_path):
    make_review(tmp_path, "r1", [{"key": "a", "id": "10.1000/abc", "title": "A"}], cards=["a"], refs=[
        {"title": "Shared ref", "year": "2020", "doi": "10.9/zzz", "citedBy": "a", "raw": "Shared ref 2020"},
        {"title": "A", "year": "2019", "doi": "10.1000/abc", "citedBy": "a", "raw": "A 2019"},
    ])
    make_review(tmp_path, "r2", [{"key": "x", "id": "10.1000/def", "title": "X"}], cards=["x"], refs=[
        {"title": "Shared ref", "year": "2020", "doi": "https://doi.org/10.9/ZZZ", "citedBy": "x", "raw": "Shared ref 2020"},
    ])

    reviews, index = build(tmp_path)
    rows = library_build.build_references(index, reviews)

    shared = [r for r in rows if r["doi"] == "10.9/zzz"][0]
    assert shared["citedBy"] == "r1/a;r2/x"
    assert shared["citedByCount"] == 2
    assert [r for r in rows if r["doi"] == "10.1000/abc"][0]["inCorpus"] == "10.1000/abc"


def test_main_writes_outputs_and_never_touches_tags_json(tmp_path):
    make_review(tmp_path, "r1", [{"key": "a", "id": "10.1000/abc", "title": "A"}], cards=["a"])
    out = tmp_path / "library"
    out.mkdir()
    (out / "tags.json").write_text('{"tags": {"失智症": {"synonyms": [], "source": "user"}}}', encoding="utf-8")
    before = (out / "tags.json").read_bytes()

    code = library_build.main(["--reviews", str(tmp_path / "reviews"), "--out", str(out)])

    assert code == 0
    assert (out / "tags.json").read_bytes() == before
    assert sorted(p.name for p in out.iterdir()) == ["index.json", "matrix.md", "references.csv", "tags.json"]


def test_main_does_not_create_tags_json(tmp_path):
    make_review(tmp_path, "r1", [{"key": "a", "id": "10.1000/abc", "title": "A"}], cards=["a"])
    out = tmp_path / "library"

    library_build.main(["--reviews", str(tmp_path / "reviews"), "--out", str(out)])

    assert not (out / "tags.json").exists()


def test_main_without_reviews_exits_one(tmp_path):
    (tmp_path / "reviews").mkdir()

    assert library_build.main(["--reviews", str(tmp_path / "reviews"), "--out", str(tmp_path / "library")]) == 1
