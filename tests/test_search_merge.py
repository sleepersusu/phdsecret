import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import search_merge  # noqa: E402


def hit(id_, route, title="T", abstract=None, via=None):
    return {"id": id_, "title": title, "year": 2021, "authors": ["A"], "abstract": abstract,
            "venue": "J", "route": route, "via": via}


def test_same_paper_from_two_routes_merges_routes_and_fills_fields():
    hits = [hit("https://doi.org/10.1/ABC", "keyword", abstract=None, via="q1"),
            hit("10.1/abc", "forward", abstract="An abstract", via="10.9/src")]

    result = search_merge.merge(hits, {})

    assert len(result["pool"]) == 1
    paper = result["pool"][0]
    assert paper["id"] == "10.1/abc"
    assert paper["routes"] == ["keyword", "forward"]
    assert paper["via"] == ["q1", "10.9/src"]
    assert paper["abstract"] == "An abstract"


def test_arxiv_versions_are_the_same_paper():
    result = search_merge.merge([hit("arXiv:2301.01234v1", "keyword"), hit("arxiv:2301.01234v2", "backward")], {})

    assert [p["id"] for p in result["pool"]] == ["arxiv:2301.01234"]


def test_already_read_papers_leave_the_pool():
    index = {"papers": {"10.1/abc": {"title": "T", "primary": None, "appearances": []}}}

    result = search_merge.merge([hit("10.1/abc", "keyword"), hit("10.1/abc", "forward")], index)

    assert result["pool"] == []
    assert [p["id"] for p in result["alreadyRead"]] == ["10.1/abc"]


def test_hits_without_identifier_go_to_no_id():
    result = search_merge.merge([hit(None, "keyword", title="No id"), hit("10.1/abc", "keyword")], {})

    assert [h["title"] for h in result["noId"]] == ["No id"]


def test_counts():
    index = {"papers": {"10.1/read": {}}}
    hits = [hit("10.1/a", "keyword"), hit("10.1/a", "forward"), hit("10.1/read", "keyword"), hit("", "keyword")]

    counts = search_merge.merge(hits, index)["counts"]

    assert counts == {"hits": 4, "unique": 2, "alreadyRead": 1, "noId": 1, "pool": 1}


def test_main_writes_pool_and_tolerates_missing_library(tmp_path):
    hits_dir = tmp_path / "search" / "hits"
    hits_dir.mkdir(parents=True)
    (hits_dir / "keyword.json").write_text(json.dumps([hit("10.1/a", "keyword")]), encoding="utf-8")

    code = search_merge.main([str(tmp_path), "--library", str(tmp_path / "library")])

    pool = json.loads((tmp_path / "search" / "pool.json").read_text(encoding="utf-8"))
    assert code == 0
    assert pool["counts"]["pool"] == 1


def test_main_without_hits_exits_one(tmp_path):
    assert search_merge.main([str(tmp_path), "--library", str(tmp_path / "library")]) == 1
