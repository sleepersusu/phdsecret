---
name: lit-gaps
description: 流水線的對照提案段（自動）＋停 2：派 subagent 把提案逐節對照所有卡片寫出缺口清單，核對引文，再派另一個 subagent 試著推翻每一條，最後把整段自動流程的成果與例外一次呈現給本人。state.json 的 stage 是 auto:gaps 或 stop2，或使用者說「對照提案」「看缺口」時使用。
---

# lit-gaps（對照提案 → 停 2）

你是主控：只派工、跑腳本、看結果。

## 0. 開工檢查

照 `CLAUDE.md`「開工檢查」的「對照提案」列。

## 1. 寫缺口清單

先讀 `protocol.md` 的「模式」：**無提案** → 跳過第 1～3 節，改走第 4、5 節。

1. 讀 `state.json`、`progress.md`、`protocol.md`。
2. `uv run scripts/matrix.py reviews/<slug>`（確保矩陣是最新的）。
3. 派一個 general-purpose subagent（`model` 用甲模型）：「讀 `.claude/skills/lit-gaps/gap-analyst.md` 照做。slug：`<slug>`。」
4. `uv run scripts/quote_check.py reviews/<slug> reviews/<slug>/proposal-gaps.md`。有失敗 → 對同一個 subagent 用 SendMessage 附上失敗輸出請它修，修完再跑一次。**只修一輪**，還是不過的條目從 `proposal-gaps.md` 移到 `proposal-gaps-rejected.md` 的「## 引文核對不過」小節，保留原文與失敗原因。

## 2. 試著推翻

1. 派另一個 general-purpose subagent（`model` 用乙模型）：「讀 `.claude/skills/lit-gaps/gap-refuter.md` 照做。slug：`<slug>`。」
2. 讀 `gaps-review.md`，檢查條數不等於 `proposal-gaps.md` 的條數時，用 SendMessage 請它補查漏掉的。推翻的內容移到 `proposal-gaps-rejected.md` 的「## 已撤回」小節，附上推翻理由，不要直接刪掉：
   - 範圍是整條：整條移過去。
   - 範圍是部分引文：只把那幾則引文移過去，條目留在 `proposal-gaps.md`。
3. 有部分推翻的條目時，派一個 general-purpose subagent（`model` 用甲模型）：「讀 `reviews/<slug>/gaps-review.md` 與 `proposal-gaps-rejected.md`，把 `proposal-gaps.md` 裡被撤掉部分引文的條目改寫成只講剩下引文撐得住的；不新增引文，不動其他條目。slug：`<slug>`。」
4. 再跑一次 `quote_check.py`，必須 0 失敗；數字寫進 `progress.md`。

## 3. 停 2（本人在場）

`state.json` 改成 `stop2`，`note` 寫「停 2：缺口清單備妥，等本人看」。一次呈現，依序：

1. 一句話：幾篇、幾張卡片、幾條缺口（有支撐、已有人做過、沒提到、衝突各幾條）。
2. **例外與待裁決**（列在最前面）：`progress.md` 的例外、卡片的「待本人裁決」欄位、章節未涵蓋的篇、`references.csv` 的模糊合併筆數、BibTeX 失敗的篇、`tag-merge-report.json` 被拒絕的標籤提議。
3. 驗證數字：卡片引文通過數／總數、補漏總數（各卡 `auditAdded` 加總）、未涵蓋章節總數、缺口清單引文通過數／總數、整條撤回幾條、撤掉部分引文幾條。
4. 檔案位置：`matrix.md`、`proposal-gaps.md`、`references.csv`、`cards/`。
5. 「提案沒提到」與「建議補讀」逐條列出（這兩類最可能改變提案）。
6. 標籤歸併摘要：本批新增的類別、被歸進既有類別的寫法（看 `tag-merge-report.json` 的 `accepted`）、被拒絕的提議、`paper-tags.json` 的 `unmapped`。提醒本人：改類別編輯 `library/tags.json`（改過的設 `"source": "user"`），改單篇編輯 `reviews/<slug>/tag-overrides.json`，改完重跑 `uv run scripts/apply_tags.py reviews/<slug>` 與 `matrix.py`。

最後一句：「看完要開始寫，打 `/lit-draft`；看不懂某個方法，打 `/teach <想弄懂的東西>`。」

## 4. 研究空白整理（無提案模式，自動）

接續時，輸出檔已存在且 `progress.md` 已記錄的步驟跳過，不重做（例：`research-gaps-review.md` 已處理完就跳過本節的推翻步驟）。

1. 讀 `state.json`、`progress.md`、`protocol.md`。
2. `uv run scripts/matrix.py reviews/<slug>`；`uv run scripts/combo_gaps.py reviews/<slug>`。
3. 派 general-purpose subagent（`model` 用甲模型）：「讀 `.claude/skills/lit-gaps/landscape-analyst.md` 照做。slug：`<slug>`。」
4. `uv run scripts/quote_check.py reviews/<slug> reviews/<slug>/research-gaps.md`。有失敗 → 對同一個 subagent 用 SendMessage 附上失敗輸出請它修，修完再跑一次。**只修一輪**，還是不過的條目移到 `research-gaps-rejected.md` 的「## 引文核對不過」小節，保留原文與失敗原因。
5. 派另一個 general-purpose subagent（`model` 用乙模型）：「讀 `.claude/skills/lit-gaps/landscape-refuter.md` 照做。slug：`<slug>`。」讀 `research-gaps-review.md`，條數不符時請它補查。推翻的移到 `research-gaps-rejected.md` 的「## 已撤回」小節並附理由：整條推翻整條移、部分推翻只移那幾則引文。有部分推翻時，派甲模型 subagent 把那些條目改寫成只講剩下引文撐得住的，不新增引文、不動其他條目。
6. 再跑一次 `quote_check.py`，必須 0 失敗；數字寫進 `progress.md`。

## 5. 停 2：研究空白與設計選項（無提案模式，本人在場）

開始前確認這個 session 可用 `grilling` 與 `domain-modeling`（名稱只看冒號後面）；缺了就停下來，照 `CLAUDE.md`「開工檢查」的安裝指令列出缺哪些、貼出指令，等本人裝好、重開 Claude Code 再繼續。

接續時，輸出檔已存在且 `progress.md` 已記錄的步驟跳過，不重做（例：`design-options.md` 已存在就跳過第 2 步）。

`state.json` 改成 `stop2`，`note` 寫「停 2：研究空白備妥，等本人看」。

1. 一次呈現：一句話（幾篇、幾張卡片、研究空白各類幾條）；例外與待裁決（同第 3 節第 2 點）；驗證數字（卡片引文、補漏總數、未涵蓋章節、研究空白引文通過數、撤回條數）；檔案位置（`matrix.md`、`research-gaps.md`、`references.csv`、`cards/`）；「沒人做過的組合」與「建議補讀」逐條；標籤歸併摘要（同第 3 節第 6 點）。
2. 派 general-purpose subagent（`model` 用甲模型）：「讀 `.claude/skills/lit-gaps/design-options.md` 照做。slug：`<slug>`。」跑 `quote_check.py reviews/<slug> reviews/<slug>/design-options.md`，失敗修一輪，仍不過的那一點標「⚠ 引文未核對通過」。
3. 把 2～3 個方向呈現給本人，請本人選一個，或要求合併、重提。
4. 用 `grilling` 一次一題追問選定的方向（研究問題夠不夠具體、資料拿不拿得到、跟既有研究差在哪、做得完嗎），每題附建議答案，依本人的回答修正。
5. 定案寫 `reviews/<slug>/chosen-direction.md`：題目、研究問題、方法概要、建立在哪些文獻（附引文）、本人修改的紀錄。用 `domain-modeling` 在 `docs/adr/` 寫一份 ADR：選了哪個方向、捨棄了哪些、為什麼。
6. `state.json` 的 `stage` 設為 `draft`，`note` 寫「方向已定，等撰寫第一版提案」。最後一句：「要開始寫第一版提案，打 `/lit-draft`；看不懂某個方法，打 `/teach <想弄懂的東西>`。」
