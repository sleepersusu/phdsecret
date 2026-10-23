# 子專案 5：無提案模式、研究空白、設計選項與文章分類

日期：2026-10-23 · 狀態：本人已確認設計

## 目的

現行流水線假設本人已有提案：停 1 要求提案到位、萃取寫「跟提案的關係」、對照提案段寫缺口。博士生一開始常常只有教授給的論文、還沒有提案。本設計：

1. 加「無提案」模式，從文獻**長出**第一版提案（研究空白 → 設計選項 → 本人選定 → 撰寫）。
2. 每篇論文加文章類型與領域標籤，讓比較表、文獻庫、日後的前端可以分類篩選。

「已有提案」的路徑行為不變。

## 模式

### 決定與記錄

- `/lit-protocol` 第 1 節：看 `proposal/` 底下（不含 `proposal/template/`）有沒有提案檔。
  - 沒有 → 建議「無提案」；有 → 建議「已有提案」。本人確認。
- 寫進 `protocol.md` 新增的 `## 模式` 一節：`模式：已有提案` 或 `模式：無提案`。之後每個階段開工時讀這一行決定分支。
- 模式不是永久的：無提案路徑的終點是第一版提案；本人把它放進 `proposal/` 後，下一批自然走「已有提案」。

### 各階段分支

| 階段 | 已有提案 | 無提案 |
|---|---|---|
| 停 1 | 照舊 | 不要求提案；「提案對照範圍」改問「研究興趣的大方向」；多問「學校或教授有沒有提案範本」，有就請本人放 `proposal/template/`；授權題仍問學校 AI 規範 |
| 萃取 | 照舊 | 甲乙不讀提案，`proposalRelation` 一律 `[]` |
| 參考文獻合併 | 照舊 | 照舊 |
| 對照提案 | `proposal-gaps.md` | 改為研究空白整理 `research-gaps.md` |
| 停 2 | 看缺口 | 看研究空白 → 設計選項 → 本人選定 |
| 撰寫 | 修改提案段落 | 寫第一版提案 |

`extract_text.py` 本來就允許不給 `--proposal`，不用改。`diff_cards.py` 遇到兩邊 `proposalRelation` 皆空會略過（子專案 1 行為），不用改。

## 研究空白整理（無提案模式的對照提案段）

### `scripts/combo_gaps.py`（新增）

用法：`uv run scripts/combo_gaps.py reviews/<slug>`

- 讀所有 `cards/<key>/card.json` 的 `structured.methods` 與 `structured.dataSources`。
- 名稱以 `diff_cards` 既有的正規化規則比對（`casefold` 後去非文字字元），同名視為同一個；顯示名取第一次出現的寫法。
- 寫 `reviews/<slug>/combo-gaps.json`：

```json
{"methods": [{"name": "Transformer", "papers": ["smith2023"]}],
 "dataSources": [{"name": "MIMIC-IV", "papers": ["smith2023", "lee2024"]}],
 "used": [{"method": "Transformer", "dataSource": "MIMIC-IV", "papers": ["smith2023"]}],
 "unused": [{"method": "LSTM", "dataSource": "eICU", "methodPapers": ["lee2024"], "dataPapers": ["kim2022"]}]}
```

- 「用過」：同一篇卡片同時有該方法與該資料來源。
- `unused` 依（方法出現篇數＋資料來源出現篇數）由多到少排序，同分依名稱。
- stdout 摘要：方法數、資料來源數、用過組合數、沒用過組合數。
- 沒有任何 `card.json` → exit 1。

這一步讓「沒人做過的組合」由腳本產生候選，agent 不憑感覺宣稱「沒人做過」。

### `landscape-analyst.md`（新增，`lit-gaps/`）

- 讀：`protocol.md`（研究興趣的大方向）、`matrix.md`、每張 `card.md`、`combo-gaps.json`、`references.csv`。
- 寫 `reviews/<slug>/research-gaps.md`：

```markdown
# 研究空白：<slug>

## 共同做法
- <幾篇都用了什麼方法／資料／指標> "..." [<key>, p.<N>]；"..." [<key2>, p.<M>]

## 作者自承的限制與未來工作
- <限制或建議的下一步；多篇提到同一點時合併> "..." [<key>, p.<N>]

## 論文間的衝突
- <A 怎麼說、B 怎麼說、差在哪；不替任何一邊調和> "..." [<keyA>, p.<N>]；"..." [<keyB>, p.<M>]

## 沒人做過的組合【推論】
- <方法> × <資料來源>：<為什麼可能值得做>。僅代表本批 <n> 篇，需往外查證。方法："..." [<key>, p.<N>]；資料："..." [<key2>, p.<M>]

## 建議補讀
- <refId> <title>（被 <n> 篇引用，不在本批）
```

- 規則：每條至少一則論文引文，格式一字不差（會被 `quote_check.py` 核對）；「沒人做過的組合」只能從 `combo-gaps.json` 的 `unused` 挑，每條方法與資料各附一則引文，必須帶「僅代表本批 <n> 篇，需往外查證」；某類沒有東西寫「- 無」；推論用「可能」標明。
- 回報：`DONE：共同做法 <n>、限制 <n>、衝突 <n>、組合 <n>、建議補讀 <n>`。

### `landscape-refuter.md`（新增）

- 逐條試著推翻 `research-gaps.md`：引文是否真的支持說明、「共同做法」是否真的多篇、「衝突」是否其實是不同設定下的結果、「沒人做過的組合」是否其實有卡片做過（查卡片與原文）。
- 寫 `reviews/<slug>/research-gaps-review.md`，每條一筆：`成立` / `部分推翻（列出撤掉的引文）` / `整條推翻`，附理由。
- 主控照 `lit-gaps` 現有的推翻流程處理：整條推翻與撤掉的引文移到 `research-gaps-rejected.md`（「## 引文核對不過」「## 已撤回」），部分推翻派改寫，最後 `quote_check.py` 必須 0 失敗。只修一輪。

## 停 2：設計選項（無提案模式）

1. 呈現：例外與待裁決、驗證數字、`research-gaps.md` 各類條數與「沒人做過的組合」逐條、建議補讀、標籤歸併摘要（見下）。
2. 派 subagent 讀 `design-options.md`（新增）寫 `reviews/<slug>/design-options.md`：2～3 個方向，每個方向：
   - 一句話題目
   - 研究問題
   - 建立在哪幾篇的什麼做法上（引文）
   - 改進 `research-gaps.md` 的哪幾條（引用條目文字）
   - 需要的資料與方法
   - 風險與可行性疑慮（原文沒寫寫「原文未提及」）
   跑 `quote_check.py`，失敗修一輪。
3. 本人選一個（或要求合併、重提）。用 `grilling` 一次一題追問修正，每題附建議答案。
4. 定案寫 `reviews/<slug>/chosen-direction.md`（題目、研究問題、方法概要、建立在哪些文獻、本人修改的紀錄）；用 `domain-modeling` 在 `docs/adr/` 寫一份 ADR 記錄選擇與捨棄的方向。
5. `state.json` → `draft`，`note`：「方向已定，等撰寫第一版提案」。

## 撰寫第一版提案（`lit-draft`，無提案模式）

- 文件：第一版提案，草稿放 `reviews/<slug>/drafts/proposal-v1/`。
- 章節：`proposal/template/` 有範本就照它；沒有就用：背景、文獻回顧、研究問題、研究方法、預期貢獻、時程。
- 「本人親自寫」除現有四類（研究動機、貢獻聲明、文獻取捨與批判、討論詮釋）外，**加上研究問題與研究方法**。素材：相關卡片與引文、`research-gaps.md` 相關條目、`chosen-direction.md`、這段要回答的 2～3 個問題。
- 寫完提醒本人：把完成的提案放進 `proposal/`，下一批就走「已有提案」。

## 文章分類

### 文章類型 `articleType`

- 加入結構化欄位（`cardschema.STRUCTURED`），比對方式 `enum`，標題「文章類型」。甲乙都寫，不一致交 judge。
- 值只能是：`原始研究`、`個案報告`、`敘述性回顧`、`系統性回顧`、`統合分析`、`範疇回顧`、`研究計畫書`、`評論`、`其他`。
- 格式同 `studyType`：單一物件 `{"value", "quote", "page"}`。判斷系統性回顧等需看方法段（搜尋策略、PRISMA），不只看摘要。
- 比較表因 `STRUCTURED` 自動多一欄。

### 領域標籤 `topics`

- 存在 `card.structured.topics`，清單，每項 `{"value": "<標籤>", "quote", "page"}`。**不加入** `STRUCTURED`（不經 `diff_cards` 比對：自由命名的字面必然不同，硬比只會產生假不一致）。
- 甲乙都寫。`build_card.py` 取聯集：以 `a.json` 的 `topics` 為底，接上 `b.json` 中名稱（以 `diff_cards` 的名稱正規化）不重複的項目。
- 下標規則（寫進 `card-schema.md`）：
  - 只標論文的**主題**：研究對象／族群、疾病或狀態、介入手段、使用的技術、研究情境。順帶提到的詞不標。
  - 證據引文優先取自標題、摘要、研究問題或方法段；只出現在前言或討論的不算。
  - 名稱用原文常用說法或卡片語言皆可，歸併在後面處理。
- `_missing_evidence` 一併檢查 `topics`；`coverage_check` 不計 `topics`（它不是內容摘錄）。

### 標籤字典 `library/tags.json`

```json
{"tags": {
  "失智症": {"synonyms": ["Dementia", "失智"], "source": "agent"},
  "認知障礙": {"synonyms": ["cognitive impairment"], "source": "user"}
}}
```

- 鍵是歸併後的類別名（canonical）；`synonyms` 是會被歸到此類的原始寫法；`source` 為 `agent` 或 `user`（本人建立或改過的）。
- 跨批次累積；本人可以直接編輯（改名、合併、移動同義詞），改過的條目 `source` 設為 `user`。

### 歸併規則（保守）

**只合併完全同一個概念、只是寫法不同的：**翻譯（Dementia ＝ 失智症）、縮寫（AD ＝ Alzheimer's disease ＝ 阿茲海默症）、拼法或單複數（wearable device ＝ wearable devices）。

**不合併：**上下位概念（阿茲海默症 ⊂ 失智症）、相關但不同的概念（認知障礙 ≠ 失智症）。稍有不同就各自成類。

### 歸併流程

1. `tag-normalizer.md`（新增，`lit-extract/`）subagent：讀本批所有 `card.json` 的 `topics` 原始值、`library/tags.json`。對每個**還不在字典裡**（類別名或同義詞皆無，比對經 `casefold`、去頭尾空白）的原始寫法，依保守規則決定：歸入既有類別，或新建類別。寫 `reviews/<slug>/tag-proposals.json`：

```json
{"proposals": [
  {"raw": "Alzheimer's disease", "canonical": "阿茲海默症", "new": true, "reason": "新概念"},
  {"raw": "AD", "canonical": "阿茲海默症", "new": false, "reason": "縮寫"}
]}
```

2. `scripts/merge_tags.py reviews/<slug> [--library library]`（新增）：把提議合併進 `library/tags.json`。
   - 只做新增：新類別（`source: agent`）、或把 `raw` 加進既有類別的 `synonyms`。
   - 拒絕：`raw` 已在字典（任何類別的名或同義詞）、`new: true` 但類別名已存在、`new: false` 但類別不存在、目標類別 `source` 為 `user` 時把 `raw` 加進去（本人管理的類別不由 agent 擴充）。被拒的列在 stdout 與 `reviews/<slug>/tag-merge-report.json`。
   - `library/tags.json` 不存在時建立。
3. `scripts/apply_tags.py reviews/<slug> [--library library]`（新增）：
   - 每篇的原始 `topics` 依字典對到類別名（`casefold` 比對類別名與同義詞）；對不到的保留原字並列入 `unmapped`。
   - 套用 `reviews/<slug>/tag-overrides.json`（可不存在）：`{"<key>": {"add": ["..."], "remove": ["..."]}}`，`remove` 比對類別名，最後執行；本人改單篇用這個檔。
   - 寫 `reviews/<slug>/paper-tags.json`：`{"<key>": {"articleType": "...", "tags": ["失智症", ...], "raw": ["Dementia", ...], "unmapped": [...]}}`；`tags` 去重並依字母序。
   - 卡片本身不改：`card.json` 保留原始標籤與引文（證據），歸併結果只在 `paper-tags.json`。
4. `matrix.py`：`paper-tags.json` 存在時，比較表多一欄「標籤」（以「; 」連接）。
5. 停 2（兩種模式都有）呈現「標籤歸併摘要」：本批新增的類別、被歸進既有類別的寫法、被腳本拒絕的提議、`unmapped`。提醒本人：改類別編輯 `library/tags.json`（改過設 `source: user`），改單篇編輯 `tag-overrides.json`，改完重跑 `apply_tags.py`。

位置：歸併在萃取段收尾（`matrix.py` 之前）：`tag-normalizer` → `merge_tags.py` → `apply_tags.py` → `matrix.py`。

## 要改的檔案

- 新增腳本與測試：`scripts/combo_gaps.py`、`scripts/merge_tags.py`、`scripts/apply_tags.py`。
- 修改腳本與測試：`scripts/cardschema.py`（`articleType`）、`scripts/build_card.py`（`topics` 聯集、渲染、缺引文檢查）、`scripts/matrix.py`（標籤欄）。
- 新增 skill 文件：`lit-gaps/landscape-analyst.md`、`lit-gaps/landscape-refuter.md`、`lit-gaps/design-options.md`、`lit-extract/tag-normalizer.md`。
- 修改 skill：`lit-protocol/SKILL.md`、`lit-protocol/protocol-template.md`、`lit-extract/SKILL.md`、`extractor-full.md`、`extractor-structured.md`、`card-schema.md`、`lit-gaps/SKILL.md`、`lit-draft/SKILL.md`。
- `CLAUDE.md`：流程表下補模式說明；「記憶放檔案」補 `library/tags.json` 可由本人編輯。

## 測試（先紅後綠）

- `test_combo_gaps.py`：用過與沒用過的判定；名稱正規化視為同一個；`unused` 排序；無卡片 exit 1。
- `test_build_card.py`：`topics` 聯集去重（名稱正規化）；`b.json` 無 `topics` 時只用甲的；`topics` 缺引文列入 `missingEvidence`；`card.md` 渲染文章類型與標籤。
- `test_diff_cards.py`：`articleType` 不同列為不一致；`topics` 不同不列為不一致。
- `test_merge_tags.py`：新類別建立；同義詞加入既有 agent 類別；拒絕已存在的 `raw`、`new` 與字典狀態矛盾、加進 `user` 類別；字典不存在時建立；報告檔內容。
- `test_apply_tags.py`：同義詞對到類別（大小寫不敏感）；對不到列 `unmapped`；overrides 的 add 與 remove；remove 在最後；`tags` 去重排序；`articleType` 帶出；卡片不被修改。
- `test_matrix.py`：有 `paper-tags.json` 時多標籤欄；沒有時行為不變；`articleType` 欄出現。
- `test_coverage_check.py`：`topics` 不計入章節涵蓋。
