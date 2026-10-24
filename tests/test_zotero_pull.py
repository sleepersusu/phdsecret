import http.client
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import zotero_pull  # noqa: E402

BASE = "http://zotero.test/api"


def paper(key, title, doi="", date="2021-03-29", last="Page", extra=""):
    creators = [{"creatorType": "author", "lastName": last}] if last else []
    return {"key": key, "data": {"itemType": "journalArticle", "title": title, "DOI": doi, "date": date,
                                 "extra": extra, "creators": creators}, "links": {}}


def pdf(key, parent, path):
    data = {"itemType": "attachment", "contentType": "application/pdf", "title": "PDF"}
    if parent:
        data["parentItem"] = parent
    return {"key": key, "data": data, "links": {"enclosure": {"href": Path(path).as_uri()}}}


def make_pdf(tmp_path, name, content=b"%PDF-1.4 test"):
    path = tmp_path / "storage" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_base_key_rules():
    assert zotero_pull.base_key({"creators": [{"lastName": "Müller"}], "date": "07/2016"}) == "muller2016"
    assert zotero_pull.base_key({"creators": [{"lastName": "王"}], "title": "Deep learning for X", "date": ""}) == "deepnd"
    assert zotero_pull.base_key({"creators": [{"name": "WHO Group"}], "date": "2020"}) == "whogroup2020"


def test_pull_copies_pdf_with_key_and_id(tmp_path):
    src = make_pdf(tmp_path, "Page …等 - 2021 - PRISMA.pdf")
    items = [paper("P1", "PRISMA 2020", doi="10.1136/BMJ.n71"), pdf("A1", "P1", src)]

    result = zotero_pull.pull(items, tmp_path / "pdfs")

    assert result["pulled"] == [{"key": "page2021", "id": "10.1136/bmj.n71", "title": "PRISMA 2020", "zoteroKey": "P1"}]
    assert (tmp_path / "pdfs" / "page2021.pdf").read_bytes() == src.read_bytes()
    assert src.exists()


def test_same_key_gets_letter_suffix(tmp_path):
    items = [paper("P1", "Alpha", doi="10.1/a"), pdf("A1", "P1", make_pdf(tmp_path, "a.pdf")),
             paper("P2", "Beta", doi="10.1/b"), pdf("A2", "P2", make_pdf(tmp_path, "b.pdf"))]

    result = zotero_pull.pull(items, tmp_path / "pdfs")

    assert [p["key"] for p in result["pulled"]] == ["page2021", "page2021a"]


def test_unrelated_existing_pdf_makes_new_paper_take_next_suffix(tmp_path):
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    (pdfs / "page2021.pdf").write_bytes(b"mine")
    items = [paper("P1", "Alpha", doi="10.1/a"), pdf("A1", "P1", make_pdf(tmp_path, "a.pdf", b"alpha"))]

    result = zotero_pull.pull(items, pdfs)

    assert (pdfs / "page2021.pdf").read_bytes() == b"mine"
    assert (pdfs / "page2021a.pdf").read_bytes() == b"alpha"
    assert [p["key"] for p in result["pulled"]] == ["page2021a"]
    assert result["skipped"] == []


def test_paper_without_pdf_and_loose_pdf_are_listed(tmp_path):
    items = [paper("P1", "No PDF here", doi="10.1/a"), pdf("A9", None, make_pdf(tmp_path, "RAISE.pdf"))]
    items[1]["data"]["title"] = "RAISE2026"

    result = zotero_pull.pull(items, tmp_path / "pdfs")

    assert result["noPdf"] == [{"title": "No PDF here", "id": "10.1/a", "zoteroKey": "P1"}]
    assert result["noMetadata"] == [{"title": "RAISE2026", "zoteroKey": "A9"}]


def test_arxiv_id_from_extra_when_no_doi(tmp_path):
    items = [paper("P1", "Preprint", extra="arXiv: 2301.01234v2\nother"), pdf("A1", "P1", make_pdf(tmp_path, "p.pdf"))]

    result = zotero_pull.pull(items, tmp_path / "pdfs")

    assert result["pulled"][0]["id"] == "arxiv:2301.01234"


def test_collection_items_paginates():
    collections = [{"key": "C1", "data": {"name": "reviewsystem"}, "meta": {}}]
    page1 = [paper(f"P{i}", "T") for i in range(100)]
    page2 = [paper("P100", "T")]
    responses = {f"{BASE}/users/0/collections?limit=100&start=0": collections,
                 f"{BASE}/users/0/collections/C1/items?limit=100&start=0": page1,
                 f"{BASE}/users/0/collections/C1/items?limit=100&start=100": page2}

    key, items = zotero_pull.collection_items(BASE, "reviewsystem", responses.__getitem__)

    assert key == "C1" and len(items) == 101


def test_main_reports_unreachable_zotero(tmp_path, capsys):
    def down(url):
        raise zotero_pull.ZoteroUnavailable("refused")

    code = zotero_pull.main([str(tmp_path), "--collection", "x", "--base", BASE], fetch=down)

    assert code == 1
    assert "允許此電腦上的其他應用程式與 Zotero 通訊" in capsys.readouterr().err


def test_main_lists_collections_when_name_not_found(tmp_path, capsys):
    collections = [{"key": "C1", "data": {"name": "reviewsystem"}, "meta": {}}]

    code = zotero_pull.main([str(tmp_path), "--collection", "nope", "--base", BASE],
                            fetch={f"{BASE}/users/0/collections?limit=100&start=0": collections}.__getitem__)

    assert code == 1
    assert "reviewsystem" in capsys.readouterr().err


def test_main_writes_zotero_pull_json(tmp_path):
    src = make_pdf(tmp_path, "a.pdf")
    collections = [{"key": "C1", "data": {"name": "demo"}, "meta": {}}]
    items = [paper("P1", "Alpha", doi="10.1/a"), pdf("A1", "P1", src)]
    responses = {f"{BASE}/users/0/collections?limit=100&start=0": collections,
                 f"{BASE}/users/0/collections/C1/items?limit=100&start=0": items}
    review = tmp_path / "reviews" / "demo"

    code = zotero_pull.main([str(review), "--collection", "demo", "--base", BASE], fetch=responses.__getitem__)

    result = json.loads((review / "search" / "zotero-pull.json").read_text(encoding="utf-8"))
    assert code == 0
    assert result["pulled"][0]["key"] == "page2021"
    assert (review / "pdfs" / "page2021.pdf").exists()


def test_same_key_suffix_goes_past_z(tmp_path):
    items = []
    for i in range(29):
        items += [paper(f"P{i}", f"Title {i:02d}", doi=f"10.1/{i}"), pdf(f"A{i}", f"P{i}", make_pdf(tmp_path, f"{i}.pdf"))]

    result = zotero_pull.pull(items, tmp_path / "pdfs")

    keys = [p["key"] for p in result["pulled"]]
    assert len(keys) == len(set(keys)) == 29
    assert {"page2021", "page2021a", "page2021z", "page2021aa", "page2021ab"} <= set(keys)


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_fetch_json_non_json_response_is_unavailable(monkeypatch):
    monkeypatch.setattr(zotero_pull.urllib.request, "urlopen", lambda url, timeout=None: FakeResponse(b"<html>not json"))

    with pytest.raises(zotero_pull.ZoteroUnavailable):
        zotero_pull.fetch_json(BASE)


def test_fetch_json_undecodable_response_is_unavailable(monkeypatch):
    monkeypatch.setattr(zotero_pull.urllib.request, "urlopen", lambda url, timeout=None: FakeResponse(b"\xff\xfe"))

    with pytest.raises(zotero_pull.ZoteroUnavailable):
        zotero_pull.fetch_json(BASE)


def test_fetch_json_http_exception_is_unavailable(monkeypatch):
    def broken(url, timeout=None):
        raise http.client.HTTPException("bad status line")

    monkeypatch.setattr(zotero_pull.urllib.request, "urlopen", broken)

    with pytest.raises(zotero_pull.ZoteroUnavailable):
        zotero_pull.fetch_json(BASE)


def test_multiple_pdf_attachments_use_first_existing(tmp_path):
    existing = make_pdf(tmp_path, "good.pdf")
    missing = tmp_path / "storage" / "gone.pdf"
    items = [paper("P1", "Alpha", doi="10.1/a"), pdf("A1", "P1", missing), pdf("A2", "P1", existing)]

    result = zotero_pull.pull(items, tmp_path / "pdfs")

    assert [p["zoteroKey"] for p in result["pulled"]] == ["P1"]
    assert (tmp_path / "pdfs" / "page2021.pdf").read_bytes() == existing.read_bytes()


def test_existing_target_is_never_overwritten_even_if_check_is_bypassed(tmp_path, monkeypatch):
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    (pdfs / "page2021.pdf").write_bytes(b"mine")
    real_exists = Path.exists
    monkeypatch.setattr(Path, "exists", lambda self: False if self.name == "page2021.pdf" else real_exists(self))
    items = [paper("P1", "Alpha", doi="10.1/a"), pdf("A1", "P1", make_pdf(tmp_path, "a.pdf"))]

    result = zotero_pull.pull(items, pdfs)

    assert (pdfs / "page2021.pdf").read_bytes() == b"mine"
    assert result["skipped"] == [{"key": "page2021", "title": "Alpha"}]
    assert result["pulled"] == []



def _collection_responses(items, collections=None):
    collections = collections or [{"key": "C1", "data": {"name": "demo"}, "meta": {}}]
    return {f"{BASE}/users/0/collections?limit=100&start=0": collections,
            f"{BASE}/users/0/collections/C1/items?limit=100&start=0": items}


def test_rerun_keeps_previous_keys_and_does_not_recopy(tmp_path):
    review = tmp_path / "reviews" / "demo"
    alpha_paper = paper("P1", "Alpha", doi="10.1/a", last="Smith", date="2023")
    beta_paper = paper("P2", "Beta", doi="10.1/b", last="Smith", date="2023")
    beta_pdf = pdf("A2", "P2", make_pdf(tmp_path, "beta.pdf", b"beta-bytes"))
    args = [str(review), "--collection", "demo", "--base", BASE]

    run1 = _collection_responses([alpha_paper, beta_paper, beta_pdf])
    assert zotero_pull.main(args, fetch=run1.__getitem__) == 0
    assert (review / "pdfs" / "smith2023.pdf").read_bytes() == b"beta-bytes"

    alpha_pdf = pdf("A1", "P1", make_pdf(tmp_path, "alpha.pdf", b"alpha-bytes"))
    run2 = _collection_responses([alpha_paper, beta_paper, beta_pdf, alpha_pdf])
    assert zotero_pull.main(args, fetch=run2.__getitem__) == 0

    result = json.loads((review / "search" / "zotero-pull.json").read_text(encoding="utf-8"))
    assert result["pulled"] == [
        {"key": "smith2023", "id": "10.1/b", "title": "Beta", "zoteroKey": "P2"},
        {"key": "smith2023a", "id": "10.1/a", "title": "Alpha", "zoteroKey": "P1"}]
    assert result["skipped"] == [] and result["noPdf"] == []
    assert sorted(p.name for p in (review / "pdfs").iterdir()) == ["smith2023.pdf", "smith2023a.pdf"]
    assert (review / "pdfs" / "smith2023.pdf").read_bytes() == b"beta-bytes"
    assert (review / "pdfs" / "smith2023a.pdf").read_bytes() == b"alpha-bytes"


def test_collections_are_paginated():
    first = [{"key": f"X{i}", "data": {"name": f"c{i}"}, "meta": {}} for i in range(100)]
    second = [{"key": "C1", "data": {"name": "demo"}, "meta": {}}]
    responses = {f"{BASE}/users/0/collections?limit=100&start=0": first,
                 f"{BASE}/users/0/collections?limit=100&start=100": second,
                 f"{BASE}/users/0/collections/C1/items?limit=100&start=0": []}

    key, items = zotero_pull.collection_items(BASE, "demo", responses.__getitem__)

    assert key == "C1" and items == []


def test_duplicate_collection_names_exit_one(tmp_path, capsys):
    collections = [{"key": "C1", "data": {"name": "demo"}, "meta": {}},
                   {"key": "C2", "data": {"name": "demo"}, "meta": {}}]

    code = zotero_pull.main([str(tmp_path), "--collection", "demo", "--base", BASE],
                            fetch=_collection_responses([], collections).__getitem__)

    err = capsys.readouterr().err
    assert code == 1
    assert "有多個同名資料夾" in err and "C1" in err and "C2" in err


def test_summary_separates_new_and_cumulative_counts(tmp_path, capsys):
    review = tmp_path / "reviews" / "demo"
    responses = _collection_responses([paper("P1", "Alpha", doi="10.1/a"),
                                       pdf("A1", "P1", make_pdf(tmp_path, "a.pdf"))])
    args = [str(review), "--collection", "demo", "--base", BASE]

    zotero_pull.main(args, fetch=responses.__getitem__)
    first = capsys.readouterr().out
    zotero_pull.main(args, fetch=responses.__getitem__)
    second = capsys.readouterr().out

    assert "本次新複製 1 篇（累計 1 篇）" in first
    assert "本次新複製 0 篇（累計 1 篇）" in second
