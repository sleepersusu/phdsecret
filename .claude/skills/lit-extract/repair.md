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

項目在哪個檔就改哪個檔：結構化欄位若在 `judge.json` 有裁決，改 `judge.json` 裡的 `value`；其餘改 `a.json`。

## 回報

一行：`DONE <key>：改頁碼 <n>、換引文 <n>、刪除 <n>`。
