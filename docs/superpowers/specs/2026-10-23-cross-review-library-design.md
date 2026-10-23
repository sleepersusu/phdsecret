# 子專案 3：跨批次文獻庫

日期：2026-10-23 · 狀態：本人已確認設計

## 目的

現在每批（`reviews/<slug>/`）各自獨立：沒有跨批次的總表，同一篇出現在兩批會重新萃取。本設計加一個**可重建的全域索引**，讓比對跨批次、讀過的論文不重做。

## 架構決定

- 卡片留在原批次，`library/` 只放由腳本從 `reviews/*` 產出的衍生檔，隨時可重建，不是另一份需手動維護的資料。
- 不搬移卡片（避免改動所有腳本路徑、與上游衝突）。
- 沿用舊卡片時**只重做 `proposalRelation`**：它是拿當時版本的提案比對的，提案改過就過時；其餘欄位描述論文本身，不隨提案改變。

## 論文識別（`scripts/paperid.py`，新增）

`canonical_id(raw) -> str | None`：

- DOI：去 `https://doi.org/`、`http://dx.doi.org/`、`doi:` 前綴，去尾端句點，轉小寫 → `10.xxxx/...`。
- arXiv：`arXiv:2301.01234v3`、`arxiv:2301.01234`、`10.48550/arXiv.2301.01234` → 一律 `arxiv:2301.01234`（去版本號）。
- PMID：`PMID: 123`、`pmid:123` → `pmid:123`。
- 空值、`id 待確認` 或無法辨識 → `None`。

`merge_refs.py` 既有的 `_doi`、`_paper_dois` 改用此模組，行為以現有測試為基準不變。

## 建立文獻庫（`scripts/library_build.py`，新增）

用法：`uv run scripts/library_build.py [--reviews reviews] [--out library]`

讀每個 `reviews/<slug>/` 的 `papers.json`、`state.json`、`cards/<key>/card.json`、`refs/*.json`。

產出：

1. `library/index.json`

```json
{"papers": {"10.1000/abc": {
    "title": "...",
    "primary": {"review": "advisor-12", "key": "smith2023"},
    "appearances": [{"review": "advisor-12", "key": "smith2023", "hasCard": true}]
  }},
 "unindexed": [{"review": "advisor-12", "key": "foo", "reason": "id 待確認"}]}
```

   - `primary`：有 `card.json` 的出現處中，所屬批次 `state.json` 的 `updatedAt` 最新者；同時間依 review 名稱字母序。皆無卡片則為 `null`。
2. `library/matrix.md`：每篇一列（取 `primary` 的卡片），欄位同 `matrix.py` 再加「批次」欄（列出所有出現批次）；連結指向 `../reviews/<slug>/cards/<key>/card.md`。沒有卡片的篇不列。
3. `library/references.csv`：合併所有批次的 `refs/*.json`，沿用 `merge_refs.py` 的分組與去重邏輯（以 import 重用，不複製），`citedBy` 改為 `<review>/<key>`，`inCorpus` 改為該篇在 `index.json` 的識別（不在庫中為空）。

stdout 摘要：篇數、跨 2 批以上的篇數、未索引篇數、參考文獻去重後筆數。

## 停 1：比對已讀（`scripts/library_lookup.py`，新增）

用法：`uv run scripts/library_lookup.py reviews/<slug> [--library library]`

- 讀新批次的 `papers.json` 與 `library/index.json`（不存在則視為空庫）。
- 寫 `reviews/<slug>/known.json`：`[{"key": "<新 key>", "id": "...", "source": {"review": "...", "key": "..."}}]`，只收 `primary` 不為 `null` 且 `primary.review` 不是本批的篇。
- `lit-protocol` 盤點第 2 節末執行；停 1 呈現列出「以前讀過、會沿用舊卡片」的篇。

## 萃取段：沿用流程（`lit-extract`）

對 `known.json` 的每篇：

1. 把來源 `card.json` 複製為本批 `cards/<key>/a.json`：`key` 改為新 key，刪除 `pending`、`missingEvidence`、`auditAdded`；`source: "audit"` 標記保留。
2. `uv run scripts/build_card.py` 後跑 `quote_check.py`（以本批 `text/<key>.txt` 核對）：
   - 全部通過 → 同一版本，走沿用。
   - 有失敗 → 版本不同（如預印本 vs 正式版頁碼不同），刪掉複製的檔，改走完整萃取；`progress.md` 記「<key>：舊卡片引文對不上本批 PDF，改完整萃取」。
3. 沿用：甲、乙各自**只重寫 `proposalRelation`**（可查原文），分別寫入 `a.json` 的該欄位與 `b.json`（`{"key", "narrative": {"proposalRelation": [...]}}`）。
4. `uv run scripts/diff_cards.py reviews/<slug>/cards/<key> --fields proposalRelation`；有差異派 judge（只裁 `proposalRelation`）。
5. `build_card.py` → `coverage_check.py` → `quote_check.py`（含 repair 一輪）。不跑 auditor（來源卡片已補漏）。
6. 摘要：複製來源 `summary.md`，跑 `summary_check.py`；不過則派 summarizer 重寫。
7. `progress.md` 每篇一行：`<key>：沿用 <review>/<key>，proposalRelation 不一致 <n>（judge 解決 <n>）、引文 <通過>/<總數>`。

## `diff_cards.py --fields`（修改）

- `--fields a,b,...`：只比對列出的欄位（結構化或敘述欄位名皆可）；未指定時行為不變。
- 指定欄位以外、只出現在一邊的欄位不列為不一致。

## 流程與 skill 改動（用 `skill-creator`）

- `lit-protocol/SKILL.md`：盤點加 `library_lookup.py`；停 1 呈現加已讀清單。
- `lit-extract/SKILL.md`：加「沿用流程」一節；新增 `extractor-relation.md`（甲乙共用，只寫 `proposalRelation`）。
- `lit-gaps/SKILL.md`：停 2 呈現前執行 `library_build.py`，呈現加 `library/matrix.md` 位置與跨批次篇數。
- `CLAUDE.md` 的流程段補一句 `library/` 是衍生檔、可重建。

## 測試（先紅後綠）

- `test_paperid.py`：DOI 各前綴與大小寫；尾端句點；arXiv 版本號與 10.48550 DOI 等價；PMID；`id 待確認` 與空值回 `None`。
- `test_merge_refs.py`：既有測試全綠（重構不改行為）。
- `test_library_build.py`：兩批同一 DOI 合為一篇；`primary` 取 `updatedAt` 新者；同時間依名稱；無卡片 `primary` 為 `null` 且不進 matrix；`id 待確認` 進 `unindexed`；參考文獻跨批去重、`citedBy` 為 `review/key`。
- `test_library_lookup.py`：命中寫入 `known.json`；`primary` 是本批不算；空庫產出空清單；無 `index.json` 視為空庫。
- `test_diff_cards.py`：`--fields proposalRelation` 只比該欄；結構化欄位只有一邊有時不報；未指定時行為不變。

## 要改的檔案

- 新增：`scripts/paperid.py`、`scripts/library_build.py`、`scripts/library_lookup.py`、對應測試、`lit-extract/extractor-relation.md`。
- 修改：`scripts/merge_refs.py`、`scripts/diff_cards.py`、`lit-protocol/SKILL.md`、`lit-extract/SKILL.md`、`lit-gaps/SKILL.md`、`CLAUDE.md`。
