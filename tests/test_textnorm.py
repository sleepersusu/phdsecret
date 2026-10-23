import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from textnorm import loosen, normalize  # noqa: E402


def test_normalize_expands_ligatures():
    assert normalize("ﬁnding") == "finding"


def test_normalize_straightens_quotes_and_dashes():
    assert normalize("“model” – it’s") == "\"model\" - it's"


def test_normalize_joins_words_split_across_lines():
    assert normalize("early predic-\ntion of sepsis") == "early prediction of sepsis"


def test_normalize_collapses_whitespace():
    assert normalize("  a \n\n b\tc ") == "a b c"


def test_loosen_ignores_case_spaces_and_hyphens():
    assert loosen("State-of-the-art  Model") == loosen("stateof the art model")
