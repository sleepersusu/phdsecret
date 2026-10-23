# 子專案 1：萃取完整性檢查

日期：2026-10-23 · 狀態：本人已確認設計

## 目的

本人要求「不能有缺少」。現行萃取段只有結構化欄位（研究類型、資料來源、樣本數、方法、數字）由甲乙雙寫比對；敘述欄位只有甲一人寫，且沒有任何機制檢查「該寫的有沒有寫」——推翻者與引文核對都只驗「寫出來的對不對」。

本設計讓遺漏**可以被偵測**，不宣稱零遺漏。

## 範圍

- 納入：敘述欄位雙寫與比對、章節涵蓋檢查、auditor 補漏。
- 不納入：結果表逐列萃取（本人選擇不做，成本高且 PDF 表格轉文字常錯）、自訂欄位（`custom`）與 `structure` 雙寫。

## 每篇的新流程

| 步 | 誰 | 動作 | 變動 |
|---|---|---|---|
| 1 | 甲、乙 subagent | 甲寫 `a.json`（整張卡片）；乙寫 `b.json`，**改為含結構化欄位＋敘述欄位**（`researchQuestion`、`designNotes`、`findings`、`contributions`、`limitations`、`proposalRelation`） | 修改乙 |
| 2 | `diff_cards.py` | 結構化欄位照舊；敘述欄位以引文位置配對，配不上的列入 `diff.json` | 修改 |
| 3 | judge subagent | 裁決範圍擴大到敘述欄位 | 修改 |
| 4 | `build_card.py` | 套 judge 裁決，合成第一版 `card.json`／`card.md` | 修改 |
| 5 | `coverage_check.py` | 列出被引用 0 次的章節 | 新增 |
| 6 | auditor subagent | 逐章節重讀，寫 `audit.json` | 新增 |
| 7 | `build_card.py` | 併入 `audit.json`，補漏項目標「補漏」 | 修改 |
| 8 | `coverage_check.py` | 驗每節「有項目或有理由」 | 新增 |
| 9 | `quote_check.py`＋repair | 照舊，只修一輪 | 不變 |

## 敘述欄位的配對規則（`diff_cards.py`）

自由文字無法比字面，改以證據位置判斷「是不是同一項」：

- 同一欄位內，甲的一項與乙的一項視為**同一項**，當且僅當：
  1. `page` 相同，且
  2. 兩段 `quote` 經 `textnorm.loosen` 後，一方包含另一方，或最長共同子字串 ≥ 25 個字元（中英文皆適用，不依賴斷詞）。
- 配對是一對一；一項只能配到對方一項（取共同子字串最長者）。
- 配不上的項目寫入 `diff.json`：

```json
{"field": "limitations", "kind": "narrative",
 "onlyA": [{"text": "...", "quote": "...", "page": 9}],
 "onlyB": [{"text": "...", "quote": "...", "page": 10}],
 "detail": "只有甲 1 項；只有乙 1 項"}
```

- 只有一邊有該欄位、或兩邊皆空，依現行規則處理（前者列為不一致，後者略過）。
- 寧可多報：兩邊為同一論點引了不同句子會被列為差異，代價是一次 judge，不會漏。

`proposalRelation` 的配對另加條件：`relation` 相同。`relation` 不同但引文配得上 → 列為不一致，交 judge。

## judge（`judge.md`）

- `diff.json` 每一筆（含敘述欄位）都要有一筆裁決。
- 敘述欄位的裁決：對 `onlyA`、`onlyB` 每一項，回原文判斷收或不收；兩邊都漏的可補。`value` 是**該欄位完整的最終清單**（含已配對成功、由甲提供的項目），格式同現行。
- `build_card.py` 依欄位名決定寫回 `structured` 或 `narrative`。

## 章節涵蓋（`coverage_check.py`，新增）

用法：`uv run scripts/coverage_check.py reviews/<slug>/cards/<key>`

- 讀 `card.json` 的 `structure`（每節 `page`～`endPage`）與所有項目的 `page`（結構化、敘述、`custom`，不含 `structure` 本身）。
- 某項的頁碼落在某節的頁碼範圍內，該節計數 +1；章節範圍重疊時兩節都算。
- 讀 `audit.json`（若存在）的 `sectionReasons`。
- 輸出 `coverage.json`：`{"sections": [{"heading", "page", "endPage", "items": n, "reason": "..."|null}], "uncovered": ["heading", ...]}`；`uncovered` 為 `items == 0` 且無理由的節。
- `uncovered` 非空時 exit code 1（第 8 步據此記例外），stdout 列出各節計數。
- `structure` 為空 → exit code 1，訊息「沒有章節拆解，無法檢查涵蓋」。

## auditor（`auditor.md`，新增）

- 讀：`card.json`、`coverage.json`、`text/<key>.txt`、`card-schema.md`、`protocol.md`。
- 任務：逐章節重讀原文，找出**卡片沒寫到、但屬於某個欄位定義**的內容。不修改、不評論既有項目。
- 對 `coverage.json` 裡 `items == 0` 的每一節，必須二擇一：補出項目，或寫理由。不得留白。
- 寫 `audit.json`：

```json
{"additions": {"limitations": [{"text": "...", "quote": "...", "page": 11}]},
 "sectionReasons": [{"heading": "2.1 Data access", "reason": "只說明資料取得流程，無屬於任何欄位的內容"}]}
```

- `additions` 的欄位名限結構化與敘述欄位（含 `custom.<名稱>`）；項目格式與該欄位相同。
- 回報：`DONE <key>：補漏 <n> 項、無項目章節 <n> 節`。

## 合併補漏（`build_card.py`）

- 存在 `audit.json` 時，把 `additions` 的每一項附上 `"source": "audit"` 後附加到對應欄位尾端（不去重；auditor 被要求不重複既有項目，重複的由 repair 或本人處理）。
- `card.md` 在 `source == "audit"` 的項目後標 `（補漏）`。
- `card.json` 新增 `auditAdded`：補漏項目數。
- 補漏項目同樣受 `missingEvidence` 檢查與 `quote_check.py` 核對。

## 例外與紀錄

- 第 8 步 `coverage_check.py` 仍 exit 1 → 記成例外，列出未涵蓋的節。不重派 auditor。
- `progress.md` 每篇一行改為：`<key>：不一致 <n> 欄（judge 解決 <n>、待裁決 <n>）、補漏 <n> 項、無項目章節 <n> 節、未涵蓋 <n> 節、引文 <通過>/<總數>（寬鬆 <n>）、修 <0|1> 輪`。
- 停 2 摘要第 3 點「驗證數字」加：補漏總數、未涵蓋章節總數。

## 測試（先紅後綠）

- `test_diff_cards.py`：敘述欄位同頁包含配對成功；同頁共同子字串 ≥ 25 配對成功、< 25 不配；不同頁不配；一對一配對取最長；`proposalRelation` 的 `relation` 不同列為不一致；兩邊皆空略過；只有一邊有欄位列為不一致；結構化欄位現有行為不變。
- `test_build_card.py`：judge 裁決敘述欄位寫回 `narrative`；`audit.json` 補漏附 `source` 並出現在 `card.md` 標「（補漏）」；無 `audit.json` 時行為不變；`auditAdded` 計數。
- `test_coverage_check.py`（新）：頁碼落入範圍計數；範圍重疊兩節都算；有理由的 0 項節不列入 `uncovered`；`structure` 為空 exit 1；全涵蓋 exit 0。

## 要改的檔案

- 腳本：`scripts/diff_cards.py`、`scripts/build_card.py`、`scripts/cardschema.py`（若需區分雙寫敘述欄位）、新增 `scripts/coverage_check.py`。
- skill（用 `skill-creator`）：`lit-extract/SKILL.md`、`extractor-structured.md`、`judge.md`、`card-schema.md`、新增 `auditor.md`；`lit-gaps/SKILL.md` 停 2 摘要。

## 成本

每篇從約 2 份全文閱讀＋偶爾 judge，變為約 3 份全文閱讀（auditor 1 份）＋較常 judge（敘述欄位差異多）。
