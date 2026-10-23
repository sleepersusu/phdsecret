---
name: lit-protocol
description: 流水線的停 1：開一個新的文獻 review（例：教授給的 12 篇），盤點 PDF 與提案，跟本人逐題定下研究方向、卡片欄位、要對照的提案章節與授權，產出 reviews/<slug>/protocol.md 與 state.json。使用者說「開新的 review」「停 1」「定方向」「開始讀這批 paper」或打 /lit-protocol 時使用；reviews/<slug>/state.json 的 stage 是 stop1 時也用它接續。
---

# lit-protocol（停 1：定方向）

本人在場的階段。產出 `protocol.md`，讓之後的自動段不必再問本人。

## 0. 開工檢查

照 `CLAUDE.md`「開工檢查」的「停 1」列。

## 1. 定位

1. 問 review 的名稱，用小寫 kebab-case（例：`advisor-12`）。
2. `reviews/<slug>/state.json` 已存在 → 讀它與 `progress.md`，從中斷處接續。
3. 建 `reviews/<slug>/pdfs/`，請本人把 PDF 放進去。PDF 到位才往下。
4. 決定模式：看 `proposal/` 底下（不含 `proposal/template/`）有沒有提案檔。有 → 建議「已有提案」；沒有 → 建議「無提案」。問本人確認，記下來，第 4 節寫進 `protocol.md` 的「模式」。無提案模式不要求提案。
5. PDF 檔名去掉副檔名就是這篇的 key，之後卡片、引文都用它（例：`[smith2023, p.6]`）。檔名含空白、逗號或方括號時，請本人改成簡短的英數檔名（例：`smith2023.pdf`）；你不要自己改 `pdfs/` 裡的檔案。

## 2. 盤點（不問本人，自己做完）

1. `uv run scripts/inventory.py reviews/<slug>` → 產出 `inventory.json` 並印出表格。
2. 狀態不是「可讀」的檔案記成例外，第 4 步一次告訴本人。
3. 已有提案：`uv run scripts/extract_text.py reviews/<slug> --proposal proposal/<提案檔>`；無提案：`uv run scripts/extract_text.py reviews/<slug>`。論文（與提案）的純文字放進 `text/`。提案格式不支援時，請本人另存成 .docx、.pdf 或 .md。
4. 確認每篇的 id：盤點抓到的 DOI、arXiv ID 只是候選，前兩頁也可能出現別篇的 DOI。讀 `text/<key>.txt` 第一頁取得標題與作者，再查 `https://doi.org/<doi>` 或 `https://arxiv.org/abs/<id>`，標題相符才算確認；沒有候選就用標題查（有 `paper-lookup` 就用它）。確認不了的標「id 待確認」。
5. 寫 `reviews/<slug>/papers.json`：`[{"key": "...", "id": "DOI 或 arXiv:xxxx.xxxxx", "title": "..."}]`，只收可讀的篇。寫完跑 `uv run scripts/library_lookup.py reviews/<slug>`，以前在別批讀過的篇會列進 `known.json`。
6. 已有提案模式：讀 `text/proposal.txt`，列出章節標題，每節寫一句大意。無提案模式跳過。

## 3. 逐題定案

同時用 `grilling` 與 `domain-modeling`：一次問一題，每題附你的建議答案。名詞定下來就寫進 `CONTEXT.md`；難以回頭又有取捨的決定才寫 ADR。已經有答案的題目跳過。

1. **研究方向**：一兩句話說想研究什麼。
2. **來源與用途**：這批文獻從哪來、要交什麼給誰、期限。
3. **卡片語言**：引文一律保留原文；說明用中文還是英文。
4. **卡片欄位**：照 `protocol-template.md` 的核心欄位逐一確認，問要不要加欄位。研究類型對得上時，問要不要加掛 CHARMS（預測模型）、CONSORT-AI（AI 介入試驗）或 TRIPOD+AI（預測模型報告完整度）。
5. **提案對照範圍**（已有提案）：列出第 2 步的章節，請本人選要對照哪幾節。
   **研究興趣與範本**（無提案）：一兩句話說大方向（研究空白整理會依此聚焦）；問學校或教授有沒有提案範本，有就請本人放進 `proposal/template/`，記下檔名，沒有就記「用標準結構」。
6. **授權與規範**：提案是不是本人寫的、同不同意在這條流水線（本機與 Claude）處理；學校或指導教授對 AI 使用有沒有規範。撰寫階段的 `scientific-writing`、`peer-review` 處理未發表的稿子前會確認授權，現在先記下來，到時才不會卡住。無提案模式沒有提案要授權，只問學校或指導教授的 AI 使用規範。
7. **執行設定**：照範本的預設（甲 opus、乙 sonnet、一次 3 篇）問本人要不要改。方案用量有限時可以降成一次 1–2 篇，或甲乙都用 sonnet（兩邊一起漏的風險會變高）。

## 4. 寫檔與確認

1. 照 `protocol-template.md` 寫 `reviews/<slug>/protocol.md`。
2. 寫 `state.json`：`stage` 為 `stop1`，`note` 寫「停 1：protocol 備妥，等本人確認」。
3. `progress.md` 追加一筆：盤點數字、例外、定案的事。
4. 一次呈現：模式、篇數與盤點結果（例外列最前面）、以前讀過會沿用舊卡片的篇（`known.json`）、研究方向、卡片欄位、提案對照範圍、授權紀錄。問「可以開始萃取嗎」。
5. 本人點頭 → `state.json` 的 `stage` 改成 `auto:extract`，接著執行 `/lit-extract`。之後萃取、參考文獻合併、對照提案會自動一路跑完，到停 2 才再找本人。
