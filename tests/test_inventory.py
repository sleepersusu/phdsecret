import json
import sys
from pathlib import Path

from fpdf import FPDF
from pypdf import PdfReader, PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import inventory  # noqa: E402

BODY = "Deep learning for early sepsis prediction in intensive care units. " * 5


def make_pdf(path, pages, title=None):
    pdf = FPDF()
    pdf.set_font("helvetica", size=11)
    if title:
        pdf.set_title(title)
    for text in pages:
        pdf.add_page()
        if text:
            pdf.multi_cell(0, 6, text)
    pdf.output(str(path))
    return path


def encrypt_copy(src, dst, user_password):
    writer = PdfWriter()
    for page in PdfReader(src).pages:
        writer.add_page(page)
    writer.encrypt(user_password=user_password, owner_password="owner")
    with open(dst, "wb") as f:
        writer.write(f)
    return dst


def test_text_pdf_is_readable_and_counts_pages(tmp_path):
    path = make_pdf(tmp_path / "a.pdf", [BODY, BODY])

    result = inventory.inspect_pdf(path)

    assert result["pages"] == 2
    assert result["readable"] is True
    assert result["encrypted"] is False


def test_pdf_without_text_is_not_readable(tmp_path):
    path = make_pdf(tmp_path / "scan.pdf", ["", ""])

    result = inventory.inspect_pdf(path)

    assert result["pages"] == 2
    assert result["readable"] is False


def test_finds_doi_and_strips_trailing_punctuation(tmp_path):
    path = make_pdf(tmp_path / "a.pdf", [BODY + "\nhttps://doi.org/10.1016/j.jbi.2023.104321.", BODY])

    result = inventory.inspect_pdf(path)

    assert result["doi"] == "10.1016/j.jbi.2023.104321"


def test_doi_only_in_reference_pages_is_ignored(tmp_path):
    path = make_pdf(tmp_path / "a.pdf", [BODY, BODY, BODY + "\ndoi:10.1000/cited.paper"])

    result = inventory.inspect_pdf(path)

    assert result["doi"] is None


def test_finds_arxiv_id_without_version(tmp_path):
    path = make_pdf(tmp_path / "a.pdf", ["arXiv:2401.01234v2 [cs.CL] 3 Jan 2024\n" + BODY])

    result = inventory.inspect_pdf(path)

    assert result["arxiv"] == "2401.01234"


def test_title_comes_from_metadata_only(tmp_path):
    titled = make_pdf(tmp_path / "t.pdf", [BODY], title="Sepsis Prediction with Transformers")
    untitled = make_pdf(tmp_path / "u.pdf", [BODY])

    assert inventory.inspect_pdf(titled)["title"] == "Sepsis Prediction with Transformers"
    assert inventory.inspect_pdf(untitled)["title"] is None


def test_password_protected_pdf_is_unreadable(tmp_path):
    plain = make_pdf(tmp_path / "plain.pdf", [BODY])
    locked = encrypt_copy(plain, tmp_path / "locked.pdf", user_password="secret")

    result = inventory.inspect_pdf(locked)

    assert result["encrypted"] is True
    assert result["readable"] is False
    assert result["pages"] is None


def test_permissions_only_encryption_is_still_readable(tmp_path):
    plain = make_pdf(tmp_path / "plain.pdf", [BODY])
    restricted = encrypt_copy(plain, tmp_path / "restricted.pdf", user_password="")

    result = inventory.inspect_pdf(restricted)

    assert result["encrypted"] is True
    assert result["readable"] is True


def test_main_writes_sorted_inventory_json(tmp_path, capsys):
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    make_pdf(pdfs / "b.pdf", [BODY])
    make_pdf(pdfs / "a.pdf", [BODY])

    code = inventory.main([str(tmp_path)])

    written = json.loads((tmp_path / "inventory.json").read_text(encoding="utf-8"))
    assert code == 0
    assert [row["file"] for row in written] == ["a.pdf", "b.pdf"]
    assert "| file |" in capsys.readouterr().out


def test_main_includes_uppercase_extension(tmp_path):
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    make_pdf(pdfs / "Paper.PDF", [BODY])

    inventory.main([str(tmp_path)])

    written = json.loads((tmp_path / "inventory.json").read_text(encoding="utf-8"))
    assert [row["file"] for row in written] == ["Paper.PDF"]


def test_main_records_broken_pdf_and_keeps_going(tmp_path, capsys):
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    (pdfs / "broken.pdf").write_bytes(b"not a pdf at all")
    make_pdf(pdfs / "good.pdf", [BODY])

    code = inventory.main([str(tmp_path)])

    written = json.loads((tmp_path / "inventory.json").read_text(encoding="utf-8"))
    broken, good = written
    assert code == 0
    assert broken["readable"] is False
    assert broken["error"]
    assert good["readable"] is True
    assert "壞檔" in capsys.readouterr().out


def test_main_fails_without_pdfs_dir(tmp_path, capsys):
    code = inventory.main([str(tmp_path)])

    assert code == 1
    assert "pdfs" in capsys.readouterr().err
