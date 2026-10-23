# 卡片格式

萃取者寫的是 JSON；`scripts/build_card.py` 把它轉成給人讀的 `card.md`。

## 共通規則

- `key`：PDF 檔名去掉副檔名（`pdfs/smith2023.pdf` → `smith2023`）。
- `page`：PDF 的第幾頁，對應 `text/<key>.txt` 裡的 `=== p.N ===`，不是期刊印的頁碼。
- `quote`：從 `text/<key>.txt` 那一頁**逐字照抄**的一段，不改寫、不翻譯、不補字。
  - 一個子句到一句話，盡量 6 個字（word）以上，短到哪裡都對得上的不算證據。
  - 不跨頁；不含雙引號（`"`、`“`、`”`）與換行，原文有雙引號就換一段抄。
  - 每一項都要有 `quote` 和 `page`，沒有證據的項目不要寫。
- 原文沒提到的欄位給空清單 `[]`，代表「原文未提及」。不推測、不用常識補。
- 說明文字（`text`、`purpose`）用 `protocol.md` 定的卡片語言。

## 結構化欄位（甲乙兩人都要寫，會被拿來比對）

| 欄位 | 型別 | 寫什麼 |
|---|---|---|
| `studyType` | 物件 | `value` 只能是：`實證研究`、`系統設計與實作`、`review`、`質性研究`、`其他` |
| `dataSources` | 清單 | 用到的每個資料集、世代、醫院、語料；`value` 只寫原文的名稱本身，不翻譯、不加括號補充（版本、年份寫進 `designNotes`） |
| `sampleSize` | 清單 | 原文報告的每個樣本數，連單位（病人、住院次數、影像、題目⋯）；`value` 含數字 |
| `methods` | 清單 | 本文提出或主要評估的方法，加上結果表裡出現的比較基準；`value` 只寫原文的名稱本身，不翻譯、不加括號補充（架構細節寫進 `designNotes`） |
| `results` | 清單 | 摘要裡出現的所有量化結果，加上結果節主表中主要方法那一列；`value` 寫「指標 數值（設定）」 |

結構化欄位的每一項：`{"value": "...", "quote": "...", "page": N}`；`studyType` 是單一物件，其餘是清單。

## 敘述欄位（只有甲寫）

每一項：`{"text": "說明", "quote": "...", "page": N}`。

| 欄位 | 寫什麼 |
|---|---|
| `researchQuestion` | 這篇想回答什麼 |
| `designNotes` | 研究設計的說明：怎麼切資料、比較什麼、怎麼評估 |
| `findings` | 作者的結論 |
| `contributions` | 作者自己宣稱的貢獻 |
| `limitations` | 作者自己寫的限制 |
| `proposalRelation` | 跟提案的關係，每項多兩個欄位：`relation`（`支持`、`衝突`、`已有人做過`）與 `proposalQuote`（從 `text/proposal.txt` 逐字照抄的對應句子，同樣不含雙引號） |
| `custom` | `protocol.md` 的自訂欄位與加掛清單，`{"欄位名": [項目, ...]}`。加掛清單（CHARMS 等）每個項目一個欄位，欄位名照清單原文（例：`Source of data`） |

## 結構拆解（只有甲寫）

`structure`：一級章節逐一列出，`{"heading": "原文的節標題，逐字", "page": 起始頁, "endPage": 結束頁, "purpose": "這一節在做什麼"}`。`heading` 也會被當成引文核對。

## 完整範例

```json
{
  "key": "smith2023",
  "id": "10.1016/j.jbi.2023.104321",
  "title": "Early Sepsis Prediction with Transformers",
  "structured": {
    "studyType": {"value": "實證研究", "quote": "We conducted a retrospective cohort study", "page": 2},
    "dataSources": [{"value": "MIMIC-IV", "quote": "using adult ICU stays from MIMIC-IV", "page": 3}],
    "sampleSize": [{"value": "45,121 ICU stays", "quote": "resulting in 45,121 ICU stays", "page": 3}],
    "methods": [{"value": "Transformer", "quote": "we train a Transformer encoder on hourly vitals", "page": 4}],
    "results": [{"value": "AUROC 0.89（內部測試）", "quote": "achieved an AUROC of 0.89 on the internal test set", "page": 6}]
  },
  "narrative": {
    "researchQuestion": [{"text": "能否在發病前 6 小時預測敗血症", "quote": "whether sepsis can be predicted six hours before onset", "page": 1}],
    "designNotes": [],
    "findings": [],
    "contributions": [],
    "limitations": [],
    "proposalRelation": [{"relation": "已有人做過", "text": "提案想用的資料集與預測時距，這篇都做過", "quote": "using adult ICU stays from MIMIC-IV", "page": 3, "proposalQuote": "We will use MIMIC-IV to predict sepsis"}],
    "custom": {}
  },
  "structure": [{"heading": "2 Methods", "page": 3, "endPage": 5, "purpose": "資料、前處理與模型"}]
}
```
