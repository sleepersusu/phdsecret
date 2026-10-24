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


def test_ris_arxiv_and_pmid_go_to_notes_not_doi():
    rows = [{**paper("arxiv:2301.01234"), "status": "included"}, {**paper("pmid:123"), "status": "included"}]

    ris = screen_compare.to_ris(rows)

    assert "DO  - " not in ris
    assert "N1  - arXiv:2301.01234" in ris
    assert "N1  - PMID: 123" in ris


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
