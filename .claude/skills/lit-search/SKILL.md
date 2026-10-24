---
name: lit-search
description: 流水線的停 0：從研究問題出發找文獻。跟本人定搜尋條件，派 subagent 三路搜尋（關鍵字、往回追、往前追）、雙人篩選，產出候選清單與 RIS；本人匯入 Zotero 抓 PDF 後，腳本把 PDF 讀回 reviews/<slug>/pdfs/，接著進停 1。使用者說「找文獻」「搜尋論文」「停 0」或打 /lit-search 時使用；reviews/<slug>/state.json 的 stage 是 stop0 時也用它接續。
---

# lit-search（停 0：找文獻）

本人在場的階段，中間的搜尋與篩選自動跑。產出候選清單與 PDF，接著交給 `/lit-protocol`。

## 0. 開工檢查

照 `CLAUDE.md`「開工檢查」的「停 0」列。

## 1. 定位

1. 問這批的名稱，小寫 kebab-case（例：`dementia-wearables`）。之後 Zotero 的資料夾也用這個名稱。
2. `reviews/<slug>/state.json` 已存在 → 讀它與 `progress.md`，從中斷處接續；輸出檔已存在且 `progress.md` 已記錄的步驟跳過。
3. 建 `reviews/<slug>/search/`；寫 `state.json`：`stage` 為 `stop0`，`note`「停 0：定搜尋條件」。

## 2. 定搜尋條件（本人在場）

用 `grilling`：一次問一題、附建議答案，已答的跳過。

1. 研究問題（一兩句）。`proposal/` 沒有提案時，這也是之後無提案模式的研究興趣。
2. 納入條件，編號 I1、I2⋯。
3. 排除條件，編號 E1、E2⋯。
4. 年份範圍、語言。
5. 預計篇數（篩選後大概要幾篇）。

寫 `reviews/<slug>/search/search-protocol.md`（以上各題，條件保留編號）。

## 3. 三路搜尋（自動）

三個 general-purpose subagent 平行（`model` 用 sonnet）：

- 「讀 `.claude/skills/lit-search/search-keyword.md` 照做。slug：`<slug>`。」
- 「讀 `.claude/skills/lit-search/search-backward.md` 照做。slug：`<slug>`。」（`library/references.csv` 不存在就不派，記一句「文獻庫尚未建立，略過往回追」）
- 「讀 `.claude/skills/lit-search/search-forward.md` 照做。slug：`<slug>`。」（`library/index.json` 不存在就不派，同上）

回 `BLOCKED` 的路記成例外，其餘照常。

## 4. 合併與篩選（自動）

1. `uv run scripts/search_merge.py reviews/<slug>`。
2. **同時**派兩個 general-purpose subagent，彼此不知道對方：甲（opus）「讀 `.claude/skills/lit-search/screener.md` 照做。slug：`<slug>`，角色：甲。」；乙（sonnet）同一句，角色：乙。
3. `uv run scripts/screen_compare.py reviews/<slug>`。
4. `progress.md` 追加：各路命中數、`flow.json` 的數字、例外。

## 5. 停 0 呈現（本人在場）

`state.json` 的 `note` 改「停 0：候選清單備妥，等本人決定」。一次呈現：

1. 各路命中數；`search/queries.json` 每條搜尋式（資料庫、日期、命中數）。
2. `search/flow.json` 的流程數字。
3. `status` 為 `toUser` 的篇逐條：標題、年份、甲乙各自的判斷、依據條件與理由。請本人逐篇決定收或不收。
4. `pool.json` 的 `noId` 清單（沒有 DOI／PMID／arXiv ID 的，本人可手動補 id 後重跑第 4 節）。

本人決定後：寫 `search/final.ris`（`included` ＋ 本人收下的 `toUser`，格式同 `candidates.ris`，可從它擷取）；`progress.md` 追加本人的決定與最終篇數。

接著請本人在 Zotero：建立名稱為 `<slug>` 的資料夾 → 匯入 `final.ris` 到這個資料夾 → 全選 →「尋找可用的 PDF」→ 完成後告訴你。

## 6. 讀回 PDF

1. `uv run scripts/zotero_pull.py reviews/<slug> --collection <slug>`。連不上或找不到資料夾時，把腳本的訊息轉告本人，等本人處理後重跑。
2. 呈現 `search/zotero-pull.json`：複製了幾篇；`noPdf`（請本人在 Zotero 手動找 PDF，或從學校圖書館下載後拖進該條目）；`noMetadata`（請本人對它按右鍵 →「擷取 PDF 的中繼資料」）；`skipped`（`pdfs/` 已有同名檔，沒有覆蓋）。本人處理後可重跑第 1 步，已複製的不會重複。`zotero_pull.py` 從不覆蓋 `pdfs/` 裡已有的檔；若複製中途失敗（少見，腳本會中止並報錯），請本人自己刪掉 `pdfs/` 裡那一個不完整的檔再重跑（流水線不刪 `pdfs/` 的檔）。
3. `state.json` 改 `stop1`，`note`「PDF 已就緒 <n> 篇、缺 PDF <n> 篇」；`progress.md` 追加數字。接著執行 `/lit-protocol`。
