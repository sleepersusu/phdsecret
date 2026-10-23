import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import paperid  # noqa: E402


def test_doi_prefixes_case_and_trailing_dot():
    for raw in ["https://doi.org/10.1000/ABC.", "http://dx.doi.org/10.1000/abc", "doi: 10.1000/Abc", "10.1000/abc"]:
        assert paperid.canonical_id(raw) == "10.1000/abc"


def test_arxiv_forms_are_one_id_without_version():
    for raw in ["arXiv:2301.01234v3", "arxiv:2301.01234", "10.48550/arXiv.2301.01234", "https://doi.org/10.48550/arxiv.2301.01234v2"]:
        assert paperid.canonical_id(raw) == "arxiv:2301.01234"


def test_pmid_forms():
    assert paperid.canonical_id("PMID: 123") == "pmid:123"
    assert paperid.canonical_id("pmid:123") == "pmid:123"


def test_unconfirmed_or_empty_is_none():
    for raw in [None, "", "  ", "id 待確認", "not an id"]:
        assert paperid.canonical_id(raw) is None


def test_doi_aliases():
    assert paperid.doi_aliases("arXiv:2301.01234v2") == {"10.48550/arxiv.2301.01234"}
    assert paperid.doi_aliases("https://doi.org/10.1000/ABC") == {"10.1000/abc"}
    assert paperid.doi_aliases("PMID: 123") == set()
    assert paperid.doi_aliases(None) == set()


def test_normalize_doi_keeps_merge_refs_behavior():
    assert paperid.normalize_doi(" https://doi.org/10.1001/JAMA.2016.0288. ") == "10.1001/jama.2016.0288"
    assert paperid.normalize_doi(None) is None
