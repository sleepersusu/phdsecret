---
name: lit-extract
description: 流水線的萃取段（自動）：每篇論文派兩個 subagent 各自萃取（甲寫整張卡片，乙寫結構化與敘述欄位），腳本比對不一致才派 judge，合成第一版卡片後做章節涵蓋檢查、派 auditor 逐章節補漏，再逐則核對引文，每篇另寫一段精簡摘要（summary_check 核對來源標記），最後產出比較矩陣，接著自動進入 lit-refs。reviews/<slug>/state.json 的 stage 是 auto:extract，或使用者說「開始萃取」「讀卡片」時使用。
---

# lit-extract（萃取）

你是主控：只派工、跑腳本、看結果，不自己讀論文全文，也不自己寫卡片內容。自動段不問本人，例外記下來，到停 2 一次呈現。

## 0. 開工檢查

照 `CLAUDE.md`「開工檢查」的「萃取」列。

## 1. 準備

1. 讀 `reviews/<slug>/state.json`、`progress.md`、`protocol.md`、`papers.json`。`protocol.md` 的「執行設定」寫了甲乙用哪個模型、一次處理幾篇。
2. 讀 `protocol.md` 的「模式」。已有提案：`uv run scripts/extract_text.py reviews/<slug> --proposal <protocol.md 記的提案檔>`；無提案：`uv run scripts/extract_text.py reviews/<slug>`（不給 `--proposal`）。
3. 找出還沒完成的篇：`papers.json` 裡的每篇，只有 `progress.md` 已有該 `<key>` 的每篇一行（第 2 節最後才寫），或已記成例外，才算完成；其餘都要重做。不能用 `card.md` 是否存在判斷，因為第 2 節第 3 步就會產出第一版 `card.md`，那時 auditor 還沒跑。重做前先刪掉 `cards/<key>/` 裡所有產生的檔案：`a.json`、`b.json`、`diff.json`、`judge.json`、`audit.json`、`coverage.json`、`card.json`、`card.md`、`summary.md`，讓甲乙從頭來，避免舊檔被併進新結果。這些是流水線的產出，不是本人的檔案；不碰 `pdfs/` 與 `text/`。
4. 讀 `reviews/<slug>/known.json`（不存在就當空清單）。列在裡面的篇走第 2b 節沿用流程，其餘走第 2 節。兩者都以 `progress.md` 的每篇一行作為「已完成」的判準。

## 2. 每篇的流程

一次處理「執行設定」指定的篇數，篇與篇之間平行。每篇：

1. **同時**派兩個 general-purpose subagent，彼此不知道對方的存在：
   - 甲（`model` 用執行設定的甲模型）：prompt 為「讀 `.claude/skills/lit-extract/extractor-full.md` 照做。slug：`<slug>`，key：`<key>`。」
   - 乙（`model` 用執行設定的乙模型）：prompt 為「讀 `.claude/skills/lit-extract/extractor-structured.md` 照做。slug：`<slug>`，key：`<key>`。」
   - 指定的模型不能用時，改用預設模型，記進 `progress.md`。
   - 回 `BLOCKED` → 記成例外，這篇跳過。
2. `uv run scripts/diff_cards.py reviews/<slug>/cards/<key>`（結構化與敘述欄位都比）。有不一致 → 派 judge subagent（`model` 用甲模型）：「讀 `.claude/skills/lit-extract/judge.md` 照做。slug：`<slug>`，key：`<key>`。」
3. `uv run scripts/build_card.py reviews/<slug>/cards/<key>`（第一版卡片）。
4. `uv run scripts/coverage_check.py reviews/<slug>/cards/<key>`。這一步 exit 1 是正常的，只是產出 `coverage.json` 給 auditor。
5. 派 auditor subagent（`model` 用甲模型）：「讀 `.claude/skills/lit-extract/auditor.md` 照做。slug：`<slug>`，key：`<key>`。」回 `BLOCKED` → 記成例外，跳過第 6、7 步。
6. `uv run scripts/build_card.py reviews/<slug>/cards/<key>`（併入補漏）。失敗（例如 `audit.json` 格式錯誤）→ 記成例外（auditor 產出無法併入），刪掉 `audit.json`，重跑 build_card 以第一版卡片繼續第 7、8 步。
7. `uv run scripts/coverage_check.py reviews/<slug>/cards/<key>`。仍 exit 1 → 記成例外，列出未涵蓋的節；不重派 auditor。若輸出是「沒有章節拆解」，例外寫「沒有章節拆解，無法檢查涵蓋」，不要寫成未涵蓋幾節。
8. `uv run scripts/quote_check.py reviews/<slug> reviews/<slug>/cards/<key>/card.md`。
9. 第 8 步有失敗、或 `card.json` 的 `missingEvidence` 不是空的 → 派一個 subagent 修，prompt 附上失敗輸出與 `missingEvidence`：「讀 `.claude/skills/lit-extract/repair.md` 照做。slug：`<slug>`，key：`<key>`。失敗清單：…」。修完重跑第 6、7、8 步。**只修一輪**，還是不過就記成例外。
10. 派 summarizer subagent（`model` 用乙模型）：「讀 `.claude/skills/lit-extract/summarizer.md` 照做。slug：`<slug>`，key：`<key>`。」接著 `uv run scripts/summary_check.py reviews/<slug>/cards/<key>`。exit 1 → 對同一個 subagent 用 SendMessage 附上輸出請它修，修完再跑一次。**只修一輪**，還是不過就記成例外。第 9 步修過卡片的，摘要在修完之後才寫。

每篇做完，在 `progress.md` 追加一行：`<key>：不一致 <n> 欄（judge 解決 <n>、待裁決 <n>）、補漏 <n> 項、無項目章節 <n> 節、未涵蓋 <n> 節、引文 <通過數>/<總數>（寬鬆 <n>）、修 <0 或 1> 輪、摘要 <通過／例外>`。補漏數取 `card.json` 的 `auditAdded`；無項目章節與未涵蓋數取 `coverage.json`。

## 2b. 沿用舊卡片（`known.json` 列的篇）

以前在別批做過、文獻庫裡有卡片的篇，不重新萃取。每篇：

1. 先照第 1 節第 3 點清掉 `cards/<key>/` 裡舊的產出（若有），避免舊的 b.json、diff.json、judge.json 被併進沿用的卡片。`uv run scripts/reuse_card.py reviews/<slug> <key> --source <source.review>/<source.key>`；`protocol.md` 的模式是「無提案」時加 `--clear-relation`。
2. `uv run scripts/build_card.py reviews/<slug>/cards/<key>`，再 `uv run scripts/quote_check.py reviews/<slug> reviews/<slug>/cards/<key>/card.md`（用本批的 PDF 文字核對）。有失敗代表 PDF 版本不同（例：預印本對正式版，頁碼不同）：照第 1 節第 3 點刪掉 `cards/<key>/` 產生的檔案，改走第 2 節完整萃取，`progress.md` 記「<key>：舊卡片引文對不上本批 PDF，改完整萃取」。
3. 已有提案模式：**同時**派兩個 general-purpose subagent，彼此不知道對方的存在：甲（甲模型）「讀 `.claude/skills/lit-extract/extractor-relation.md` 照做。slug：`<slug>`，key：`<key>`，角色：甲。」；乙（乙模型）同一句，角色：乙。接著 `uv run scripts/diff_cards.py reviews/<slug>/cards/<key> --fields proposalRelation`，有不一致照第 2 節第 2 步派 judge。無提案模式跳過這一步。
4. `uv run scripts/build_card.py reviews/<slug>/cards/<key>`；`uv run scripts/coverage_check.py reviews/<slug>/cards/<key>`（exit 1 記成例外，同第 2 節第 7 步）；`uv run scripts/quote_check.py reviews/<slug> reviews/<slug>/cards/<key>/card.md`，失敗照第 2 節第 9 步修一輪。不派 auditor：來源卡片已補過漏。
5. `uv run scripts/summary_check.py reviews/<slug>/cards/<key>`。沒有摘要或不通過（例：跟提案的關係改了，標記對不上）→ 照第 2 節第 10 步派 summarizer 重寫，修一輪。
6. `progress.md` 追加一行：`<key>：沿用 <source.review>/<source.key>、proposalRelation 不一致 <n>（judge 解決 <n>；無提案寫「清空」）、引文 <通過數>/<總數>、修 <0 或 1> 輪、摘要 <沿用／重寫／例外>`。

## 3. 收尾

1. 標籤歸併：
   1. 先刪掉舊的 `reviews/<slug>/tag-proposals.json`（重跑時才會重新產生，不然舊提議會全部回「這個寫法已在字典裡」）。派 tag-normalizer subagent（`model` 用乙模型）：「讀 `.claude/skills/lit-extract/tag-normalizer.md` 照做。slug：`<slug>`。」回 `BLOCKED` → 記成例外，跳過本點第 2 小步（merge_tags），仍跑第 3 小步（apply_tags 用現有字典）。
   2. `uv run scripts/merge_tags.py reviews/<slug>`。被拒絕的提議會列在 `tag-merge-report.json`，到停 2 呈現，不重派。
   3. `uv run scripts/apply_tags.py reviews/<slug>`。
   - merge_tags 或 apply_tags exit 非 0 → 記成例外，繼續下一點（matrix）。
   - `progress.md` 追加一行標籤歸併數字：提議 <n>、接受 <n>、拒絕 <n>、unmapped <n>（取自 `tag-merge-report.json` 與 `paper-tags.json`）。
2. `uv run scripts/matrix.py reviews/<slug>`。
3. 對每張卡片再跑一次 `quote_check.py`，數字寫進 `progress.md`。
4. 例外（BLOCKED、修過仍不過、待本人裁決的欄位、章節未涵蓋）整理成一段，追加到 `progress.md` 的「例外」小節。
5. `state.json` 改成 `auto:refs`，`note` 寫「萃取完成，<n> 篇、例外 <n>」，接著執行 `/lit-refs`。
