# 子專案 2：吸收輔助（精簡摘要＋閱讀順序）

日期：2026-10-23 · 狀態：本人已確認設計

## 目的

本人要「快速吸收」。現有產出 `card.md` 是資料表，不是讀書筆記；12 篇也沒有建議的閱讀順序。本設計補兩樣：每篇一份約半頁的摘要、整批一份閱讀順序。

兩者都**不引入新資訊**：摘要只改寫已核對過的卡片項目，閱讀順序只用已存在的資料（卡片、`references.csv`），所以不新增錯誤來源。

## 精簡摘要

### 位置與時機

萃取段（`lit-extract`）每篇的卡片完成並通過引文核對後，接著做摘要。篇與篇平行。

### summarizer（`summarizer.md`，新增）

- 讀：`cards/<key>/card.json`、`protocol.md`（卡片語言）。**不讀全文。**
- 寫：`cards/<key>/summary.md`，一段 5～8 句。
- 每句句末附一或多個來源標記 `[<欄位>#<n>]`，`n` 從 1 起算，指向 `card.json` 該欄位清單的第 n 項。
  - 可用欄位：結構化（`studyType` 不帶編號，寫 `[studyType]`）、敘述欄位、`custom.<名稱>`。
- 只能改寫標記所指項目的內容，不加卡片沒有的事實、不加評論。
- 回報：`DONE <key>：<n> 句`。

### `summary_check.py`（新增）

用法：`uv run scripts/summary_check.py reviews/<slug>/cards/<key>`

1. 句子切分：以 `。`、`. `、`！`、`？` 與換行切句，空白句略過。
2. 每句至少一個標記，否則列為「無來源」。
3. 每個標記都要對得到 `card.json` 的真實項目（欄位存在、編號在範圍內），否則列為「標記無效」。
4. 涵蓋四塊，各至少被一個標記引用：
   - 研究問題：`researchQuestion`
   - 研究設計：`methods` 或 `designNotes` 或 `dataSources`
   - 結論：`findings` 或 `results`
   - 限制：`limitations`
   該塊在卡片上全為空清單時不強制。
- 輸出：問題逐條印出；有問題 exit 1，否則 exit 0。

### 失敗處理

exit 1 → 對同一個 summarizer 用 SendMessage 附上失敗輸出修一輪 → 仍不過記成例外（`progress.md`），停 2 呈現。

## 閱讀順序

### 位置與時機

參考文獻合併段（`lit-refs`）收尾，`merge_refs.py` 之後（需要 `references.csv`）。

### `reading_order.py`（新增）

用法：`uv run scripts/reading_order.py reviews/<slug>`

讀 `papers.json`、`cards/<key>/card.json`、`references.csv`，寫 `reviews/<slug>/reading-order.md`。

排序鍵（依序比較）：

1. `studyType.value == "review"` 者在前。
2. 本批引用次數多者在前：`references.csv` 中對應到本批論文（`inCorpus`）那一列的被引用次數；對不到則為 0。
3. `proposalRelation` 中 `relation` 為 `衝突` 或 `已有人做過` 的項目數多者在前。
4. `key` 字母順序。

沒有 `card.json` 的篇（萃取例外）列在最後，理由寫「卡片未完成」。

輸出格式：

```markdown
# 建議閱讀順序

| # | 論文 | 理由 | 連結 |
|---|---|---|---|
| 1 | <title> | review；被本批 3 篇引用 | [摘要](cards/<key>/summary.md)・[卡片](cards/<key>/card.md) |
```

理由由排序鍵產生，只列非零／成立的訊號，以「；」連接；全不成立寫「無特殊訊號」。摘要不存在時只附卡片連結。

## 流程與 skill 改動（用 `skill-creator`）

- `lit-extract/SKILL.md`：每篇第 2 節流程末加摘要與 `summary_check.py`；`progress.md` 每篇一行加「摘要 <通過|例外>」。
- 新增 `lit-extract/summarizer.md`。
- `lit-refs/SKILL.md`：第 4 節收尾加 `reading_order.py`。
- `lit-gaps/SKILL.md`：停 2 呈現的檔案位置加 `reading-order.md`，並加一句「建議從 `reading-order.md` 開始讀」。

## 測試（先紅後綠）

- `test_summary_check.py`：全部合格 exit 0；某句無標記；標記欄位不存在；編號超出範圍；`[studyType]` 不帶編號合法；缺限制塊 exit 1；限制欄位為空時不要求；研究設計塊以 `designNotes` 滿足；`custom.<名稱>#n` 解析。
- `test_reading_order.py`：review 排最前；本批被引用次數排序；衝突／已有人做過數排序；平手依 key；缺 `card.json` 排最後；理由字串只列成立訊號；無訊號寫「無特殊訊號」；無 `summary.md` 只附卡片連結。

## 要改的檔案

- 新增：`scripts/summary_check.py`、`scripts/reading_order.py`、對應測試、`lit-extract/summarizer.md`。
- 修改：`lit-extract/SKILL.md`、`lit-refs/SKILL.md`、`lit-gaps/SKILL.md`。

## 成本

摘要每篇一次 agent 呼叫，只讀卡片不讀全文，成本低。閱讀順序不用 agent。
