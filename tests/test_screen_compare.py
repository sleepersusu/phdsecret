import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import screen_compare  # noqa: E402


def paper(id_, title="T", authors=("Smith J", "Lee K")):
    return {"id": id_, "title": title, "year": 2021, "authors": list(authors), "abstract": "Abs",
            "venue": "J Clin", "routes": ["keyword"], "via": []}


def decisions(*pairs):
    return {"decisions": [{"id": i, "decision": d, "criterion": "I1" if d == "include" else "E1", "reason": "r"}
                          for i, d in pairs]}


POOL = [paper("10.1/inc"), paper("10.1/exc"), paper("10.1/split"), paper("10.1/unsure"), paper("10.1/missing")]
A = decisions(("10.1/inc", "include"), ("10.1/exc", "exclude"), ("10.1/split", "include"),
              ("10.1/unsure", "unsure"), ("10.1/missing", "include"))
B = decisions(("10.1/inc", "include"), ("10.1/exc", "exclude"), ("10.1/split", "exclude"), ("10.1/unsure", "include"))


def test_statuses():
    rows = screen_compare.compare(POOL, A, B)

    assert {r["id"]: r["status"] for r in rows} == {
        "10.1/inc": "included", "10.1/exc": "excluded", "10.1/split": "toUser",
        "10.1/unsure": "toUser", "10.1/missing": "toUser"}


def test_flow_numbers():
    rows = screen_compare.compare(POOL, A, B)
    counts = {"hits": 9, "unique": 6, "alreadyRead": 1, "noId": 2, "pool": 5}

    assert screen_compare.flow(counts, rows) == {
        "hits": 9, "unique": 6, "alreadyRead": 1, "noId": 2, "screened": 5,
        "included": 1, "excluded": 1, "toUser": 3}


def test_ris_has_included_and_to_user_only_with_one_au_per_author():
    rows = screen_compare.compare(POOL, A, B)

    ris = screen_compare.to_ris(rows)

    assert ris.count("TY  - JOUR") == 4
    assert ris.count("ER  - ") == 4
    assert "DO  - 10.1/exc" not in ris
    assert "AU  - Smith J\nAU  - Lee K" in ris
    assert "N1  - status: toUser" in ris


def test_ris_arxiv_and_pmid_use_doi_and_url_not_notes():
    rows = [{**paper("arxiv:2301.01234"), "status": "included"}, {**paper("pmid:123"), "status": "included"}]

    ris = screen_compare.to_ris(rows)

    assert "DO  - 10.48550/arXiv.2301.01234" in ris
    assert "UR  - https://arxiv.org/abs/2301.01234" in ris
    assert "UR  - https://pubmed.ncbi.nlm.nih.gov/123/" in ris
    assert "N1  - arXiv" not in ris and "N1  - PMID" not in ris
    assert ris.count("DO  - ") == 1


def test_ris_without_status_note():
    rows = [{**paper("10.1/a"), "status": "toUser"}]

    assert "N1  - status" not in screen_compare.to_ris(rows, with_status=False)
    assert "N1  - status: toUser" in screen_compare.to_ris(rows)


def test_decision_ids_are_canonicalised_before_matching():
    pool = [paper("arxiv:2301.01234")]
    a = decisions(("arXiv:2301.01234v2", "include"))
    b = decisions(("arxiv:2301.01234", "include"))

    assert screen_compare.compare(pool, a, b)[0]["status"] == "included"


def test_screen_check_counts_missing_and_unknown():
    check = screen_compare.screen_check(POOL, A, decisions(("10.1/inc", "include"), ("10.9/ghost", "include")))

    assert check["a"] == {"missing": 0, "unknown": 0}
    assert check["b"] == {"missing": 4, "unknown": 1}


def test_main_writes_csv_ris_and_flow(tmp_path):
    search = tmp_path / "search"
    search.mkdir()
    counts = {"hits": 5, "unique": 5, "alreadyRead": 0, "noId": 0, "pool": 5}
    (search / "pool.json").write_text(json.dumps({"pool": POOL, "counts": counts}), encoding="utf-8")
    (search / "screen-a.json").write_text(json.dumps(A), encoding="utf-8")
    (search / "screen-b.json").write_text(json.dumps(B), encoding="utf-8")

    code = screen_compare.main([str(tmp_path)])

    rows = list(csv.DictReader((search / "candidates.csv").open(encoding="utf-8")))
    assert code == 0
    assert rows[0]["authors"] == "Smith J; Lee K"
    assert json.loads((search / "flow.json").read_text(encoding="utf-8"))["toUser"] == 3
    assert (search / "candidates.ris").read_text(encoding="utf-8").count("ER  - ") == 4


def test_main_without_screen_files_exits_one(tmp_path):
    (tmp_path / "search").mkdir()
    (tmp_path / "search" / "pool.json").write_text(json.dumps({"pool": [], "counts": {}}), encoding="utf-8")

    assert screen_compare.main([str(tmp_path)]) == 1


def test_ris_values_with_newlines_stay_on_one_line():
    import re

    row = {**paper("10.1/nl", title="Line one\nline two"), "status": "included",
           "abstract": "Background: x\n\nMethods: y\nER  - fake"}

    ris = screen_compare.to_ris([row])
    lines = [line for line in ris.split("\n") if line.strip()]

    assert all(re.match(r"^[A-Z][A-Z0-9]  - ", line) for line in lines)
    assert sum(1 for line in lines if line.startswith("TY  - ")) == 1
    assert sum(1 for line in lines if line == "ER  - ") == 1
    assert "TI  - Line one line two" in lines
    assert "AB  - Background: x Methods: y ER - fake" in lines


def _setup(tmp_path, a=A, b=B):
    search = tmp_path / "search"
    search.mkdir(exist_ok=True)
    counts = {"hits": 5, "unique": 5, "alreadyRead": 0, "noId": 0, "pool": 5}
    (search / "pool.json").write_text(json.dumps({"pool": POOL, "counts": counts}), encoding="utf-8")
    (search / "screen-a.json").write_text(json.dumps(a), encoding="utf-8")
    (search / "screen-b.json").write_text(json.dumps(b), encoding="utf-8")
    return search


def test_main_records_screen_check_and_warns(tmp_path, capsys):
    search = _setup(tmp_path)

    code = screen_compare.main([str(tmp_path)])

    flow = json.loads((search / "flow.json").read_text(encoding="utf-8"))
    assert code == 0
    assert flow["screenCheck"] == {"a": {"missing": 0, "unknown": 0}, "b": {"missing": 1, "unknown": 0}}
    assert "警告" in capsys.readouterr().out


def test_final_writes_included_plus_user_included(tmp_path):
    search = _setup(tmp_path)
    screen_compare.main([str(tmp_path)])
    (search / "decisions.json").write_text(json.dumps(
        {"10.1/split": "include", "10.1/unsure": "exclude", "10.1/missing": "include"}), encoding="utf-8")

    code = screen_compare.main([str(tmp_path), "--final"])

    ris = (search / "final.ris").read_text(encoding="utf-8")
    flow = json.loads((search / "flow.json").read_text(encoding="utf-8"))
    assert code == 0
    assert ris.count("ER  - ") == 3
    assert "DO  - 10.1/inc" in ris and "DO  - 10.1/split" in ris and "DO  - 10.1/unsure" not in ris
    assert "N1  - status" not in ris
    assert (flow["final"], flow["userIncluded"], flow["userExcluded"]) == (3, 2, 1)
    assert flow["toUser"] == 3


def test_final_without_decisions_file_exits_one(tmp_path, capsys):
    _setup(tmp_path)

    assert screen_compare.main([str(tmp_path), "--final"]) == 1
    assert "decisions.json" in capsys.readouterr().err


def test_final_with_undecided_to_user_papers_exits_one(tmp_path, capsys):
    search = _setup(tmp_path)
    (search / "decisions.json").write_text(json.dumps({"10.1/split": "include"}), encoding="utf-8")

    code = screen_compare.main([str(tmp_path), "--final"])

    err = capsys.readouterr().err
    assert code == 1
    assert "10.1/unsure" in err and "10.1/missing" in err and not (search / "final.ris").exists()
