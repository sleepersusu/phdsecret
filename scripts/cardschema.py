"""卡片欄位定義，給比對、合成、矩陣等腳本共用；欄位意義見 .claude/skills/lit-extract/card-schema.md。"""
import re

# (欄位, 比對方式, 標題)。比對方式：enum 整個值要一樣、names 比名稱集合、numbers 比數字集合。
STRUCTURED = [
    ("studyType", "enum", "研究類型"),
    ("dataSources", "names", "資料來源"),
    ("sampleSize", "numbers", "樣本數"),
    ("methods", "names", "方法"),
    ("results", "numbers", "數字"),
    ("articleType", "enum", "文章類型"),
]

NARRATIVE = [
    ("researchQuestion", "研究問題"),
    ("designNotes", "說明"),
    ("findings", "結論"),
    ("contributions", "貢獻"),
    ("limitations", "限制"),
]

# 甲乙都寫、要比對的敘述欄位；custom 與 structure 只有甲寫，不比對。
DUAL_NARRATIVE = [field for field, _ in NARRATIVE] + ["proposalRelation"]

# 領域標籤存在 structured.topics，甲乙都寫但不比對：自由命名的字面必然不同，改取聯集再由字典歸併。
TOPICS = "topics"

# 只能有一個值的結構化欄位（單一物件，不是清單）。
SINGLE_VALUE_FIELDS = {"studyType", "articleType"}

NON_WORD = re.compile(r"[\W_]+")


def field_items(value):
    """單值欄位是單一物件，其餘結構化欄位是清單；統一成清單處理。"""
    if value is None:
        return []
    return [value] if isinstance(value, dict) else value


def name_key(name):
    """名稱比對用：忽略大小寫與標點空白，MIMIC-IV 與 mimic iv 視為同一個。"""
    return NON_WORD.sub("", (name or "").casefold())
