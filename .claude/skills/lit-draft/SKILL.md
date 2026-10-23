---
name: lit-draft
description: 流水線的撰寫段：依 doc-coauthoring 的流程跟本人一節一節寫，先把段落分成「agent 起草」與「本人親自寫」兩類（本人段落只給素材不給成稿），起草時每個關於文獻的主張都附可核對的引文，寫完每節跑引文核對、peer-review 與無上下文讀者測試。使用者說「開始寫」「寫第一段」「寫 Background」或打 /lit-draft 時使用。
---

# lit-draft（撰寫）

本人在場的階段。草稿放 `reviews/<slug>/drafts/<文件名>/`，不改 `proposal/` 的原稿。

## 0. 開工檢查

照 `CLAUDE.md`「開工檢查」的「撰寫」列。另外確認 `protocol.md`「授權與規範」已記本人同意處理提案；沒有記就先問本人，記下來再往下。`scientific-writing`、`peer-review` 要求確認授權時，以這筆紀錄回答。

## 1. 收集脈絡（照 doc-coauthoring 第一階段）

一次問一題、附建議答案，已經知道的跳過：

1. 這次寫什麼文件、哪幾節（例：提案的 Background、文獻回顧章）。`protocol.md` 的模式是「無提案」時，預設文件是**第一版提案**，草稿放 `drafts/proposal-v1/`；章節依 `protocol.md` 記的提案範本，沒有範本就用：背景、文獻回顧、研究問題、研究方法、預期貢獻、時程。
2. 讀者是誰（指導教授、審查委員、期刊）。
3. 語言、字數、引用格式。
4. 學校或指導教授對 AI 使用的規範（`protocol.md` 有記就沿用）。

## 2. 段落規劃

寫 `drafts/<文件名>/outline.md`：每一節列出段落，每段一句話說要講什麼，並分類：

- **agent 起草**：整理文獻、描述既有方法與結果、比較各篇的研究設計。
- **本人親自寫**：價值在本人自己的判斷的段落，至少包括：
  1. 研究動機：為什麼是這個題目、為什麼是現在。
  2. 貢獻聲明：本人的研究跟這批文獻差在哪裡。
  3. 文獻的取捨與批判：為什麼採信這篇、不採那篇。
  4. 討論裡的詮釋：結果代表什麼。
  5. 無提案模式另加：研究問題、研究方法。這兩段是本人的研究設計判斷。

本人段落只給素材，不給成稿：相關卡片與引文、`proposal-gaps.md`（已有提案）或 `research-gaps.md` 與 `chosen-direction.md`（無提案）裡相關的條目、這段要回答的 2～3 個問題。

把 outline 給本人看，確認分類後才開始起草。

## 3. 起草（照 doc-coauthoring 第二階段，一節一節來）

每一節：

1. 依 `scientific-writing` 的規則寫：不編造證據、不隱藏不確定性、作者對內容負責。
2. 只能引用本批有卡片的論文。每個關於文獻的主張，句尾用 `[@<key>]` 引用（citekey 對應 `papers.bib`），並在同一行後面附證據註解：

   ```markdown
   The model reached an AUROC of 0.89 on internal data [@smith2023].<!-- "achieved an AUROC of 0.89 on the internal test set" [smith2023, p.6] -->
   ```

   證據引文從卡片或 `text/<key>.txt` 逐字照抄，不含雙引號與換行。
3. 存成 `drafts/<文件名>/<兩位數序號>-<節名>.md`。
4. `uv run scripts/quote_check.py reviews/<slug> <這一節的檔案> --require-evidence`，必須 0 失敗（有 `[@key]` 卻沒附證據的行也算失敗）。
5. 派一個 general-purpose subagent 用 `peer-review` 審這一節（授權依 `protocol.md`），結果存 `drafts/<文件名>/<序號>-<節名>.review.md`。
6. 派另一個 general-purpose subagent 當沒有上下文的讀者（doc-coauthoring 第三階段）：只給它這一節的檔案，請它列出讀不懂、跳太快、缺定義的地方。
7. 依 5、6 修改後，重跑第 4 步，再把這一節給本人看。本人有意見就改，改完重跑第 4 步。

`humanizer` 只在本人要求時用來調整文風，不用來掩蓋 AI 的使用。

## 4. 收尾

1. `progress.md` 追加：寫了哪幾節、字數、引文核對結果、peer-review 主要意見與處理方式。
2. `state.json` 的 `stage` 設為 `draft`，`note` 寫目前寫到哪一節。
3. 告訴本人交稿前要做的事：刪掉 `<!-- -->` 證據註解；用 `papers.bib` 產生參考文獻列表（例如 `pandoc --citeproc --bibliography reviews/<slug>/papers.bib`）；本人段落由本人完成；依學校規範決定是否揭露 AI 的使用。無提案模式：提醒本人把完成的提案放進 `proposal/`，下一批論文就會自動走「已有提案」模式。
