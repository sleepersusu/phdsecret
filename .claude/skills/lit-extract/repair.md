# 修引文

一張卡片有幾則引文核對不過（在原文那一頁找不到），或有項目缺引文。你只修這些項目，其他不動。

## 讀

1. 主控給你的失敗清單：`quote_check.py` 的輸出（哪一行、哪一頁、找不到或出現在別頁）與 `card.json` 的 `missingEvidence`。
2. `reviews/<slug>/cards/<key>/card.md`：用行號對到是哪一項。
3. `reviews/<slug>/text/<key>.txt`：找正確的頁與逐字原文。
4. `.claude/skills/lit-extract/card-schema.md` 的引文規則。

## 修

逐項處理：

- 原文其實在別頁 → 改 `page`。
- 引文有改寫或抄錯 → 換成原文逐字的那一段。
- 原文找不到能支持這一項的句子 → 刪掉這一項。不要硬找一句意思接近的。

`card.json` 是 `build_card.py` 用 `a.json`、`judge.json`、`audit.json` 重建的，只改 `card.md` 或 `card.json` 會在下次重建時被蓋掉。項目來自哪個檔就改哪個檔：

- 標了（補漏）（`source: audit`）的項目 → 改 `audit.json` 的 `additions.<欄位>`（含 `custom.<名稱>`）。若這一項只是重複卡片已有的項目 → 直接從 `audit.json` 刪掉。
- 欄位（結構化或敘述）在 `judge.json` 有 `resolved` 裁決 → 改 `judge.json` 裡的 `value`。
- `structured.topics` 的項目只在 `b.json`（不在 `a.json`）時 → 修 `b.json`；要刪就從 `b.json` 刪（build_card 會把 b.json 的標籤接在甲的後面，改 a.json 不會生效）。
- 其餘 → 改 `a.json`。

## 回報

一行：`DONE <key>：改頁碼 <n>、換引文 <n>、刪除 <n>`。
