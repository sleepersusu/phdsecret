import json
import sys
from pathlib import Path

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


def test_existing_pdf_is_not_overwritten(tmp_path):
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    (pdfs / "page2021.pdf").write_bytes(b"mine")
    items = [paper("P1", "Alpha", doi="10.1/a"), pdf("A1", "P1", make_pdf(tmp_path, "a.pdf"))]

    result = zotero_pull.pull(items, pdfs)

    assert (pdfs / "page2021.pdf").read_bytes() == b"mine"
    assert result["skipped"] == [{"key": "page2021", "title": "Alpha"}]
    assert result["pulled"] == []


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
    responses = {f"{BASE}/users/0/collections?limit=100": collections,
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
                            fetch={f"{BASE}/users/0/collections?limit=100": collections}.__getitem__)

    assert code == 1
    assert "reviewsystem" in capsys.readouterr().err


def test_main_writes_zotero_pull_json(tmp_path):
    src = make_pdf(tmp_path, "a.pdf")
    collections = [{"key": "C1", "data": {"name": "demo"}, "meta": {}}]
    items = [paper("P1", "Alpha", doi="10.1/a"), pdf("A1", "P1", src)]
    responses = {f"{BASE}/users/0/collections?limit=100": collections,
                 f"{BASE}/users/0/collections/C1/items?limit=100&start=0": items}
    review = tmp_path / "reviews" / "demo"

    code = zotero_pull.main([str(review), "--collection", "demo", "--base", BASE], fetch=responses.__getitem__)

    result = json.loads((review / "search" / "zotero-pull.json").read_text(encoding="utf-8"))
    assert code == 0
    assert result["pulled"][0]["key"] == "page2021"
    assert (review / "pdfs" / "page2021.pdf").exists()
