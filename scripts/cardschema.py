"""卡片欄位定義，給比對、合成、矩陣三支腳本共用；欄位意義見 .claude/skills/lit-extract/card-schema.md。"""

# (欄位, 比對方式, 標題)。比對方式：enum 整個值要一樣、names 比名稱集合、numbers 比數字集合。
STRUCTURED = [
    ("studyType", "enum", "研究類型"),
    ("dataSources", "names", "資料來源"),
    ("sampleSize", "numbers", "樣本數"),
    ("methods", "names", "方法"),
    ("results", "numbers", "數字"),
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


def field_items(value):
    """studyType 是單一物件，其餘結構化欄位是清單；統一成清單處理。"""
    if value is None:
        return []
    return [value] if isinstance(value, dict) else value
