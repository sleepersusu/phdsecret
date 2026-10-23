"""引文比對用的文字正規化：PDF 抽出來的字與 agent 抄的字常差在連字、引號、斷行，不差在內容。"""
import re
import unicodedata

PUNCTUATION_MAP = {
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "–": "-",
    "—": "-",
    "−": "-",
    " ": " ",
}
LINE_BREAK_HYPHEN = re.compile(r"(\w)-[ \t]*\n\s*(\w)")
WHITESPACE = re.compile(r"\s+")
SPACES_AND_HYPHENS = re.compile(r"[\s\-]+")


def normalize(text):
    """嚴格比對用：只抹掉排版差異（連字、彎引號、行尾斷字、多餘空白）。"""
    text = unicodedata.normalize("NFKC", text)
    text = LINE_BREAK_HYPHEN.sub(r"\1\2", text)
    for source, target in PUNCTUATION_MAP.items():
        text = text.replace(source, target)
    return WHITESPACE.sub(" ", text).strip()


def loosen(text):
    """寬鬆比對用：再忽略大小寫、空白與連字號，吸收 state-of-the-art 被斷成 stateof the art 這類差異。"""
    return SPACES_AND_HYPHENS.sub("", normalize(text).casefold())
