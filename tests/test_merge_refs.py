import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import merge_refs  # noqa: E402

SEYMOUR = "Seymour CW, et al. Assessment of clinical criteria for sepsis. JAMA. 2016;315(8):762-774."
VASWANI = "Vaswani A, et al. Attention is all you need. NeurIPS 2017."
RAJKOMAR = "Rajkomar A, et al. Scalable and accurate deep learning with electronic health records. npj Digit Med. 2018."


def ref(raw, title, year, doi=None, page=9, author="X"):
    return {"raw": raw, "page": page, "title": title, "firstAuthor": author, "year": year, "doi": doi}


def make_review(tmp_path, refs_by_key, papers=None, counts=None):
    (tmp_path / "text").mkdir()
    (tmp_path / "refs").mkdir()
    for key, refs in refs_by_key.items():
        page_text = "\n".join(r["raw"] for r in refs)
        (tmp_path / "text" / f"{key}.txt").write_text(f"=== p.9 ===\nReferences\n{page_text}\n", encoding="utf-8")
        (tmp_path / "refs" / f"{key}.json").write_text(json.dumps({"key": key, "references": refs}), encoding="utf-8")
    for key, count in (counts or {}).items():
        (tmp_path / "refs" / f"{key}.count.json").write_text(json.dumps({"count": count}), encoding="utf-8")
    (tmp_path / "papers.json").write_text(json.dumps(papers or []), encoding="utf-8")
    return tmp_path


def read_rows(review):
    with open(review / "references.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_report(review):
    return json.loads((review / "refs-report.json").read_text(encoding="utf-8"))


def test_same_doi_cited_by_two_papers_becomes_one_row(tmp_path):
    review = make_review(tmp_path, {
        "a": [ref(SEYMOUR, "Assessment of clinical criteria for sepsis", "2016", "10.1001/jama.2016.0288")],
        "b": [ref(SEYMOUR, "Assessment of Clinical Criteria for Sepsis", "2016", "https://doi.org/10.1001/JAMA.2016.0288")],
    })

    merge_refs.main([str(review)])

    rows = read_rows(review)
    assert len(rows) == 1
    assert rows[0]["citedByCount"] == "2"
    assert rows[0]["citedBy"] == "a;b"


def test_title_and_year_match_when_one_side_lacks_doi(tmp_path):
    review = make_review(tmp_path, {
        "a": [ref(SEYMOUR, "Assessment of clinical criteria for sepsis", "2016", "10.1001/jama.2016.0288")],
        "b": [ref(SEYMOUR, "Assessment of clinical criteria for sepsis.", "2016")],
    })

    merge_refs.main([str(review)])

    rows = read_rows(review)
    assert len(rows) == 1
    assert rows[0]["uncertain"] == ""


def test_near_identical_titles_merge_but_are_marked_uncertain(tmp_path):
    review = make_review(tmp_path, {
        "a": [ref(RAJKOMAR, "Scalable and accurate deep learning with electronic health records", "2018")],
        "b": [ref(RAJKOMAR, "Scalable and accurate deep learning for electronic health records", "2018")],
    })

    merge_refs.main([str(review)])

    rows = read_rows(review)
    assert len(rows) == 1
    assert rows[0]["uncertain"] == "y"


def test_near_identical_titles_in_the_same_paper_stay_separate(tmp_path):
    scalable = "Jazbec M, et al. Scalable gaussian process variational autoencoders. AISTATS 2020."
    sparse = "Jazbec M, et al. Sparse Gaussian Process Variational Autoencoders. arXiv 2020."
    review = make_review(tmp_path, {
        "a": [
            ref(scalable, "Scalable gaussian process variational autoencoders", "2020"),
            ref(sparse, "Sparse Gaussian Process Variational Autoencoders", "2020"),
        ],
    })

    merge_refs.main([str(review)])

    rows = read_rows(review)
    assert len(rows) == 2
    assert all(row["uncertain"] == "" for row in rows)


def test_same_title_different_year_stays_separate(tmp_path):
    review = make_review(tmp_path, {
        "a": [ref(VASWANI, "Attention is all you need", "2017")],
        "b": [ref(VASWANI, "Attention is all you need", "2023")],
    })

    merge_refs.main([str(review)])

    assert len(read_rows(review)) == 2


def test_rows_sorted_by_cited_count(tmp_path):
    review = make_review(tmp_path, {
        "a": [ref(VASWANI, "Attention is all you need", "2017"), ref(SEYMOUR, "Assessment of clinical criteria for sepsis", "2016")],
        "b": [ref(SEYMOUR, "Assessment of clinical criteria for sepsis", "2016")],
    })

    merge_refs.main([str(review)])

    assert [row["title"] for row in read_rows(review)][0] == "Assessment of clinical criteria for sepsis"


def test_reference_that_is_in_the_corpus_is_marked(tmp_path):
    review = make_review(
        tmp_path,
        {"a": [ref(SEYMOUR, "Assessment of clinical criteria for sepsis", "2016", "10.1001/jama.2016.0288")]},
        papers=[{"key": "seymour2016", "id": "10.1001/jama.2016.0288", "title": "Assessment of clinical criteria for sepsis"}],
    )

    merge_refs.main([str(review)])

    assert read_rows(review)[0]["inCorpus"] == "seymour2016"


def test_raw_not_found_in_paper_text_is_reported(tmp_path):
    review = make_review(tmp_path, {"a": [ref(SEYMOUR, "Assessment of clinical criteria for sepsis", "2016")]})
    fabricated = ref("Nobody N. A paper that does not exist. 2020.", "A paper that does not exist", "2020")
    (review / "refs" / "a.json").write_text(
        json.dumps({"key": "a", "references": [ref(SEYMOUR, "Assessment of clinical criteria for sepsis", "2016"), fabricated]}),
        encoding="utf-8",
    )

    merge_refs.main([str(review)])

    unverified = read_report(review)["unverified"]
    assert [u["title"] for u in unverified] == ["A paper that does not exist"]


def test_count_mismatch_is_reported(tmp_path):
    review = make_review(
        tmp_path,
        {"a": [ref(SEYMOUR, "Assessment of clinical criteria for sepsis", "2016")]},
        counts={"a": 3},
    )

    merge_refs.main([str(review)])

    assert read_report(review)["countMismatch"] == [{"key": "a", "extracted": 1, "counted": 3}]
